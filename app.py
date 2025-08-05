from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
# Optional imports for development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")

import pymysql
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    # Check if AWS credentials are available
    try:
        # Try to create a session and check credentials
        boto3_session = boto3.Session()
        credentials = boto3_session.get_credentials()
        if credentials is None:
            raise NoCredentialsError()
        # Test if credentials work by making a simple call
        sts_client = boto3.client('sts')
        sts_client.get_caller_identity()
        AWS_AVAILABLE = True
        print("AWS credentials are available and valid")
    except (NoCredentialsError, ClientError, Exception) as e:
        AWS_AVAILABLE = False
        print(f"AWS credentials not available or invalid: {e}")
except ImportError:
    AWS_AVAILABLE = False
    print("Warning: boto3 not installed. AWS features will be disabled.")

# Import configuration
from config import config

app = Flask(__name__)

# Load configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



# AWS Configuration
if AWS_AVAILABLE:
    try:
        transcribe_client = boto3.client('transcribe', region_name=app.config.get('AWS_REGION', 'us-east-1'))
        comprehend_client = boto3.client('comprehend', region_name=app.config.get('AWS_REGION', 'us-east-1'))
        s3_client = boto3.client('s3', region_name=app.config.get('AWS_REGION', 'us-east-1'))
    except Exception as e:
        print(f"Warning: AWS client initialization failed: {e}")
        AWS_AVAILABLE = False
else:
    transcribe_client = comprehend_client = s3_client = None


# Helper functions
def allowed_file(filename, file_type):
    if file_type == 'audio':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'webm']
    elif file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov', 'avi', 'mkv']
    return False

def process_ai_submission(file_path, file_type, text_content=None, progress_callback=None):
    """
    Enhanced process uploaded file or text using AWS AI services with Bedrock integration
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 Starting AI processing: file_path={file_path}, file_type={file_type}")
        
        if text_content:
            # For text submissions, use Bedrock for analysis
            logger.info("📝 Processing text submission")
            if progress_callback:
                progress_callback("Analyzing text with AI...", 50)
            
            from audio_processor import AudioProcessor
            processor = AudioProcessor()
            
            # Log AWS credential status
            if processor.aws_available:
                logger.info("☁️ AWS credentials available - will use Bedrock for text analysis")
            else:
                logger.warning("🚫 AWS credentials not available - using fallback text analysis")
            
            project_data = processor.extract_project_details_with_bedrock(text_content)
            
            if progress_callback:
                progress_callback("Text analysis complete!", 100)
            
            logger.info("✅ Text processing completed successfully")
            return project_data
            
        elif file_type == 'audio':
            # Use the enhanced AudioProcessor for audio files
            logger.info("🎵 Processing audio file")
            from audio_processor import AudioProcessor
            processor = AudioProcessor()
            
            # Log AWS credential status
            if processor.aws_available:
                logger.info("☁️ AWS credentials available - will use AWS Transcribe and Bedrock")
            else:
                logger.warning("🚫 AWS credentials not available - using filename-based mock processing")
            
            project_data = processor.process_audio_file(file_path, progress_callback)
            logger.info("✅ Audio processing completed successfully")
            return project_data
            
        elif file_type == 'video':
            # For video files, extract audio and process
            logger.info("📹 Processing video file")
            from audio_processor import AudioProcessor
            processor = AudioProcessor()
            
            # Log AWS credential status
            if processor.aws_available:
                logger.info("☁️ AWS credentials available - will use AWS services for video processing")
            else:
                logger.warning("🚫 AWS credentials not available - using filename-based mock processing")
            
            if progress_callback:
                progress_callback("Processing video file...", 30)
            
            # TODO: Extract audio from video file
            # For now, use filename-based mock data
            logger.info("📹 Video processing not yet implemented - using filename-based mock data")
            mock_transcript = processor._mock_transcription(file_path)
            project_data = processor.extract_project_details_with_bedrock(mock_transcript)
            
            if progress_callback:
                progress_callback("Video processing complete!", 100)
            
            logger.info("✅ Video processing completed successfully")
            return project_data
        
        return None
    
    except Exception as e:
        logger.error(f"❌ AI processing error: {e}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        
        if progress_callback:
            progress_callback(f"Error: {str(e)}", -1)
        
        return None

# Helper functions for AI text analysis
def extract_project_title(text):
    """Extract a project title from the text"""
    # Simple logic to create a title from the first sentence or key phrases
    sentences = text.split('.')
    if sentences:
        first_sentence = sentences[0].strip()
        if len(first_sentence) > 50:
            return first_sentence[:47] + "..."
        return first_sentence
    return "Home Improvement Project"

def extract_project_type(text, entities_response):
    """Extract project type from text"""
    text_lower = text.lower()
    
    # Common project types and keywords
    project_types = {
        'plumbing': ['plumb', 'pipe', 'faucet', 'sink', 'toilet', 'drain', 'leak', 'water'],
        'electrical': ['electric', 'wire', 'outlet', 'switch', 'light', 'circuit', 'power'],
        'kitchen': ['kitchen', 'cabinet', 'countertop', 'appliance', 'stove', 'refrigerator'],
        'bathroom': ['bathroom', 'shower', 'bathtub', 'tile', 'vanity'],
        'roofing': ['roof', 'shingle', 'gutter', 'leak'],
        'flooring': ['floor', 'carpet', 'hardwood', 'tile', 'laminate'],
        'painting': ['paint', 'wall', 'interior', 'exterior'],
        'hvac': ['heating', 'cooling', 'hvac', 'furnace', 'air conditioning'],
        'general': ['repair', 'fix', 'maintenance', 'handyman']
    }
    
    for project_type, keywords in project_types.items():
        if any(keyword in text_lower for keyword in keywords):
            return project_type.title()
    
    return 'General'

def extract_location(entities_response):
    """Extract location from entities"""
    # Look for location entities
    if 'Entities' in entities_response:
        for entity in entities_response['Entities']:
            if entity['Type'] == 'LOCATION':
                return entity['Text']
    return 'Not specified'

def extract_budget_range(text):
    """Extract budget range from text"""
    import re
    
    # Look for dollar amounts
    dollar_pattern = r'\$([0-9,]+)'
    matches = re.findall(dollar_pattern, text)
    
    if matches:
        amounts = [int(match.replace(',', '')) for match in matches]
        if len(amounts) >= 2:
            return min(amounts), max(amounts)
        elif len(amounts) == 1:
            amount = amounts[0]
            # If single amount, create a range around it
            return amount * 0.8, amount * 1.2
    
    # Look for budget keywords
    text_lower = text.lower()
    if 'budget' in text_lower or 'cost' in text_lower or 'price' in text_lower:
        # Default budget ranges based on common project types
        if any(word in text_lower for word in ['kitchen', 'bathroom']):
            return 5000, 25000
        elif any(word in text_lower for word in ['roof', 'hvac']):
            return 3000, 15000
        else:
            return 500, 5000
    
    return None, None

def extract_timeline(text):
    """Extract timeline from text"""
    text_lower = text.lower()
    
    # Look for timeline keywords
    if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'emergency']):
        return 'ASAP'
    elif any(word in text_lower for word in ['week', '1 week', 'within a week']):
        return '1 week'
    elif any(word in text_lower for word in ['2 weeks', 'two weeks', 'couple weeks']):
        return '2 weeks'
    elif any(word in text_lower for word in ['month', '1 month', 'within a month']):
        return '1 month'
    elif any(word in text_lower for word in ['flexible', 'no rush', 'whenever']):
        return 'Flexible'
    
    return '2-4 weeks'

# Bid management helper functions
def add_bid_history(bid_id, action, old_status=None, new_status=None, old_amount=None, new_amount=None, notes=None, created_by=None):
    """Add an entry to bid history for tracking changes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bid_history (bid_id, action, old_status, new_status, old_amount, new_amount, notes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (bid_id, action, old_status, new_status, old_amount, new_amount, notes, created_by))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding bid history: {e}")
        return False

def calculate_bid_expiration(days=30):
    """Calculate bid expiration date (default 30 days from now)"""
    from datetime import datetime, timedelta
    return datetime.now() + timedelta(days=days)

def expire_old_bids():
    """Expire bids that have passed their expiration date"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find expired bids
        cursor.execute('''
            SELECT id, status FROM bids 
            WHERE expires_at < NOW() AND status = 'Submitted'
        ''')
        expired_bids = cursor.fetchall()
        
        # Update expired bids
        for bid in expired_bids:
            cursor.execute('''
                UPDATE bids SET status = 'Expired' WHERE id = %s
            ''', (bid['id'],))
            
            # Add history entry
            add_bid_history(bid['id'], 'Expired', bid['status'], 'Expired', 
                          notes='Automatically expired due to time limit')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return len(expired_bids)
    except Exception as e:
        print(f"Error expiring bids: {e}")
        return 0

def send_bid_notification(bid_id, action, recipient_email=None, recipient_name=None, project_title=None, contractor_name=None, amount=None):
    """Send email notification for bid status changes"""
    # This is a placeholder for email functionality
    # In production, you would integrate with AWS SES, SendGrid, or similar
    try:
        print(f"EMAIL NOTIFICATION:")
        print(f"To: {recipient_email} ({recipient_name})")
        print(f"Subject: Bid {action.title()} - {project_title}")
        
        if action == 'submitted':
            print(f"Body: A new bid of ${amount} has been submitted by {contractor_name} for your project '{project_title}'.")
        elif action == 'accepted':
            print(f"Body: Congratulations! Your bid of ${amount} for '{project_title}' has been accepted.")
        elif action == 'rejected':
            print(f"Body: Your bid for '{project_title}' has been rejected. Thank you for your interest.")
        elif action == 'withdrawn':
            print(f"Body: The bid by {contractor_name} for '{project_title}' has been withdrawn.")
        elif action == 'expired':
            print(f"Body: Your bid for '{project_title}' has expired after 30 days.")
        
        print(f"Bid ID: {bid_id}")
        print("---")
        
        # TODO: Implement actual email sending with services like:
        # - AWS SES
        # - SendGrid
        # - Mailgun
        # - SMTP
        
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If there's a guest project in session, redirect to guest registration
    if session.get('guest_project_id'):
        return redirect(url_for('guest_register'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        location = request.form.get('location', '')
        company = request.form.get('company', '') if user_type == 'contractor' else ''
        specialties = request.form.get('specialties', '') if user_type == 'contractor' else ''
        business_info = request.form.get('business_info', '') if user_type == 'contractor' else ''
        
        # Validate input
        if not email or not password or not first_name or not last_name:
            flash('Please fill in all required fields.')
            return redirect(url_for('register'))
        
        try:
            # Check if user already exists
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Email already registered. Please use a different email or login.')
                cursor.close()
                conn.close()
                return redirect(url_for('register'))
            
            # Hash password
            password_hash = generate_password_hash(password)
            
            # Insert into users table
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name, role)
                VALUES (%s, %s, %s, %s, %s)
            ''', (email, password_hash, first_name, last_name, user_type))
            
            user_id = cursor.lastrowid
            
            # Insert into appropriate role-specific table
            if user_type == 'homeowner':
                cursor.execute('''
                    INSERT INTO homeowners (user_id, location)
                    VALUES (%s, %s)
                ''', (user_id, location))
            else:  # contractor
                # Get contractor-specific fields
                company = request.form.get('company', '')
                specialties = request.form.get('specialties', '')
                business_info = request.form.get('business_info', '')
                
                cursor.execute('''
                    INSERT INTO contractors (user_id, location, company, specialties, business_info)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (user_id, location, company, specialties, business_info))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Check if we need to redirect to project submission
            if request.form.get('redirect_to_project') == 'true':
                # Log the user in automatically and redirect to submit_project
                session['user'] = {
                    'id': user_id,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': user_type
                }
                flash('Registration successful! You can now submit your project.')
                return redirect(url_for('submit_project'))
            else:
                flash('Registration successful! You can now log in.')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}')
            return redirect(url_for('register'))
    
    return render_template('register.html')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Check if this is an AJAX request
            if request.is_json or request.headers.get('Content-Type', '').startswith('application/json') or 'XMLHttpRequest' in request.headers.get('X-Requested-With', ''):
                return jsonify({'success': False, 'error': 'Please log in to access this feature', 'redirect': url_for('login')}), 401
            else:
                flash('Please log in to access this page')
                return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        
        # Check if user is admin
        if not is_admin_user(session['user']['id']):
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def is_admin_user(user_id):
    """Check if user has admin privileges"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT admin_level, is_active FROM admin_users 
            WHERE user_id = %s AND is_active = TRUE
        ''', (user_id,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        return admin is not None
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

def get_admin_level(user_id):
    """Get admin level for user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT admin_level FROM admin_users 
            WHERE user_id = %s AND is_active = TRUE
        ''', (user_id,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        return admin['admin_level'] if admin else None
    except Exception as e:
        print(f"Error getting admin level: {e}")
        return None

def log_admin_activity(admin_user_id, action, target_type, target_id=None, details=None):
    """Log admin activity for audit trail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        user_agent = request.environ.get('HTTP_USER_AGENT', '')
        
        cursor.execute('''
            INSERT INTO admin_activity_logs 
            (admin_user_id, action, target_type, target_id, details, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (admin_user_id, action, target_type, target_id, json.dumps(details) if details else None, ip_address, user_agent))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging admin activity: {e}")
        return False

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.context_processor
def inject_user():
    return dict(user=session.get('user'))


@app.route('/guest_register', methods=['GET', 'POST'])
def guest_register():
    """Handle guest user registration and project claiming"""
    guest_project_id = session.get('guest_project_id')
    guest_project = None
    
    # Get guest project details if available
    if guest_project_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM guest_projects WHERE id = %s AND status = "Pending"', (guest_project_id,))
        guest_project = cursor.fetchone()
        cursor.close()
        conn.close()
    
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([first_name, last_name, email, password, confirm_password]):
            flash('Please fill in all required fields.')
            return render_template('guest_register.html', guest_project=guest_project)
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('guest_register.html', guest_project=guest_project)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.')
            return render_template('guest_register.html', guest_project=guest_project)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('An account with this email already exists. Please sign in instead.')
                cursor.close()
                conn.close()
                return render_template('guest_register.html', guest_project=guest_project)
            
            # Create new user
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name, role)
                VALUES (%s, %s, %s, %s, %s)
            ''', (email, password_hash, first_name, last_name, 'homeowner'))
            
            user_id = cursor.lastrowid
            
            # Create homeowner record
            cursor.execute('''
                INSERT INTO homeowners (user_id, location)
                VALUES (%s, %s)
            ''', (user_id, location))
            
            homeowner_id = cursor.lastrowid
            
            # If there's a guest project, claim it
            if guest_project:
                # Move guest project to regular projects table
                cursor.execute('''
                    INSERT INTO projects (title, description, project_type, location, budget_min, budget_max, 
                                        timeline, original_file_path, ai_processed_text, homeowner_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (guest_project['title'], guest_project['description'], guest_project['project_type'],
                      guest_project['location'] or location, guest_project['budget_min'], guest_project['budget_max'],
                      guest_project['timeline'], guest_project['original_file_path'], guest_project['ai_processed_text'],
                      homeowner_id, guest_project['created_at']))
                
                project_id = cursor.lastrowid
                
                # Mark guest project as claimed
                cursor.execute('''
                    UPDATE guest_projects SET status = 'Claimed' WHERE id = %s
                ''', (guest_project_id,))
                
                # Clear guest project from session
                session.pop('guest_project_id', None)
                
                flash(f'Registration successful! Your project "{guest_project["title"]}" has been added to your account.')
            else:
                flash('Registration successful! You can now submit projects and receive contractor bids.')
            
            conn.commit()
            
            # Log the user in
            session['user'] = {
                'id': user_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': 'homeowner'
            }
            
            cursor.close()
            conn.close()
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Registration failed: {str(e)}')
            return render_template('guest_register.html', guest_project=guest_project)
    
    return render_template('guest_register.html', guest_project=guest_project)

@app.route('/complete-registration')
def complete_registration():
    """Redirect to guest registration page"""
    return redirect(url_for('guest_register'))

@app.route('/guest_login')
def guest_login():
    """Redirect guest users to login with option to claim their project"""
    guest_project_id = session.get('guest_project_id')
    if guest_project_id:
        flash('Please sign in to your existing account to claim your submitted project, or create a new account.')
    return redirect(url_for('login'))

def cleanup_expired_guest_projects():
    """Clean up expired guest projects (called periodically)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mark expired projects
        cursor.execute('''
            UPDATE guest_projects 
            SET status = 'Expired' 
            WHERE status = 'Pending' AND expires_at < NOW()
        ''')
        
        expired_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        return expired_count
    except Exception as e:
        print(f"Error cleaning up expired guest projects: {e}")
        return 0

# ============================================================================
# ADVANCED BIDDING FEATURES
# ============================================================================

@app.route('/api/bid_comparison', methods=['POST'])
@login_required
def save_bid_comparison():
    """Save bid comparison for future reference"""
    user = session['user']
    if user['role'] != 'homeowner':
        return jsonify({'success': False, 'message': 'Only homeowners can save bid comparisons'}), 403
    
    data = request.get_json()
    project_id = data.get('project_id')
    bid_ids = data.get('bid_ids', [])
    notes = data.get('notes', '')
    
    if not project_id or len(bid_ids) < 2:
        return jsonify({'success': False, 'message': 'Invalid comparison data'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Homeowner profile not found'}), 404
    
    homeowner_id = homeowner_result['id']
    
    # Verify project ownership
    cursor.execute('SELECT * FROM projects WHERE id = %s AND homeowner_id = %s', (project_id, homeowner_id))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Project not found or access denied'}), 404
    
    # Save comparison
    import json
    cursor.execute('''
        INSERT INTO bid_comparisons (project_id, homeowner_id, bid_ids, comparison_notes)
        VALUES (%s, %s, %s, %s)
    ''', (project_id, homeowner_id, json.dumps(bid_ids), notes))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Comparison saved successfully'})

@app.route('/api/bid_comparison/<int:project_id>')
@login_required
def get_bid_comparisons(project_id):
    """Get saved bid comparisons for a project"""
    user = session['user']
    if user['role'] != 'homeowner':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Homeowner profile not found'}), 404
    
    homeowner_id = homeowner_result['id']
    
    # Get comparisons
    cursor.execute('''
        SELECT * FROM bid_comparisons 
        WHERE project_id = %s AND homeowner_id = %s 
        ORDER BY created_at DESC
    ''', (project_id, homeowner_id))
    
    comparisons = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'comparisons': comparisons})

@app.route('/send_bid_message/<int:bid_id>', methods=['POST'])
@login_required
def send_bid_message(bid_id):
    """Send a message related to a bid (negotiation, question, etc.)"""
    user = session['user']
    data = request.get_json()
    
    message_text = data.get('message_text', '').strip()
    message_type = data.get('message_type', 'negotiation')
    proposed_amount = data.get('proposed_amount')
    proposed_timeline = data.get('proposed_timeline')
    
    if not message_text:
        return jsonify({'success': False, 'message': 'Message text is required'}), 400
    
    if message_type not in ['negotiation', 'question', 'clarification', 'counter_offer']:
        return jsonify({'success': False, 'message': 'Invalid message type'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get bid details
    cursor.execute('''
        SELECT b.*, p.homeowner_id, c.user_id as contractor_user_id
        FROM bids b
        JOIN projects p ON b.project_id = p.id
        JOIN contractors c ON b.contractor_id = c.id
        WHERE b.id = %s
    ''', (bid_id,))
    
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found'}), 404
    
    # Determine sender and receiver
    if user['role'] == 'homeowner':
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if not homeowner_result or homeowner_result['id'] != bid['homeowner_id']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        receiver_id = bid['contractor_user_id']
    else:  # contractor
        if bid['contractor_user_id'] != user['id']:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        cursor.execute('SELECT user_id FROM homeowners WHERE id = %s', (bid['homeowner_id'],))
        homeowner_user = cursor.fetchone()
        receiver_id = homeowner_user['user_id']
    
    # Insert message
    cursor.execute('''
        INSERT INTO bid_messages (bid_id, sender_id, receiver_id, message_type, message_text, proposed_amount, proposed_timeline)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (bid_id, user['id'], receiver_id, message_type, message_text, proposed_amount, proposed_timeline))
    
    message_id = cursor.lastrowid
    
    # Update bid activity timestamp
    cursor.execute('UPDATE bids SET last_activity_at = NOW() WHERE id = %s', (bid_id,))
    
    # Create notification
    notification_type = 'new_message' if message_type in ['question', 'clarification'] else 'counter_offer'
    title = f"New {message_type.replace('_', ' ').title()} on Bid"
    notification_message = f"{user['first_name']} {user['last_name']} sent you a {message_type.replace('_', ' ')}"
    
    cursor.execute('''
        INSERT INTO bid_notifications (bid_id, user_id, notification_type, title, message)
        VALUES (%s, %s, %s, %s, %s)
    ''', (bid_id, receiver_id, notification_type, title, notification_message))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Message sent successfully', 'message_id': message_id})

@app.route('/api/bids/<int:bid_id>')
@login_required
def get_bid_details(bid_id):
    """Get bid details for a specific bid"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get bid details with project and homeowner info
    cursor.execute('''
        SELECT b.*, p.title as project_title, p.description,
               h.user_id as homeowner_user_id,
               u.first_name as homeowner_first_name, u.last_name as homeowner_last_name,
               c.user_id as contractor_user_id
        FROM bids b
        JOIN projects p ON b.project_id = p.id
        JOIN homeowners h ON p.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        JOIN contractors c ON b.contractor_id = c.id
        WHERE b.id = %s
    ''', (bid_id,))
    
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found'}), 404
    
    # Check access
    has_access = False
    if user['role'] == 'homeowner':
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if homeowner_result and bid['homeowner_user_id'] == user['id']:
            has_access = True
    elif user['role'] == 'contractor':
        if bid['contractor_user_id'] == user['id']:
            has_access = True
    
    if not has_access:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    cursor.close()
    conn.close()
    
    # Format response
    response_data = {
        'success': True,
        'bid_id': bid['id'],
        'project_title': bid['project_title'],
        'homeowner_name': f"{bid['homeowner_first_name']} {bid['homeowner_last_name']}",
        'amount': bid['amount'],
        'timeline': bid['timeline'],
        'status': bid['status'],
        'description': bid['description'],
        'created_at': bid['created_at']
    }
    
    return jsonify(response_data)

@app.route('/api/bid_messages/<int:bid_id>')
@login_required
def get_bid_messages(bid_id):
    """Get all messages for a bid"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify access to bid
    cursor.execute('''
        SELECT b.*, p.homeowner_id, c.user_id as contractor_user_id
        FROM bids b
        JOIN projects p ON b.project_id = p.id
        JOIN contractors c ON b.contractor_id = c.id
        WHERE b.id = %s
    ''', (bid_id,))
    
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found'}), 404
    
    # Check access
    has_access = False
    if user['role'] == 'homeowner':
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if homeowner_result and homeowner_result['id'] == bid['homeowner_id']:
            has_access = True
    else:  # contractor
        if bid['contractor_user_id'] == user['id']:
            has_access = True
    
    if not has_access:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get messages
    cursor.execute('''
        SELECT bm.*, 
               u.first_name, u.last_name, u.role
        FROM bid_messages bm
        JOIN users u ON bm.sender_id = u.id
        WHERE bm.bid_id = %s
        ORDER BY bm.created_at ASC
    ''', (bid_id,))
    
    messages = cursor.fetchall()
    
    # Mark messages as read for current user
    cursor.execute('''
        UPDATE bid_messages 
        SET is_read = TRUE 
        WHERE bid_id = %s AND receiver_id = %s AND is_read = FALSE
    ''', (bid_id, user['id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'messages': messages})

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Get notifications for current user"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT bn.*, b.amount, p.title as project_title
        FROM bid_notifications bn
        JOIN bids b ON bn.bid_id = b.id
        JOIN projects p ON b.project_id = p.id
        WHERE bn.user_id = %s
        ORDER BY bn.created_at DESC
        LIMIT 20
    ''', (user['id'],))
    
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'notifications': notifications})

@app.route('/api/notifications/<int:notification_id>/mark_read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE bid_notifications 
        SET is_read = TRUE 
        WHERE id = %s AND user_id = %s
    ''', (notification_id, user['id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Notification marked as read'})

@app.route('/api/contractor/message_stats')
@login_required
def get_contractor_message_stats():
    """Get message statistics for contractor dashboard"""
    user = session['user']
    
    if user['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        return jsonify({'success': False, 'message': 'Contractor not found'}), 404
    contractor_id = contractor_result['id']
    
    # Get total conversations (bids with messages)
    cursor.execute('''
        SELECT COUNT(DISTINCT b.id) as total
        FROM bids b
        WHERE b.contractor_id = %s
        AND EXISTS (SELECT 1 FROM bid_messages bm WHERE bm.bid_id = b.id)
    ''', (contractor_id,))
    total_conversations = cursor.fetchone()['total']
    
    # Get unread messages count
    cursor.execute('''
        SELECT COUNT(*) as unread
        FROM bid_messages bm
        JOIN bids b ON bm.bid_id = b.id
        WHERE b.contractor_id = %s
        AND bm.receiver_id = %s
        AND bm.is_read = FALSE
    ''', (contractor_id, user['id']))
    unread_messages = cursor.fetchone()['unread']
    
    # Get active negotiations (bids with recent activity)
    cursor.execute('''
        SELECT COUNT(DISTINCT b.id) as active
        FROM bids b
        WHERE b.contractor_id = %s
        AND b.status IN ('Submitted', 'Under Review')
        AND b.negotiation_allowed = TRUE
        AND b.last_activity_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    ''', (contractor_id,))
    active_negotiations = cursor.fetchone()['active']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'total': total_conversations,
        'unread': unread_messages,
        'active': active_negotiations
    })

@app.route('/api/contractor/messages')
@login_required
def get_contractor_messages():
    """Get all bid conversations for a contractor"""
    user = session['user']
    
    if user['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        return jsonify({'success': False, 'message': 'Contractor not found'}), 404
    contractor_id = contractor_result['id']
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    sort_by = request.args.get('sort', 'recent')
    search_term = request.args.get('search', '')
    
    # Build query
    query = '''
        SELECT DISTINCT b.id as bid_id, b.amount as bid_amount, b.status as bid_status,
               b.timeline, b.last_activity_at,
               p.title as project_title,
               CONCAT(u.first_name, ' ', u.last_name) as homeowner_name,
               (SELECT COUNT(*) FROM bid_messages bm 
                WHERE bm.bid_id = b.id AND bm.receiver_id = %s AND bm.is_read = FALSE) as unread_count,
               (SELECT bm2.message_text FROM bid_messages bm2 
                WHERE bm2.bid_id = b.id ORDER BY bm2.created_at DESC LIMIT 1) as last_message
        FROM bids b
        JOIN projects p ON b.project_id = p.id
        JOIN homeowners h ON p.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        WHERE b.contractor_id = %s
        AND EXISTS (SELECT 1 FROM bid_messages bm WHERE bm.bid_id = b.id)
    '''
    
    params = [user['id'], contractor_id]
    
    # Add status filter
    if status_filter:
        if status_filter == 'active':
            query += " AND b.status IN ('Submitted', 'Under Review')"
        elif status_filter == 'pending':
            query += " AND b.status = 'Submitted'"
        elif status_filter == 'negotiating':
            query += " AND b.negotiation_allowed = TRUE AND b.status = 'Under Review'"
        elif status_filter == 'accepted':
            query += " AND b.status = 'Accepted'"
        elif status_filter == 'declined':
            query += " AND b.status = 'Declined'"
    
    # Add search filter
    if search_term:
        query += " AND (p.title LIKE %s OR CONCAT(u.first_name, ' ', u.last_name) LIKE %s)"
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern])
    
    # Add sorting
    if sort_by == 'recent':
        query += " ORDER BY b.last_activity_at DESC"
    elif sort_by == 'oldest':
        query += " ORDER BY b.last_activity_at ASC"
    elif sort_by == 'project':
        query += " ORDER BY p.title ASC"
    elif sort_by == 'amount':
        query += " ORDER BY b.amount DESC"
    else:
        query += " ORDER BY b.last_activity_at DESC"
    
    cursor.execute(query, params)
    messages = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'messages': messages})

@app.route('/api/bid_messages/<int:bid_id>/mark_read', methods=['POST'])
@login_required
def mark_bid_messages_read(bid_id):
    """Mark all messages in a bid conversation as read for current user"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify access to bid
    cursor.execute('''
        SELECT b.*, p.homeowner_id, c.user_id as contractor_user_id
        FROM bids b
        JOIN projects p ON b.project_id = p.id
        JOIN contractors c ON b.contractor_id = c.id
        WHERE b.id = %s
    ''', (bid_id,))
    
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found'}), 404
    
    # Check access
    has_access = False
    if user['role'] == 'homeowner':
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if homeowner_result and homeowner_result['id'] == bid['homeowner_id']:
            has_access = True
    else:  # contractor
        if bid['contractor_user_id'] == user['id']:
            has_access = True
    
    if not has_access:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Mark messages as read
    cursor.execute('''
        UPDATE bid_messages 
        SET is_read = TRUE 
        WHERE bid_id = %s AND receiver_id = %s AND is_read = FALSE
    ''', (bid_id, user['id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Messages marked as read'})

@app.route('/api/bid_messages', methods=['POST'])
@login_required
def send_bid_message_api():
    """Send a bid message via API (for contractor messages page)"""
    user = session['user']
    data = request.get_json()
    
    bid_id = data.get('bid_id')
    message = data.get('message', '').strip()
    message_type = data.get('message_type', 'response')
    price_adjustment = data.get('price_adjustment')
    timeline_adjustment = data.get('timeline_adjustment')
    
    if not bid_id or not message:
        return jsonify({'success': False, 'error': 'Bid ID and message are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify access to bid
        cursor.execute('''
            SELECT b.*, p.homeowner_id, c.user_id as contractor_user_id,
                   h.user_id as homeowner_user_id
            FROM bids b
            JOIN projects p ON b.project_id = p.id
            JOIN contractors c ON b.contractor_id = c.id
            JOIN homeowners h ON p.homeowner_id = h.id
            WHERE b.id = %s
        ''', (bid_id,))
        
        bid = cursor.fetchone()
        if not bid:
            return jsonify({'success': False, 'error': 'Bid not found'}), 404
        
        # Check access and determine receiver
        receiver_id = None
        if user['role'] == 'homeowner' and bid['homeowner_user_id'] == user['id']:
            receiver_id = bid['contractor_user_id']
        elif user['role'] == 'contractor' and bid['contractor_user_id'] == user['id']:
            receiver_id = bid['homeowner_user_id']
        else:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Insert message
        cursor.execute('''
            INSERT INTO bid_messages (bid_id, sender_id, receiver_id, message_text, message_type, 
                                    proposed_amount, proposed_timeline)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (bid_id, user['id'], receiver_id, message, message_type, 
              price_adjustment, timeline_adjustment))
        
        message_id = cursor.lastrowid
        
        # Update bid activity
        cursor.execute('''
            UPDATE bids SET last_activity_at = NOW() WHERE id = %s
        ''', (bid_id,))
        
        # Create notification for receiver
        notification_title = f"New message about your bid"
        if message_type == 'price_adjustment':
            notification_title = "Price adjustment proposed"
        elif message_type == 'timeline_adjustment':
            notification_title = "Timeline adjustment proposed"
        elif message_type == 'negotiation':
            notification_title = "Bid negotiation message"
        
        cursor.execute('''
            INSERT INTO bid_notifications (bid_id, user_id, notification_type, title, message)
            VALUES (%s, %s, %s, %s, %s)
        ''', (bid_id, receiver_id, 'new_message', notification_title, 
              f'New message: {message[:100]}...'))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Message sent successfully',
            'message_id': message_id
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': f'Error sending message: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/expire_bids', methods=['POST'])
@login_required
def manual_expire_bids():
    """Manually trigger bid expiration check (admin only)"""
    user = session['user']
    
    # Check if user is admin (simplified check)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE user_id = %s AND is_active = TRUE', (user['id'],))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    cursor.close()
    conn.close()
    
    # Run expiration check
    expired_count = expire_old_bids()
    
    return jsonify({
        'success': True, 
        'message': f'Expired {expired_count} bids',
        'expired_count': expired_count
    })

def expire_old_bids():
    """Check for and expire old bids based on their expiration dates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Find bids that should be expired
        cursor.execute('''
            SELECT id, project_id, contractor_id, amount
            FROM bids 
            WHERE status = 'Submitted' 
            AND auto_expire_enabled = TRUE
            AND expires_at IS NOT NULL 
            AND expires_at < NOW()
        ''')
        
        expired_bids = cursor.fetchall()
        expired_count = len(expired_bids)
        
        if expired_count > 0:
            # Update bid statuses to expired
            cursor.execute('''
                UPDATE bids 
                SET status = 'Expired', last_activity_at = NOW()
                WHERE status = 'Submitted' 
                AND auto_expire_enabled = TRUE
                AND expires_at IS NOT NULL 
                AND expires_at < NOW()
            ''')
            
            # Create notifications for expired bids
            for bid in expired_bids:
                # Notify contractor
                cursor.execute('''
                    SELECT user_id FROM contractors WHERE id = %s
                ''', (bid['contractor_id'],))
                contractor_user = cursor.fetchone()
                
                if contractor_user:
                    cursor.execute('''
                        INSERT INTO bid_notifications (bid_id, user_id, notification_type, title, message)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (bid['id'], contractor_user['user_id'], 'bid_expired', 
                          'Bid Expired', f'Your bid of ${bid["amount"]:,.2f} has expired'))
                
                # Notify homeowner
                cursor.execute('''
                    SELECT h.user_id FROM homeowners h
                    JOIN projects p ON h.id = p.homeowner_id
                    WHERE p.id = %s
                ''', (bid['project_id'],))
                homeowner_user = cursor.fetchone()
                
                if homeowner_user:
                    cursor.execute('''
                        INSERT INTO bid_notifications (bid_id, user_id, notification_type, title, message)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (bid['id'], homeowner_user['user_id'], 'bid_expired', 
                          'Bid Expired', f'A bid of ${bid["amount"]:,.2f} on your project has expired'))
        
        conn.commit()
        return expired_count
        
    except Exception as e:
        conn.rollback()
        print(f"Error expiring bids: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

# def create_demo_users():
#     """Adapted for Cognito - run manually or via script"""

def get_db_connection():
    # Try MySQL first (for production)
    try:
        if os.getenv('DB_HOST'):
            return pymysql.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USERNAME'),
                password=os.getenv('DB_PASSWORD'),
                db=os.getenv('DB_NAME'),
                port=int(os.getenv('DB_PORT', 3306)),
                cursorclass=pymysql.cursors.DictCursor
            )
    except Exception as e:
        print(f"MySQL connection failed: {e}")
        print("Falling back to SQLite for local development...")
    
    # Fallback to SQLite for local development
    import sqlite3
    conn = sqlite3.connect('homepro.db')
    conn.row_factory = sqlite3.Row  # This makes it return dict-like objects
    return conn

def init_database():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Detect database type
        is_sqlite = hasattr(conn, 'row_factory')
        
        if is_sqlite:
            # SQLite version
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('homeowner', 'contractor')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            # MySQL version
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    role ENUM('homeowner', 'contractor') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email (email),
                    INDEX idx_role (role)
                )
            ''')
        
        # Create homeowners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homeowners (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                location VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id)
            )
        ''')
        
        # Create contractors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contractors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                location VARCHAR(255),
                company VARCHAR(255),
                specialties TEXT,
                business_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_id (user_id)
            )
        ''')
        
        # Create projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                project_type VARCHAR(100) NOT NULL,
                location VARCHAR(255),
                budget_min DECIMAL(10,2),
                budget_max DECIMAL(10,2),
                timeline VARCHAR(255),
                status ENUM('Active', 'Completed', 'Closed') DEFAULT 'Active',
                original_file_path VARCHAR(500),
                ai_processed_text TEXT,
                homeowner_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE,
                INDEX idx_status (status),
                INDEX idx_homeowner (homeowner_id),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create guest_projects table for unregistered users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guest_projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                project_type VARCHAR(100) NOT NULL,
                location VARCHAR(255),
                budget_min DECIMAL(10,2),
                budget_max DECIMAL(10,2),
                timeline VARCHAR(255),
                status ENUM('Pending', 'Claimed', 'Expired') DEFAULT 'Pending',
                original_file_path VARCHAR(500),
                ai_processed_text TEXT,
                guest_email VARCHAR(255),
                guest_phone VARCHAR(20),
                guest_name VARCHAR(255),
                session_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 7 DAY),
                INDEX idx_status (status),
                INDEX idx_session (session_id),
                INDEX idx_guest_email (guest_email),
                INDEX idx_created (created_at),
                INDEX idx_expires (expires_at)
            )
        ''')
        
        # Create bids table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bids (
                id INT AUTO_INCREMENT PRIMARY KEY,
                amount DECIMAL(10,2) NOT NULL,
                timeline VARCHAR(255),
                description TEXT,
                status ENUM('Submitted', 'Accepted', 'Rejected', 'Withdrawn', 'Expired') DEFAULT 'Submitted',
                project_id INT NOT NULL,
                contractor_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                withdrawn_at TIMESTAMP NULL,
                withdrawal_reason TEXT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
                INDEX idx_project (project_id),
                INDEX idx_contractor (contractor_id),
                INDEX idx_status (status),
                INDEX idx_expires (expires_at)
            )
        ''')
        
        # Create bid_history table for tracking bid changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bid_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bid_id INT NOT NULL,
                action ENUM('Created', 'Updated', 'Withdrawn', 'Accepted', 'Rejected', 'Expired') NOT NULL,
                old_status VARCHAR(50),
                new_status VARCHAR(50),
                old_amount DECIMAL(10,2),
                new_amount DECIMAL(10,2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INT,
                FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_bid (bid_id),
                INDEX idx_action (action),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create admin_users table for admin access control
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                admin_level ENUM('super_admin', 'admin', 'moderator') DEFAULT 'admin',
                permissions JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_admin_level (admin_level),
                INDEX idx_active (is_active)
            )
        ''')
        
        # Create admin_activity_logs table for audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_user_id INT NOT NULL,
                action VARCHAR(255) NOT NULL,
                target_type ENUM('user', 'project', 'bid', 'contractor', 'system') NOT NULL,
                target_id INT,
                details JSON,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE CASCADE,
                INDEX idx_admin_user (admin_user_id),
                INDEX idx_action (action),
                INDEX idx_target (target_type, target_id),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create system_metrics table for platform statistics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(15,2) NOT NULL,
                metric_type ENUM('count', 'amount', 'percentage', 'duration') DEFAULT 'count',
                category VARCHAR(50) NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                INDEX idx_metric_name (metric_name),
                INDEX idx_category (category),
                INDEX idx_recorded (recorded_at)
            )
        ''')
        
        # Create user_verification table for verification workflow
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_verification (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                verification_type ENUM('email', 'phone', 'identity', 'business') NOT NULL,
                status ENUM('pending', 'approved', 'rejected', 'expired') DEFAULT 'pending',
                verification_data JSON,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP NULL,
                reviewed_by INT NULL,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (reviewed_by) REFERENCES admin_users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_type (verification_type),
                INDEX idx_status (status),
                INDEX idx_submitted (submitted_at)
            )
        ''')
        
        # Create content_moderation table for content review
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_moderation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content_type ENUM('project', 'contractor_profile', 'bid', 'user_message') NOT NULL,
                content_id INT NOT NULL,
                status ENUM('pending', 'approved', 'rejected', 'flagged') DEFAULT 'pending',
                flagged_reason VARCHAR(255),
                reviewed_by INT NULL,
                reviewed_at TIMESTAMP NULL,
                auto_flagged BOOLEAN DEFAULT FALSE,
                flag_score DECIMAL(3,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reviewed_by) REFERENCES admin_users(id) ON DELETE SET NULL,
                INDEX idx_content (content_type, content_id),
                INDEX idx_status (status),
                INDEX idx_auto_flagged (auto_flagged),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create project_images table for storing project images (up to 4 per project)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                image_path VARCHAR(500) NOT NULL,
                image_order TINYINT NOT NULL DEFAULT 1 CHECK (image_order >= 1 AND image_order <= 4),
                original_filename VARCHAR(255),
                file_size INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE KEY unique_project_order (project_id, image_order),
                INDEX idx_project (project_id),
                INDEX idx_order (image_order)
            )
        ''')

        # Create project_status table for tracking project progress (10% increments)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                status_percentage INT NOT NULL DEFAULT 0 CHECK (status_percentage >= 0 AND status_percentage <= 100),
                status_description VARCHAR(255),
                updated_by INT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_project (project_id),
                INDEX idx_percentage (status_percentage),
                INDEX idx_updated (updated_at)
            )
        ''')

        # Create reviews table for contractor ratings and reviews
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                contractor_id INT NOT NULL,
                homeowner_id INT NOT NULL,
                rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
                FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE,
                UNIQUE KEY unique_project_review (project_id, contractor_id),
                INDEX idx_contractor (contractor_id),
                INDEX idx_homeowner (homeowner_id),
                INDEX idx_rating (rating),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create review_replies table for contractor responses to reviews
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_replies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                review_id INT NOT NULL,
                contractor_id INT NOT NULL,
                reply_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
                UNIQUE KEY unique_review_reply (review_id),
                INDEX idx_review (review_id),
                INDEX idx_contractor (contractor_id),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create contractor_availability table for availability calendar
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contractor_availability (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contractor_id INT NOT NULL,
                available_date DATE NOT NULL,
                status ENUM('available', 'busy', 'unavailable') DEFAULT 'available',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
                UNIQUE KEY unique_contractor_date (contractor_id, available_date),
                INDEX idx_contractor (contractor_id),
                INDEX idx_date (available_date),
                INDEX idx_status (status)
            )
        ''')
        
        # Check if contractors table needs new columns (for migration)
        try:
            cursor.execute("SHOW COLUMNS FROM contractors LIKE 'average_rating'")
            if not cursor.fetchone():
                new_columns = [
                    "ADD COLUMN bio TEXT AFTER business_info",
                    "ADD COLUMN years_experience INT DEFAULT 0 AFTER bio",
                    "ADD COLUMN profile_picture VARCHAR(500) AFTER years_experience",
                    "ADD COLUMN portfolio TEXT AFTER profile_picture",
                    "ADD COLUMN average_rating DECIMAL(3,1) DEFAULT 0.0 AFTER portfolio",
                    "ADD COLUMN rating_count INTEGER DEFAULT 0 AFTER average_rating",
                    "ADD COLUMN verified BOOLEAN DEFAULT FALSE AFTER rating_count"
                ]
                
                for column in new_columns:
                    try:
                        cursor.execute(f"ALTER TABLE contractors {column}")
                        print(f"Added column: {column}")
                    except Exception as e:
                        if "Duplicate column name" not in str(e):
                            print(f"Warning: Could not add column {column}: {e}")
        except Exception as e:
            print(f"Migration check error: {e}")

        # Check if projects table needs status update (for migration)
        try:
            cursor.execute("SHOW COLUMNS FROM projects WHERE Field = 'status'")
            status_column = cursor.fetchone()
            if status_column and 'Completed' not in status_column['Type']:
                # Update the status enum to include more options
                cursor.execute('''
                    ALTER TABLE projects 
                    MODIFY COLUMN status ENUM('Active', 'In Progress', 'Completed', 'Terminated', 'Closed') DEFAULT 'Active'
                ''')
                print("Updated projects status column with new options")
        except Exception as e:
            print(f"Projects status migration error: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables created successfully!")
        return True
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email or not password:
            flash('Please enter both email and password.')
            return redirect(url_for('login'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, email, password_hash, first_name, last_name, role FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                # Login successful
                session['user'] = {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'role': user['role']
                }
                
                # Check for guest project to claim
                guest_project_id = session.get('guest_project_id')
                if guest_project_id and user['role'] == 'homeowner':
                    try:
                        # Get guest project details
                        cursor.execute('SELECT * FROM guest_projects WHERE id = %s AND status = "Pending"', (guest_project_id,))
                        guest_project = cursor.fetchone()
                        
                        if guest_project:
                            # Get homeowner ID
                            cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
                            homeowner_result = cursor.fetchone()
                            
                            if homeowner_result:
                                homeowner_id = homeowner_result['id']
                                
                                # Move guest project to regular projects table
                                cursor.execute('''
                                    INSERT INTO projects (title, description, project_type, location, budget_min, budget_max, 
                                                        timeline, original_file_path, ai_processed_text, homeowner_id, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ''', (guest_project['title'], guest_project['description'], guest_project['project_type'],
                                      guest_project['location'], guest_project['budget_min'], guest_project['budget_max'],
                                      guest_project['timeline'], guest_project['original_file_path'], guest_project['ai_processed_text'],
                                      homeowner_id, guest_project['created_at']))
                                
                                # Mark guest project as claimed
                                cursor.execute('UPDATE guest_projects SET status = "Claimed" WHERE id = %s', (guest_project_id,))
                                
                                conn.commit()
                                
                                # Clear guest project from session
                                session.pop('guest_project_id', None)
                                
                                flash(f'Welcome back! Your project "{guest_project["title"]}" has been added to your account.')
                    except Exception as e:
                        print(f"Error claiming guest project: {e}")
                        # Continue with normal login even if claiming fails
                
                # Check if user is admin and redirect to admin portal
                if is_admin_user(user['id']):
                    flash('Welcome to the Admin Portal!')
                    return redirect(url_for('admin_dashboard'))
                
                # Check for project submission context
                redirect_to_project = request.form.get('redirect_to_project')
                if redirect_to_project == 'true':
                    flash('Login successful! You can now complete your project submission.')
                    return redirect(url_for('submit_project'))
                
                if not guest_project_id:
                    flash('Login successful!')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Login failed: {str(e)}')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.context_processor
def inject_user():
    return dict(user=session.get('user'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user['role'] == 'homeowner':
        # Get homeowner ID from homeowners table
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if not homeowner_result:
            flash('Homeowner profile not found. Please contact support.')
            return redirect(url_for('login'))
        homeowner_id = homeowner_result['id']
        
        cursor.execute('''
            SELECT p.*, 
                   (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id) as bid_count,
                   (SELECT b.amount FROM bids b WHERE b.project_id = p.id AND b.status = 'Accepted' LIMIT 1) as accepted_bid_amount,
                   (SELECT CONCAT(u.first_name, ' ', u.last_name) FROM bids b 
                    JOIN contractors c ON b.contractor_id = c.id
                    JOIN users u ON c.user_id = u.id 
                    WHERE b.project_id = p.id AND b.status = 'Accepted' LIMIT 1) as accepted_contractor_name,
                   (SELECT b.id FROM bids b WHERE b.project_id = p.id AND b.status = 'Accepted' LIMIT 1) as accepted_bid_id
            FROM projects p 
            WHERE homeowner_id = %s 
            ORDER BY created_at DESC
        ''', (homeowner_id,))
        projects = cursor.fetchall()
        
        cursor.execute('''
            SELECT b.*, p.title as project_title, 
                   u.first_name as contractor_first_name, 
                   u.last_name as contractor_last_name,
                   c.company as contractor_company
            FROM bids b 
            JOIN projects p ON b.project_id = p.id 
            JOIN contractors c ON b.contractor_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE p.homeowner_id = %s 
            ORDER BY b.created_at DESC 
            LIMIT 15
        ''', (homeowner_id,))
        recent_bids = cursor.fetchall()
        template = 'homeowner_dashboard.html'
        render_args = {'projects': projects, 'recent_bids': recent_bids}
    else:
        # Get contractor ID from contractors table
        cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
        contractor_result = cursor.fetchone()
        if not contractor_result:
            flash('Contractor profile not found. Please contact support.')
            return redirect(url_for('login'))
        contractor_id = contractor_result['id']
        
        cursor.execute('''
            SELECT p.*, h.location,
                   (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id) as bid_count, 
                   (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id AND b.contractor_id = %s) as has_user_bid 
            FROM projects p 
            JOIN homeowners h ON p.homeowner_id = h.id
            WHERE status = 'Active' 
            ORDER BY created_at DESC
        ''', (contractor_id,))
        projects = cursor.fetchall()
        
        cursor.execute('''
            SELECT b.*, p.title, p.project_type 
            FROM bids b 
            JOIN projects p ON b.project_id = p.id 
            WHERE b.contractor_id = %s 
            ORDER BY b.created_at DESC
        ''', (contractor_id,))
        bids = cursor.fetchall()
        template = 'contractor_dashboard.html'
        render_args = {'projects': projects, 'bids': bids, 'contractor_id': contractor_id}
    
    cursor.close()
    conn.close()
    return render_template(template, **render_args)

# Global dictionary to store processing progress (in production, use Redis or database)
processing_progress = {}

@app.route('/process_audio_async', methods=['POST'])
@login_required
def process_audio_async():
    """
    Async endpoint for audio processing with progress tracking
    """
    import threading
    import uuid
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    if not allowed_file(filename, 'audio'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Generate unique processing ID
    process_id = str(uuid.uuid4())
    
    # Save file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{process_id}_{filename}")
    file.save(file_path)
    
    # Initialize progress tracking
    processing_progress[process_id] = {
        'status': 'starting',
        'progress': 0,
        'message': 'Initializing...',
        'result': None,
        'error': None
    }
    
    def progress_callback(message, progress):
        processing_progress[process_id].update({
            'message': message,
            'progress': progress,
            'status': 'processing' if progress >= 0 else 'error'
        })
        if progress < 0:
            processing_progress[process_id]['error'] = message
    
    def process_in_background():
        try:
            result = process_ai_submission(file_path, 'audio', progress_callback=progress_callback)
            if result:
                processing_progress[process_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Processing complete!',
                    'result': result
                })
            else:
                processing_progress[process_id].update({
                    'status': 'error',
                    'progress': -1,
                    'message': 'Processing failed',
                    'error': 'Unknown error occurred'
                })
        except Exception as e:
            processing_progress[process_id].update({
                'status': 'error',
                'progress': -1,
                'message': f'Error: {str(e)}',
                'error': str(e)
            })
        finally:
            # Clean up file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    # Start background processing
    thread = threading.Thread(target=process_in_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'process_id': process_id,
        'status': 'started',
        'message': 'Processing started'
    })

@app.route('/processing_status/<process_id>')
@login_required
def get_processing_status(process_id):
    """
    Get the current status of audio processing
    """
    if process_id not in processing_progress:
        return jsonify({'error': 'Process not found'}), 404
    
    status = processing_progress[process_id].copy()
    
    # Clean up completed processes after returning status
    if status['status'] in ['completed', 'error']:
        # Keep for a short time to allow client to retrieve
        pass
    
    return jsonify(status)

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """
    New route to handle audio processing and return JSON data for preview
    Step 2 of the new workflow: AWS Transcribe + GenAI analysis
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🎵 Starting audio processing for preview...")
        
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        filename = secure_filename(file.filename)
        logger.info(f"📁 Processing audio file: {filename}")
        
        # Check if file type is allowed
        if not allowed_file(filename, 'audio'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload an audio file in supported formats (MP3, WAV, M4A, AAC, FLAC, OGG, WMA, WebM).'
            }), 400
        
        # Save the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"💾 File saved to: {file_path}")
        
        # Process the audio file with AI
        def progress_callback(message, percentage):
            logger.info(f"📊 Progress: {percentage}% - {message}")
        
        project_data = process_ai_submission(file_path, 'audio', progress_callback=progress_callback)
        
        if not project_data:
            logger.error("❌ Audio processing failed")
            return jsonify({
                'success': False,
                'error': 'Failed to process audio file. Please try again or use text submission.'
            }), 500
        
        logger.info("✅ Audio processing completed successfully")
        
        # Return the processed data for preview
        return jsonify({
            'success': True,
            'data': {
                'title': project_data.get('title', ''),
                'description': project_data.get('description', ''),
                'project_type': project_data.get('project_type', 'General'),
                'location': project_data.get('location', ''),
                'budget_min': project_data.get('budget_min'),
                'budget_max': project_data.get('budget_max'),
                'timeline': project_data.get('timeline', ''),
                'transcribed_text': project_data.get('transcribed_text', ''),
                'confidence': project_data.get('confidence', 0.0),
                'extraction_method': project_data.get('extraction_method', 'unknown'),
                's3_key': project_data.get('s3_key'),
                'filename': filename
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Audio processing error: {e}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        
        return jsonify({
             'success': False,
             'error': f'Processing error: {str(e)}'
         }), 500

@app.route('/process_audio_transcript', methods=['POST'])
def process_audio_transcript():
    """
    New route to handle audio transcription only (no Bedrock analysis)
    Step 2 of the 5-step workflow: AWS Transcribe only
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🎤 Starting audio transcription only...")
        
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        filename = secure_filename(file.filename)
        logger.info(f"📁 Processing audio file: {filename}")
        
        # Check if file type is allowed
        if not allowed_file(filename, 'audio'):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload an audio file in supported formats (MP3, WAV, M4A, AAC, FLAC, OGG, WMA, WebM).'
            }), 400
        
        # Save the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"💾 File saved to: {file_path}")
        
        # Process the audio file for transcription only
        from audio_processor import AudioProcessor
        processor = AudioProcessor()
        
        def progress_callback(message, percentage):
            logger.info(f"📊 Progress: {percentage}% - {message}")
        
        transcript_data = processor.transcribe_audio_only(file_path, progress_callback=progress_callback)
        
        if not transcript_data or transcript_data.get('error'):
            logger.error("❌ Audio transcription failed")
            return jsonify({
                'success': False,
                'error': transcript_data.get('error', 'Failed to transcribe audio file. Please try again.')
            }), 500
        
        logger.info("✅ Audio transcription completed successfully")
        
        # Return the transcript data
        return jsonify({
            'success': True,
            'data': {
                'transcript': transcript_data.get('transcript', ''),
                'processing_status': transcript_data.get('processing_status', 'transcription_complete'),
                'confidence': transcript_data.get('confidence', 1.0),
                's3_key': transcript_data.get('s3_key'),
                's3_uri': transcript_data.get('s3_uri'),
                'filename': filename
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Audio transcription error: {e}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        
        return jsonify({
             'success': False,
             'error': f'Transcription error: {str(e)}'
         }), 500

@app.route('/process_transcript_ai', methods=['POST'])
def process_transcript_ai():
    """
    Process transcript with Bedrock AI for project detail extraction
    Step 4 of the 5-step workflow: AI Analysis
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🤖 Starting AI analysis of transcript...")
        
        # Get transcript from request
        transcript = request.json.get('transcript', '')
        filename = request.json.get('filename', '')
        s3_key = request.json.get('s3_key', '')
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'No transcript provided for AI analysis'
            }), 400
        
        logger.info(f"📝 Processing transcript of length: {len(transcript)}")
        
        # Process transcript with Bedrock
        from audio_processor import AudioProcessor
        processor = AudioProcessor()
        
        project_details = processor.extract_project_details_with_bedrock(transcript)
        
        if not project_details or project_details.get('error'):
            logger.error("❌ AI analysis failed")
            return jsonify({
                'success': False,
                'error': project_details.get('error', 'Failed to analyze transcript. Please try again.')
            }), 500
        
        logger.info("✅ AI analysis completed successfully")
        
        # Add transcript and file info to results
        project_details['transcript'] = transcript
        project_details['filename'] = filename
        project_details['s3_key'] = s3_key
        project_details['processing_status'] = 'ai_analysis_complete'
        
        return jsonify({
            'success': True,
            'data': project_details
        })
        
    except Exception as e:
        logger.error(f"❌ AI analysis error: {e}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        
        return jsonify({
             'success': False,
             'error': f'AI analysis error: {str(e)}'
         }), 500

@app.route('/submit_preview', methods=['POST'])
@login_required
def submit_preview():
    """
    New route to handle preview form submission
    Step 4 of the new workflow: Submit the preview form
    Requires user authentication
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📝 Processing preview form submission...")
        
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        project_type = request.form.get('project_type', 'General')
        location = request.form.get('location', '').strip()
        budget_min = request.form.get('budget_min')
        budget_max = request.form.get('budget_max')
        timeline = request.form.get('timeline', '').strip()
        
        # Get AI processing data
        transcribed_text = request.form.get('transcribed_text', '')
        confidence = request.form.get('confidence', 0.0)
        extraction_method = request.form.get('extraction_method', 'unknown')
        s3_key = request.form.get('s3_key', '')
        filename = request.form.get('filename', '')
        
        # Validate required fields
        if not title:
            return jsonify({
                'success': False,
                'error': 'Project title is required'
            }), 400
        
        if not description:
            return jsonify({
                'success': False,
                'error': 'Project description is required'
            }), 400
        
        # Process budget values
        try:
            budget_min = float(budget_min) if budget_min else None
            budget_max = float(budget_max) if budget_max else None
        except (ValueError, TypeError):
            budget_min = None
            budget_max = None
        
        # User is authenticated (required by @login_required decorator)
        user = session['user']
        
        if user['role'] != 'homeowner':
            return jsonify({
                'success': False,
                'error': 'Only homeowners can submit projects'
            }), 403
        
        # User is logged in as homeowner - save directly to projects table
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get homeowner ID from homeowners table
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if not homeowner_result:
            return jsonify({
                'success': False,
                'error': 'Homeowner profile not found. Please contact support.'
            }), 400
        
        homeowner_id = homeowner_result['id']
        
        insert_query = """
        INSERT INTO projects (
            homeowner_id, title, description, project_type, location, 
            budget_min, budget_max, timeline, status,
            original_file_path, ai_processed_text, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        # Construct file path if we have filename
        file_path = f"uploads/{filename}" if filename else None
        
        cursor.execute(insert_query, (
            homeowner_id, title, description, project_type, location,
            budget_min, budget_max, timeline, 'Active',
            file_path, transcribed_text
        ))
        
        project_id = cursor.lastrowid
        
        # Handle image uploads
        import os
        from werkzeug.utils import secure_filename
        
        for i in range(1, 5):  # Handle up to 4 images
            image_key = f'project_image_{i}'
            if image_key in request.files:
                image_file = request.files[image_key]
                if image_file and image_file.filename:
                    # Validate file type
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                    if '.' in image_file.filename and \
                       image_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        
                        # Create secure filename
                        filename = secure_filename(image_file.filename)
                        # Add project ID and timestamp to avoid conflicts
                        import time
                        timestamp = str(int(time.time()))
                        filename = f"project_{project_id}_{timestamp}_{i}_{filename}"
                        
                        # Ensure uploads directory exists
                        upload_dir = os.path.join(os.getcwd(), 'static', 'uploads', 'projects')
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        # Save file
                        file_path = os.path.join(upload_dir, filename)
                        image_file.save(file_path)
                        
                        # Store relative path in database
                        relative_path = f"uploads/projects/{filename}"
                        
                        # Insert into project_images table
                        cursor.execute("""
                            INSERT INTO project_images (project_id, image_path, image_order, created_at)
                            VALUES (%s, %s, %s, NOW())
                        """, (project_id, relative_path, i))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Project created successfully with ID: {project_id}")
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'message': 'Project submitted successfully!'
        })
        
    except Exception as e:
        logger.error(f"❌ Preview submission error: {e}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': f'Submission error: {str(e)}'
        }), 500

@app.route('/submit_project', methods=['GET', 'POST'])
def submit_project():
    if request.method == 'POST':
        print('Received POST request to /submit_project')
        print('Form data:', request.form)
        print('Files:', request.files)
        submission_method = request.form.get('submission_method')
        print('Submission method:', submission_method)
        file = request.files.get('file')
        file_path = None
        filename = None
        project_data = None
        
        if submission_method == 'audio':
            if not file or not file.filename:
                flash('Please upload an audio file for audio submission.')
                return render_template('submit_project.html')
                
            filename = secure_filename(file.filename)
            print(f'Processing audio file: {filename}')
            
            # Check if file type is allowed before saving
            if not allowed_file(filename, 'audio'):
                flash('Invalid file type. Please upload an audio file in supported formats (MP3, WAV, M4A, AAC, FLAC, OGG, WMA, WebM).')
                return render_template('submit_project.html')
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f'File saved to: {file_path}')
            
            # Process the audio file for transcription only
            from audio_processor import AudioProcessor
            processor = AudioProcessor()
            transcript_data = processor.transcribe_audio_only(file_path)
            
            if not transcript_data or transcript_data.get('error'):
                flash('Failed to transcribe audio file. Please try again or use text submission.')
                return render_template('submit_project.html')
            
            print(f'Audio transcription successful. Transcript data: {transcript_data}')
            
            # Store transcript data in session and redirect to transcript review
            session['transcript_data'] = transcript_data
            session['file_path'] = filename
            return redirect(url_for('review_transcript'))
        
        elif submission_method == 'video':
            if not file or not file.filename:
                flash('Please upload a video file for video submission.')
                return render_template('submit_project.html')
                
            filename = secure_filename(file.filename)
            print(f'Processing video file: {filename}')
            
            # Check if file type is allowed before saving
            if not allowed_file(filename, 'video'):
                flash('Invalid file type. Please upload a video file in supported formats (MP4, MOV, AVI, MKV).')
                return render_template('submit_project.html')
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f'File saved to: {file_path}')
            
            # Process the video file
            project_data = process_ai_submission(file_path, 'video')
            if not project_data:
                flash('Failed to process video file. Please try again or use text submission.')
                return render_template('submit_project.html')
            
            print(f'Video processing successful. Project data: {project_data}')
        
        elif submission_method == 'text':
            title = request.form.get('title', '')
            description = request.form.get('description', '')
            if not title or not description:
                flash('Please provide the required information: Project Title and Description are required.')
                return render_template('submit_project.html')
            budget_min_str = request.form.get('budget_min', '')
            budget_max_str = request.form.get('budget_max', '')
            budget_min = float(budget_min_str) if budget_min_str.strip() and budget_min_str.strip().replace('.','',1).isdigit() else None
            budget_max = float(budget_max_str) if budget_max_str.strip() and budget_max_str.strip().replace('.','',1).isdigit() else None
            project_data = {
                'title': title,
                'project_type': request.form.get('project_type', 'General'),
                'location': request.form.get('location', ''),
                'description': description,
                'budget_min': budget_min,
                'budget_max': budget_max,
                'timeline': request.form.get('timeline', ''),
                'transcribed_text': description,
                'confidence': 1.0
            }
            print(f'Text processing successful. Project data: {project_data}')
        
        if project_data:
            session['ai_results'] = project_data  # Using same key for consistency
            session['file_path'] = filename if submission_method in ['audio', 'video'] else None
            print(f'Session data set: ai_results={bool(project_data)}, file_path={filename}')
            return redirect(url_for('review_project'))
        else:
            if submission_method == 'audio':
                flash('Failed to process audio file. Please check the file format and try again.')
            elif submission_method == 'video':
                flash('Failed to process video file. Please check the file format and try again.')
            elif submission_method == 'text':
                flash('Please provide the required information: Project Title and Description are required.')
            else:
                flash('Please select a submission method and provide the required information.')
            return render_template('submit_project.html')
    
    return render_template('submit_project.html')

@app.route('/review_transcript')
def review_transcript():
    transcript_data = session.get('transcript_data')
    file_path = session.get('file_path')
    
    if not transcript_data:
        flash('No transcript data found. Please submit an audio file first.')
        return redirect(url_for('submit_project'))
    
    return render_template('review_transcript.html', transcript_data=transcript_data, file_path=file_path)

@app.route('/review_project')
def review_project():
    ai_results = session.get('ai_results')
    file_path = session.get('file_path')
    
    if not ai_results:
        flash('No project data found. Please submit a project first.')
        return redirect(url_for('submit_project'))
    
    return render_template('review_project.html', ai_results=ai_results, file_path=file_path)

@app.route('/confirm_project', methods=['POST'])
@login_required
def confirm_project():
    user = session['user']
    if user['role'] != 'homeowner':
        flash('Only homeowners can submit projects')
        return redirect(url_for('dashboard'))
    
    ai_results = session.get('ai_results', {})
    file_path = session.get('file_path')  # This contains the filename for audio submissions
    
    # Get form data
    title = request.form['title']
    description = request.form['description']
    project_type = request.form['project_type']
    location = request.form['location']
    budget_min = float(request.form['budget_min']) if request.form['budget_min'] else None
    budget_max = float(request.form['budget_max']) if request.form['budget_max'] else None
    timeline = request.form['timeline']
    
    # Prioritize S3 key over local filename for original_file_path
    original_file_path = ai_results.get('s3_key') or file_path
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID from homeowners table
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        flash('Homeowner profile not found. Please contact support.')
        return redirect(url_for('dashboard'))
    homeowner_id = homeowner_result['id']
    
    cursor.execute('''
        INSERT INTO projects (title, description, project_type, location, budget_min, budget_max, timeline, status, original_file_path, ai_processed_text, created_at, homeowner_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active', %s, %s, NOW(), %s)
    ''', (title, description, project_type, location, budget_min, budget_max, timeline, original_file_path, ai_results.get('transcribed_text'), homeowner_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Project submitted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/test_audio')
def test_audio():
    return render_template('test_audio.html')

@app.route('/simple_audio_test')
def simple_audio_test():
    return render_template('simple_audio_test.html')

@app.route('/project/<int:project_id>')
def view_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch project with homeowner information
    cursor.execute('''
        SELECT p.*, u.first_name as homeowner_first_name, u.last_name as homeowner_last_name, h.location as homeowner_location, u.id as homeowner_user_id
        FROM projects p 
        JOIN homeowners h ON p.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id 
        WHERE p.id = %s
    ''', (project_id,))
    project = cursor.fetchone()
    if not project:
        abort(404)
    
    # Create a nested structure for homeowner data to match template expectations
    project['homeowner'] = {
        'first_name': project['homeowner_first_name'],
        'last_name': project['homeowner_last_name'],
        'location': project['homeowner_location']
    }
    # Add homeowner_user_id for template permission checking
    project['homeowner_user_id'] = project['homeowner_user_id']
    
    audio_url = None
    if project['original_file_path']:
        # Check if this is a local file path (starts with 'uploads/')
        if project['original_file_path'].startswith('uploads/'):
            # For locally stored files, generate URL using our uploaded_file route
            import os
            filename = os.path.basename(project['original_file_path'])
            audio_url = url_for('uploaded_file', filename=filename)
        elif s3_client:
            # For S3 stored files
            # Determine the correct bucket based on the file path
            if (project['original_file_path'].startswith('projects/audios/') or 
                project['original_file_path'].startswith('projects/audios/new/')):
                # This is an S3 key for audio files uploaded to homepro0723 bucket
                bucket_name = 'homepro0723'
            else:
                # Use the default configured bucket for other files
                bucket_name = app.config.get('AWS_S3_BUCKET', 'homepro-uploads')
            
            audio_url = s3_client.generate_presigned_url('get_object',
                Params={'Bucket': bucket_name, 'Key': project['original_file_path']},
                ExpiresIn=3600)
        else:
            # Fallback: try to serve as local file
            import os
            filename = os.path.basename(project['original_file_path'])
            audio_url = url_for('uploaded_file', filename=filename)
    
    bids = []
    show_bids = 'user' in session
    bid_count = 0
    user_bid = None
    
    if show_bids:
        user = session['user']
        
        # Get total bid count for all users
        cursor.execute('SELECT COUNT(*) as count FROM bids WHERE project_id = %s', (project_id,))
        bid_count = cursor.fetchone()['count']
        
        if user['role'] == 'homeowner':
            # Homeowners can see all bid details for their own projects
            cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
            homeowner_result = cursor.fetchone()
            
            if homeowner_result and homeowner_result['id'] == project['homeowner_id']:
                # This homeowner owns the project, show all bids
                cursor.execute('''
                    SELECT b.*, u.first_name as contractor_first_name, u.last_name as contractor_last_name, 
                           c.location as contractor_location, c.company as contractor_company, c.user_id as contractor_user_id
                    FROM bids b 
                    JOIN contractors c ON b.contractor_id = c.id
                    JOIN users u ON c.user_id = u.id 
                    WHERE b.project_id = %s 
                    ORDER BY b.amount ASC
                ''', (project_id,))
                bids_raw = cursor.fetchall()
                
                # Create nested structure for contractor data
                for bid in bids_raw:
                    bid['contractor'] = {
                        'id': bid['contractor_id'],
                        'first_name': bid['contractor_first_name'],
                        'last_name': bid['contractor_last_name'],
                        'location': bid['contractor_location'],
                        'company': bid['contractor_company'],
                        'user_id': bid['contractor_user_id']
                    }
                    bids.append(bid)
        
        elif user['role'] == 'contractor':
            # Contractors can only see their own bid details
            cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
            contractor_result = cursor.fetchone()
            
            if contractor_result:
                contractor_id = contractor_result['id']
                # Get only this contractor's bid
                cursor.execute('''
                    SELECT b.*, u.first_name as contractor_first_name, u.last_name as contractor_last_name, 
                           c.location as contractor_location, c.company as contractor_company, c.user_id as contractor_user_id
                    FROM bids b 
                    JOIN contractors c ON b.contractor_id = c.id
                    JOIN users u ON c.user_id = u.id 
                    WHERE b.project_id = %s AND b.contractor_id = %s
                ''', (project_id, contractor_id))
                user_bid_raw = cursor.fetchone()
                
                if user_bid_raw:
                    user_bid_raw['contractor'] = {
                        'id': user_bid_raw['contractor_id'],
                        'first_name': user_bid_raw['contractor_first_name'],
                        'last_name': user_bid_raw['contractor_last_name'],
                        'location': user_bid_raw['contractor_location'],
                        'company': user_bid_raw['contractor_company'],
                        'user_id': user_bid_raw['contractor_user_id']
                    }
                    user_bid = user_bid_raw
                    bids.append(user_bid_raw)  # Only show their own bid
    
    # Fetch reviews for this project (if completed)
    reviews = []
    if project['status'] == 'Completed':
        cursor.execute('''
            SELECT r.*, u.first_name as homeowner_first_name, u.last_name as homeowner_last_name
            FROM reviews r
            JOIN homeowners h ON r.homeowner_id = h.id
            JOIN users u ON h.user_id = u.id
            WHERE r.project_id = %s
            ORDER BY r.created_at DESC
        ''', (project_id,))
        reviews = cursor.fetchall()
    
    # Fetch project progress status
    cursor.execute('''
        SELECT ps.*, u.first_name, u.last_name
        FROM project_status ps
        LEFT JOIN users u ON ps.updated_by = u.id
        WHERE ps.project_id = %s
        ORDER BY ps.updated_at DESC
        LIMIT 1
    ''', (project_id,))
    project_status = cursor.fetchone()
    
    # Fetch accepted bid information
    cursor.execute('''
        SELECT b.*, u.first_name as contractor_first_name, u.last_name as contractor_last_name, 
               c.location as contractor_location, c.company as contractor_company, c.id as contractor_id
        FROM bids b 
        JOIN contractors c ON b.contractor_id = c.id
        JOIN users u ON c.user_id = u.id 
        WHERE b.project_id = %s AND b.status = 'Accepted'
    ''', (project_id,))
    accepted_bid = cursor.fetchone()
    
    if accepted_bid:
        accepted_bid['contractor'] = {
            'id': accepted_bid['contractor_id'],
            'first_name': accepted_bid['contractor_first_name'],
            'last_name': accepted_bid['contractor_last_name'],
            'location': accepted_bid['contractor_location'],
            'company': accepted_bid['contractor_company']
        }
    
    # Fetch project images
    cursor.execute('''
        SELECT * FROM project_images 
        WHERE project_id = %s 
        ORDER BY image_order ASC, created_at ASC
    ''', (project_id,))
    project_images = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('project_detail.html', 
                         project=project, 
                         bids=bids, 
                         show_bids=show_bids, 
                         bid_count=bid_count,
                         user_bid=user_bid,
                         audio_url=audio_url, 
                         reviews=reviews,
                         project_status=project_status,
                         accepted_bid=accepted_bid,
                         project_images=project_images)

@app.route('/submit_bid/<int:project_id>', methods=['POST'])
@login_required
def submit_bid(project_id):
    user = session['user']
    if user['role'] != 'contractor':
        flash('Only contractors can submit bids')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID from contractors table
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        flash('Contractor profile not found. Please contact support.')
        return redirect(url_for('dashboard'))
    contractor_id = contractor_result['id']
    
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        abort(404)
    
    cursor.execute('SELECT * FROM bids WHERE project_id = %s AND contractor_id = %s', (project_id, contractor_id))
    existing_bid = cursor.fetchone()
    if existing_bid:
        flash('You have already submitted a bid for this project')
        return redirect(url_for('view_project', project_id=project_id))
    
    amount = float(request.form['amount'])
    timeline = request.form['timeline']
    description = request.form['description']
    
    # Calculate expiration date (30 days from now)
    expires_at = calculate_bid_expiration(30)
    
    cursor.execute('''
        INSERT INTO bids (amount, timeline, description, status, created_at, expires_at, project_id, contractor_id)
        VALUES (%s, %s, %s, 'Submitted', NOW(), %s, %s, %s)
    ''', (amount, timeline, description, expires_at, project_id, contractor_id))
    
    bid_id = cursor.lastrowid
    conn.commit()
    
    # Add history entry
    add_bid_history(bid_id, 'Created', None, 'Submitted', None, amount, 
                   f'Initial bid submission: {description[:100]}...', user['id'])
    
    # Send notification (placeholder)
    send_bid_notification(bid_id, 'Bid Submitted')
    
    cursor.close()
    conn.close()
    
    flash('Bid submitted successfully!')
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/edit_bid/<int:bid_id>', methods=['POST'])
@login_required
def edit_bid(bid_id):
    user = session['user']
    if user['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Only contractors can edit bids'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID from contractors table
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Contractor profile not found'}), 404
    contractor_id = contractor_result['id']
    
    # Check if the bid exists and belongs to the current contractor
    cursor.execute('SELECT * FROM bids WHERE id = %s AND contractor_id = %s', (bid_id, contractor_id))
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found or you do not have permission to edit it'}), 404
    
    # Check if the bid is still in 'Submitted' status (can only edit submitted bids)
    if bid['status'] != 'Submitted':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'You can only edit bids that are still pending review'}), 400
    
    try:
        amount = float(request.form['amount'])
        timeline = request.form['timeline']
        description = request.form['description']
        
        # Store old values for history
        old_amount = bid['amount']
        old_timeline = bid['timeline']
        old_description = bid['description']
        
        # Update the bid
        cursor.execute('''
            UPDATE bids 
            SET amount = %s, timeline = %s, description = %s
            WHERE id = %s
        ''', (amount, timeline, description, bid_id))
        conn.commit()
        
        # Add history entry
        add_bid_history(bid_id, 'Updated', bid['status'], bid['status'], 
                       old_amount, amount, 
                       f'Bid updated by contractor. Timeline changed from "{old_timeline}" to "{timeline}"', 
                       user['id'])
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bid updated successfully!'})
        
    except ValueError:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid bid amount. Please enter a valid number.'}), 400
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'An error occurred while updating your bid. Please try again.'}), 500

@app.route('/accept_bid/<int:bid_id>', methods=['POST'])
@login_required
def accept_bid(bid_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID from homeowners table
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Homeowner profile not found'}), 404
    homeowner_id = homeowner_result['id']
    
    cursor.execute('SELECT * FROM bids WHERE id = %s', (bid_id,))
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        abort(404)
    
    cursor.execute('SELECT * FROM projects WHERE id = %s', (bid['project_id'],))
    project = cursor.fetchone()
    
    if project['homeowner_id'] != homeowner_id:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'You can only accept bids for your own projects'}), 403
    
    if project['status'] != 'Active':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'This project is no longer active'}), 400
    
    # Store old status for history
    old_status = bid['status']
    
    cursor.execute("UPDATE bids SET status = 'Accepted' WHERE id = %s", (bid_id,))
    cursor.execute("UPDATE bids SET status = 'Rejected' WHERE project_id = %s AND id != %s AND status = 'Submitted'", (project['id'], bid_id))
    conn.commit()
    
    # Add history entry for accepted bid
    add_bid_history(bid_id, 'Accepted', old_status, 'Accepted', 
                   notes=f'Bid accepted by homeowner', created_by=user['id'])
    
    # Add history entries for rejected bids
    cursor.execute("SELECT id FROM bids WHERE project_id = %s AND id != %s AND status = 'Rejected'", (project['id'], bid_id))
    rejected_bids = cursor.fetchall()
    for rejected_bid in rejected_bids:
        add_bid_history(rejected_bid['id'], 'Auto-Rejected', 'Submitted', 'Rejected', 
                       notes=f'Automatically rejected when bid {bid_id} was accepted', created_by=user['id'])
    
    # Send notifications
    send_bid_notification(bid_id, 'Bid Accepted')
    for rejected_bid in rejected_bids:
        send_bid_notification(rejected_bid['id'], 'Bid Rejected')
    
    cursor.close()
    conn.close()
    
    # Note: To get contractor name, would need to join users table, but simplifying by not including name in message
    return jsonify({'success': True, 'message': 'Bid accepted successfully!'})

@app.route('/reject_bid/<int:bid_id>', methods=['POST'])
@login_required
def reject_bid(bid_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID from homeowners table
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Homeowner profile not found'}), 404
    homeowner_id = homeowner_result['id']
    
    cursor.execute('SELECT * FROM bids WHERE id = %s', (bid_id,))
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        abort(404)
    
    cursor.execute('SELECT * FROM projects WHERE id = %s', (bid['project_id'],))
    project = cursor.fetchone()
    
    if project['homeowner_id'] != homeowner_id:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'You can only reject bids for your own projects'}), 403
    
    # Store old status for history
    old_status = bid['status']
    
    cursor.execute("UPDATE bids SET status = 'Rejected' WHERE id = %s", (bid_id,))
    conn.commit()
    
    # Add history entry
    add_bid_history(bid_id, 'Rejected', old_status, 'Rejected', 
                   notes=f'Bid rejected by homeowner', created_by=user['id'])
    
    # Send notification
    send_bid_notification(bid_id, 'Bid Rejected')
    
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Bid rejected successfully'})

@app.route('/withdraw_bid/<int:bid_id>', methods=['POST'])
@login_required
def withdraw_bid(bid_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID from contractors table
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Contractor profile not found'}), 404
    contractor_id = contractor_result['id']
    
    # Check if the bid exists and belongs to the current contractor
    cursor.execute('SELECT * FROM bids WHERE id = %s AND contractor_id = %s', (bid_id, contractor_id))
    bid = cursor.fetchone()
    if not bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Bid not found or you do not have permission to withdraw it'}), 404
    
    # Check if the bid can be withdrawn (only submitted bids can be withdrawn)
    if bid['status'] != 'Submitted':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'You can only withdraw bids that are still pending review'}), 400
    
    # Get withdrawal reason from request
    withdrawal_reason = request.form.get('reason', 'No reason provided')
    
    # Store old status for history
    old_status = bid['status']
    
    # Update bid status and add withdrawal information
    cursor.execute('''
        UPDATE bids 
        SET status = 'Withdrawn', withdrawn_at = NOW(), withdrawal_reason = %s
        WHERE id = %s
    ''', (withdrawal_reason, bid_id))
    conn.commit()
    
    # Add history entry
    add_bid_history(bid_id, 'Withdrawn', old_status, 'Withdrawn', 
                   notes=f'Bid withdrawn by contractor. Reason: {withdrawal_reason}', 
                   created_by=user['id'])
    
    # Send notification
    send_bid_notification(bid_id, 'Bid Withdrawn')
    
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Bid withdrawn successfully'})

@app.route('/bid_history/<int:bid_id>')
@login_required
def bid_history(bid_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user has permission to view this bid's history
    if user['role'] == 'contractor':
        cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
        contractor_result = cursor.fetchone()
        if contractor_result:
            cursor.execute('SELECT * FROM bids WHERE id = %s AND contractor_id = %s', (bid_id, contractor_result['id']))
            bid = cursor.fetchone()
            if not bid:
                cursor.close()
                conn.close()
                abort(403)
    elif user['role'] == 'homeowner':
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if homeowner_result:
            cursor.execute('''
                SELECT b.* FROM bids b 
                JOIN projects p ON b.project_id = p.id 
                WHERE b.id = %s AND p.homeowner_id = %s
            ''', (bid_id, homeowner_result['id']))
            bid = cursor.fetchone()
            if not bid:
                cursor.close()
                conn.close()
                abort(403)
    else:
        cursor.close()
        conn.close()
        abort(403)
    
    # Get bid history
    cursor.execute('''
        SELECT bh.*, u.first_name, u.last_name 
        FROM bid_history bh
        LEFT JOIN users u ON bh.created_by = u.id
        WHERE bh.bid_id = %s
        ORDER BY bh.created_at DESC
    ''', (bid_id,))
    history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('bid_history.html', bid=bid, history=history)

@app.route('/update_project_progress/<int:project_id>', methods=['POST'])
@login_required
def update_project_progress(project_id):
    """Update project progress in 10% increments"""
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get project details
        cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
        project = cursor.fetchone()
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        # Check if project has an accepted bid
        cursor.execute("SELECT * FROM bids WHERE project_id = %s AND status = 'Accepted'", (project_id,))
        accepted_bid = cursor.fetchone()
        if not accepted_bid:
            return jsonify({'success': False, 'message': 'Project must have an accepted bid before progress can be updated'}), 400
        
        # Check permissions based on user role
        can_update = False
        if user['role'] == 'homeowner':
            # Get homeowner ID and check if they own the project
            cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
            homeowner_result = cursor.fetchone()
            if homeowner_result and homeowner_result['id'] == project['homeowner_id']:
                can_update = True
        elif user['role'] == 'contractor':
            # Get contractor ID and check if they have the accepted bid
            cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
            contractor_result = cursor.fetchone()
            if contractor_result and contractor_result['id'] == accepted_bid['contractor_id']:
                can_update = True
        
        if not can_update:
            return jsonify({'success': False, 'message': 'You do not have permission to update this project progress'}), 403
        
        # Get progress data from request
        progress_percentage = request.json.get('progress_percentage')
        update_notes = request.json.get('update_notes', '').strip()
        
        # Validate progress percentage
        if progress_percentage is None or not isinstance(progress_percentage, int):
            return jsonify({'success': False, 'message': 'Progress percentage must be a number'}), 400
        
        if progress_percentage < 0 or progress_percentage > 100 or progress_percentage % 10 != 0:
            return jsonify({'success': False, 'message': 'Progress must be in 10% increments (0, 10, 20, ..., 100)'}), 400
        
        # Get current progress
        cursor.execute('SELECT progress_percentage FROM project_status WHERE project_id = %s ORDER BY updated_at DESC LIMIT 1', (project_id,))
        current_progress = cursor.fetchone()
        current_percentage = current_progress['progress_percentage'] if current_progress else 0
        
        # Don't allow going backwards in progress
        if progress_percentage < current_percentage:
            return jsonify({'success': False, 'message': 'Progress cannot go backwards'}), 400
        
        # Insert new progress update
        cursor.execute('''
            INSERT INTO project_status (project_id, progress_percentage, update_notes, updated_by, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
        ''', (project_id, progress_percentage, update_notes, user['id']))
        
        # Update project status based on progress
        if progress_percentage == 100:
            cursor.execute("UPDATE projects SET status = 'Completed' WHERE id = %s", (project_id,))
        elif progress_percentage > 0:
            cursor.execute("UPDATE projects SET status = 'In Progress' WHERE id = %s", (project_id,))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Project progress updated successfully!',
            'progress_percentage': progress_percentage,
            'update_notes': update_notes
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error updating progress: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/complete_project/<int:project_id>', methods=['POST'])
@login_required
def complete_project(project_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        cursor.close()
        conn.close()
        abort(404)
    
    cursor.execute("SELECT * FROM bids WHERE project_id = %s AND status = 'Accepted'", (project_id,))
    accepted_bid = cursor.fetchone()
    
    # Check permissions based on user role
    can_complete = False
    if user['role'] == 'homeowner':
        # Get homeowner ID and check if they own the project
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if homeowner_result and homeowner_result['id'] == project['homeowner_id']:
            can_complete = True
    elif user['role'] == 'contractor' and accepted_bid:
        # Get contractor ID and check if they have the accepted bid
        cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
        contractor_result = cursor.fetchone()
        if contractor_result and contractor_result['id'] == accepted_bid['contractor_id']:
            can_complete = True
    
    if not can_complete:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'You do not have permission to complete this project'}), 403
    
    if not accepted_bid:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Project must have an accepted bid before it can be completed'}), 400
    
    cursor.execute("UPDATE projects SET status = 'Completed' WHERE id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project marked as completed successfully!'})

@app.route('/submit_review/<int:project_id>', methods=['POST'])
@login_required
def submit_review(project_id):
    """Submit a review for a completed project"""
    user = session['user']
    
    if user['role'] != 'homeowner':
        return jsonify({'success': False, 'message': 'Only homeowners can submit reviews'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get homeowner ID
        cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
        homeowner_result = cursor.fetchone()
        if not homeowner_result:
            return jsonify({'success': False, 'message': 'Homeowner profile not found'}), 404
        homeowner_id = homeowner_result['id']
        
        # Verify project exists and belongs to homeowner
        cursor.execute('SELECT * FROM projects WHERE id = %s AND homeowner_id = %s', (project_id, homeowner_id))
        project = cursor.fetchone()
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
        
        # Check if project is completed
        if project['status'] != 'Completed':
            return jsonify({'success': False, 'message': 'You can only review completed projects'}), 400
        
        # Get the accepted bid to find the contractor
        cursor.execute('SELECT contractor_id FROM bids WHERE project_id = %s AND status = "Accepted"', (project_id,))
        bid_result = cursor.fetchone()
        if not bid_result:
            return jsonify({'success': False, 'message': 'No accepted contractor found for this project'}), 400
        contractor_id = bid_result['contractor_id']
        
        # Check if review already exists
        cursor.execute('SELECT id FROM reviews WHERE project_id = %s AND contractor_id = %s', (project_id, contractor_id))
        existing_review = cursor.fetchone()
        if existing_review:
            return jsonify({'success': False, 'message': 'You have already reviewed this project'}), 400
        
        # Get review data from request
        rating = request.json.get('rating')
        review_text = request.json.get('review_text', '').strip()
        
        # Validate rating
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400
        
        # Insert review
        cursor.execute('''
            INSERT INTO reviews (project_id, contractor_id, homeowner_id, rating, review_text)
            VALUES (%s, %s, %s, %s, %s)
        ''', (project_id, contractor_id, homeowner_id, rating, review_text))
        
        # Update contractor's average rating and rating count
        cursor.execute('''
            SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
            FROM reviews WHERE contractor_id = %s
        ''', (contractor_id,))
        rating_stats = cursor.fetchone()
        
        cursor.execute('''
            UPDATE contractors 
            SET average_rating = %s, rating_count = %s
            WHERE id = %s
        ''', (round(rating_stats['avg_rating'], 1), rating_stats['review_count'], contractor_id))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Review submitted successfully!',
            'new_average': round(rating_stats['avg_rating'], 1),
            'review_count': rating_stats['review_count']
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error submitting review: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/close_project/<int:project_id>', methods=['POST'])
@login_required
def close_project(project_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get homeowner ID from homeowners table
    cursor.execute('SELECT id FROM homeowners WHERE user_id = %s', (user['id'],))
    homeowner_result = cursor.fetchone()
    if not homeowner_result:
        cursor.close()
        conn.close()
        flash('Homeowner profile not found. Please contact support.')
        return redirect(url_for('dashboard'))
    homeowner_id = homeowner_result['id']
    
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        cursor.close()
        conn.close()
        abort(404)
    
    if project['homeowner_id'] != homeowner_id:
        cursor.close()
        conn.close()
        flash('You can only close your own projects')
        return redirect(url_for('dashboard'))
    
    cursor.execute("UPDATE projects SET status = 'Closed' WHERE id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Project closed successfully!')
    return redirect(url_for('dashboard'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Stream uploaded files from the uploads directory or static/uploads"""
    import os
    import mimetypes
    from flask import Response
    
    # Try multiple possible paths
    possible_paths = [
        os.path.join(app.config['UPLOAD_FOLDER'], filename),  # uploads/filename
        os.path.join(os.getcwd(), 'static', 'uploads', filename),  # static/uploads/filename
        os.path.join(os.getcwd(), 'static', filename)  # static/filename (for paths like uploads/projects/filename)
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        abort(404)
    
    # Determine MIME type based on file extension
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # Default fallback based on common file extensions
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif ext == 'png':
            mime_type = 'image/png'
        elif ext == 'gif':
            mime_type = 'image/gif'
        elif ext == 'webp':
            mime_type = 'image/webp'
        elif ext in ['mp3', 'mpeg']:
            mime_type = 'audio/mpeg'
        elif ext == 'wav':
            mime_type = 'audio/wav'
        elif ext == 'webm':
            mime_type = 'audio/webm'
        else:
            mime_type = 'application/octet-stream'
    
    def generate():
        with open(file_path, "rb") as f:
            data = f.read(1024)
            while data:
                yield data
                data = f.read(1024)
    return Response(generate(), mimetype=mime_type)

# ============================================================================
# CONTRACTOR MANAGEMENT SYSTEM ROUTES
# ============================================================================

@app.route('/contractor/profile')
@login_required
def contractor_profile():
    """Contractor profile management page"""
    user = session['user']
    
    if user['role'] != 'contractor':
        flash('Access denied. Contractor account required.')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor profile with enhanced fields
    cursor.execute('''
        SELECT c.*, u.first_name, u.last_name, u.email
        FROM contractors c
        JOIN users u ON c.user_id = u.id
        WHERE c.user_id = %s
    ''', (user['id'],))
    contractor = cursor.fetchone()
    
    if not contractor:
        flash('Contractor profile not found.')
        return redirect(url_for('dashboard'))
    
    # Get recent reviews
    cursor.execute('''
        SELECT r.*, p.title as project_title,
               CONCAT(u.first_name, ' ', u.last_name) as homeowner_name
        FROM reviews r
        JOIN projects p ON r.project_id = p.id
        JOIN homeowners h ON r.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        WHERE r.contractor_id = %s
        ORDER BY r.created_at DESC
        LIMIT 10
    ''', (contractor['id'],))
    reviews = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('contractor/profile.html', contractor=contractor, reviews=reviews)

@app.route('/contractor/profile/update', methods=['POST'])
@login_required
def update_contractor_profile():
    """Update contractor profile information"""
    user = session['user']
    
    if user['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get contractor ID
        cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
        contractor_result = cursor.fetchone()
        if not contractor_result:
            return jsonify({'success': False, 'message': 'Contractor profile not found'}), 404
        contractor_id = contractor_result['id']
        
        # Get form data
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        specialties = request.form.get('specialties', '').strip()
        bio = request.form.get('bio', '').strip()
        years_experience = request.form.get('years_experience', 0, type=int)
        business_info = request.form.get('business_info', '').strip()
        portfolio = request.form.get('portfolio', '').strip()
        
        # Update contractor profile
        cursor.execute('''
            UPDATE contractors 
            SET company = %s, location = %s, specialties = %s, bio = %s,
                years_experience = %s, business_info = %s, portfolio = %s
            WHERE id = %s
        ''', (company, location, specialties, bio, years_experience, business_info, portfolio, contractor_id))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/contractor/availability')
@login_required
def contractor_availability():
    """Contractor availability calendar page"""
    user = session['user']
    
    if user['role'] != 'contractor':
        flash('Access denied. Contractor account required.')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        flash('Contractor profile not found.')
        return redirect(url_for('dashboard'))
    contractor_id = contractor_result['id']
    
    # Get availability data for the next 3 months
    from datetime import datetime, timedelta
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=90)
    
    cursor.execute('''
        SELECT * FROM contractor_availability
        WHERE contractor_id = %s AND available_date BETWEEN %s AND %s
        ORDER BY available_date
    ''', (contractor_id, start_date, end_date))
    availability = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('contractor/availability.html', availability=availability)

@app.route('/contractor/availability/update', methods=['POST'])
@login_required
def update_contractor_availability():
    """Update contractor availability for specific dates"""
    user = session['user']
    
    if user['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get contractor ID
        cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
        contractor_result = cursor.fetchone()
        if not contractor_result:
            return jsonify({'success': False, 'message': 'Contractor profile not found'}), 404
        contractor_id = contractor_result['id']
        
        # Get form data
        date = request.json.get('date')
        status = request.json.get('status', 'available')
        notes = request.json.get('notes', '').strip()
        
        # Validate date
        from datetime import datetime
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format'}), 400
        
        # Validate status
        if status not in ['available', 'busy', 'unavailable']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        # Update or insert availability
        cursor.execute('''
            INSERT INTO contractor_availability (contractor_id, available_date, status, notes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
        ''', (contractor_id, date_obj, status, notes, status, notes))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Availability updated successfully!'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error updating availability: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/contractor/messages')
@login_required
def contractor_messages():
    """Contractor messages page for managing bid conversations"""
    user = session['user']
    
    if user['role'] != 'contractor':
        flash('Access denied. Contractor account required.')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (user['id'],))
    contractor_result = cursor.fetchone()
    if not contractor_result:
        flash('Contractor profile not found.')
        return redirect(url_for('dashboard'))
    contractor_id = contractor_result['id']
    
    cursor.close()
    conn.close()
    
    return render_template('contractor_messages.html', contractor_id=contractor_id)

@app.route('/contractor/<int:contractor_id>/reviews')
def contractor_reviews(contractor_id):
    """Public page showing contractor reviews and ratings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor info
    cursor.execute('''
        SELECT c.*, u.first_name, u.last_name
        FROM contractors c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = %s
    ''', (contractor_id,))
    contractor = cursor.fetchone()
    
    if not contractor:
        abort(404)
    
    # Get reviews with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    cursor.execute('''
        SELECT r.*, p.title as project_title,
               CONCAT(u.first_name, ' ', u.last_name) as homeowner_name,
               rr.reply_text, rr.created_at as reply_created_at
        FROM reviews r
        JOIN projects p ON r.project_id = p.id
        JOIN homeowners h ON r.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        LEFT JOIN review_replies rr ON r.id = rr.review_id
        WHERE r.contractor_id = %s
        ORDER BY r.created_at DESC
        LIMIT %s OFFSET %s
    ''', (contractor_id, per_page, offset))
    reviews = cursor.fetchall()
    
    # Get total review count
    cursor.execute('SELECT COUNT(*) as total FROM reviews WHERE contractor_id = %s', (contractor_id,))
    total_reviews = cursor.fetchone()['total']
    
    # Get rating distribution
    cursor.execute('''
        SELECT rating, COUNT(*) as count
        FROM reviews
        WHERE contractor_id = %s
        GROUP BY rating
        ORDER BY rating DESC
    ''', (contractor_id,))
    rating_distribution = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    total_pages = (total_reviews + per_page - 1) // per_page
    
    return render_template('contractor/reviews.html', 
                         contractor=contractor, 
                         reviews=reviews,
                         rating_distribution=rating_distribution,
                         page=page,
                         total_pages=total_pages,
                         total_reviews=total_reviews)

@app.route('/contractor/reply_review/<int:review_id>', methods=['POST'])
@login_required
def reply_to_review(review_id):
    """Handle contractor reply to a review"""
    if session['user']['role'] != 'contractor':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    reply_text = data.get('reply_text', '').strip()
    
    if not reply_text:
        return jsonify({'success': False, 'message': 'Reply text is required'}), 400
    
    if len(reply_text) > 1000:
        return jsonify({'success': False, 'message': 'Reply text is too long (max 1000 characters)'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get contractor ID
    cursor.execute('SELECT id FROM contractors WHERE user_id = %s', (session['user']['id'],))
    contractor = cursor.fetchone()
    if not contractor:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Contractor not found'}), 404
    
    contractor_id = contractor['id']
    
    # Verify the review exists and belongs to this contractor
    cursor.execute('SELECT id, contractor_id FROM reviews WHERE id = %s', (review_id,))
    review = cursor.fetchone()
    if not review:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Review not found'}), 404
    
    if review['contractor_id'] != contractor_id:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Unauthorized to reply to this review'}), 403
    
    try:
        # Check if reply already exists
        cursor.execute('SELECT id FROM review_replies WHERE review_id = %s', (review_id,))
        existing_reply = cursor.fetchone()
        
        if existing_reply:
            # Update existing reply
            cursor.execute('''
                UPDATE review_replies 
                SET reply_text = %s, updated_at = CURRENT_TIMESTAMP
                WHERE review_id = %s AND contractor_id = %s
            ''', (reply_text, review_id, contractor_id))
        else:
            # Insert new reply
            cursor.execute('''
                INSERT INTO review_replies (review_id, contractor_id, reply_text)
                VALUES (%s, %s, %s)
            ''', (review_id, contractor_id, reply_text))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Reply submitted successfully'})
    
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Failed to submit reply'}), 500

# ============================================================================
# ADMIN PORTAL ROUTES
# ============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin Dashboard Overview with real-time platform statistics"""
    user = session['user']
    admin_level = get_admin_level(user['id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get platform statistics
    stats = {}
    
    # User statistics
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    stats['total_users'] = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as total_homeowners FROM homeowners')
    stats['total_homeowners'] = cursor.fetchone()['total_homeowners']
    
    cursor.execute('SELECT COUNT(*) as total_contractors FROM contractors')
    stats['total_contractors'] = cursor.fetchone()['total_contractors']
    
    # Project statistics
    cursor.execute('SELECT COUNT(*) as total_projects FROM projects')
    stats['total_projects'] = cursor.fetchone()['total_projects']
    
    cursor.execute("SELECT COUNT(*) as active_projects FROM projects WHERE status = 'Active'")
    stats['active_projects'] = cursor.fetchone()['active_projects']
    
    cursor.execute("SELECT COUNT(*) as completed_projects FROM projects WHERE status = 'Completed'")
    stats['completed_projects'] = cursor.fetchone()['completed_projects']
    
    # Bid statistics
    cursor.execute('SELECT COUNT(*) as total_bids FROM bids')
    stats['total_bids'] = cursor.fetchone()['total_bids']
    
    cursor.execute("SELECT COUNT(*) as pending_bids FROM bids WHERE status = 'Submitted'")
    stats['pending_bids'] = cursor.fetchone()['pending_bids']
    
    cursor.execute("SELECT COUNT(*) as accepted_bids FROM bids WHERE status = 'Accepted'")
    stats['accepted_bids'] = cursor.fetchone()['accepted_bids']
    
    # Revenue statistics (mock data for now)
    cursor.execute('SELECT SUM(amount) as total_bid_value FROM bids WHERE status = "Accepted"')
    result = cursor.fetchone()
    stats['total_revenue'] = result['total_bid_value'] if result['total_bid_value'] else 0
    
    # Recent activity
    cursor.execute('''
        SELECT u.first_name, u.last_name, u.email, u.role, u.created_at
        FROM users u
        ORDER BY u.created_at DESC
        LIMIT 10
    ''')
    recent_users = cursor.fetchall()
    
    cursor.execute('''
        SELECT p.title, p.project_type, p.created_at, 
               CONCAT(u.first_name, ' ', u.last_name) as homeowner_name
        FROM projects p
        JOIN homeowners h ON p.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        ORDER BY p.created_at DESC
        LIMIT 10
    ''')
    recent_projects = cursor.fetchall()
    
    # Pending verifications
    cursor.execute('''
        SELECT COUNT(*) as pending_verifications 
        FROM user_verification 
        WHERE status = 'pending'
    ''')
    stats['pending_verifications'] = cursor.fetchone()['pending_verifications']
    
    # Pending content moderation
    cursor.execute('''
        SELECT COUNT(*) as pending_moderation 
        FROM content_moderation 
        WHERE status = 'pending'
    ''')
    stats['pending_moderation'] = cursor.fetchone()['pending_moderation']
    
    cursor.close()
    conn.close()
    
    # Log admin activity
    log_admin_activity(user['id'], 'Viewed Admin Dashboard', 'system')
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_projects=recent_projects,
                         admin_level=admin_level)

@app.route('/admin/users')
@admin_required
def admin_users():
    """User Management System"""
    user = session['user']
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    where_conditions = []
    params = []
    
    if search:
        where_conditions.append('(u.first_name LIKE %s OR u.last_name LIKE %s OR u.email LIKE %s)')
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if role_filter:
        where_conditions.append('u.role = %s')
        params.append(role_filter)
    
    where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # Get total count
    cursor.execute(f'SELECT COUNT(*) as total FROM users u {where_clause}', params)
    total_users = cursor.fetchone()['total']
    
    # Get paginated users
    offset = (page - 1) * per_page
    cursor.execute(f'''
        SELECT u.*, 
               CASE WHEN au.id IS NOT NULL THEN TRUE ELSE FALSE END as is_admin,
               au.admin_level,
               CASE WHEN u.role = 'homeowner' THEN h.location
                    WHEN u.role = 'contractor' THEN c.location
                    ELSE NULL END as location,
               CASE WHEN u.role = 'contractor' THEN c.company ELSE NULL END as company
        FROM users u
        LEFT JOIN admin_users au ON u.id = au.user_id AND au.is_active = TRUE
        LEFT JOIN homeowners h ON u.id = h.user_id
        LEFT JOIN contractors c ON u.id = c.user_id
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s
    ''', params + [per_page, offset])
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Calculate pagination
    total_pages = (total_users + per_page - 1) // per_page
    
    # Log admin activity
    log_admin_activity(user['id'], 'Viewed User Management', 'user')
    
    return render_template('admin/users.html', 
                         users=users,
                         page=page,
                         total_pages=total_pages,
                         total_users=total_users,
                         search=search,
                         role_filter=role_filter)

@app.route('/admin/projects')
@admin_required
def admin_projects():
    """Project Lifecycle Management"""
    user = session['user']
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', '')
    project_type_filter = request.args.get('project_type', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    where_conditions = []
    params = []
    
    if status_filter:
        where_conditions.append('p.status = %s')
        params.append(status_filter)
    
    if project_type_filter:
        where_conditions.append('p.project_type = %s')
        params.append(project_type_filter)
    
    where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # Get total count
    cursor.execute(f'SELECT COUNT(*) as total FROM projects p {where_clause}', params)
    total_projects = cursor.fetchone()['total']
    
    # Get paginated projects
    offset = (page - 1) * per_page
    cursor.execute(f'''
        SELECT p.*, 
               CONCAT(u.first_name, ' ', u.last_name) as homeowner_name,
               u.email as homeowner_email,
               (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id) as bid_count,
               (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id AND b.status = 'Accepted') as accepted_bids
        FROM projects p
        JOIN homeowners h ON p.homeowner_id = h.id
        JOIN users u ON h.user_id = u.id
        {where_clause}
        ORDER BY p.created_at DESC
        LIMIT %s OFFSET %s
    ''', params + [per_page, offset])
    projects = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Calculate pagination
    total_pages = (total_projects + per_page - 1) // per_page
    
    # Log admin activity
    log_admin_activity(user['id'], 'Viewed Project Management', 'project')
    
    return render_template('admin/projects.html', 
                         projects=projects,
                         page=page,
                         total_pages=total_pages,
                         total_projects=total_projects,
                         status_filter=status_filter,
                         project_type_filter=project_type_filter)

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Business Intelligence & Analytics"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # User engagement analytics
    cursor.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as new_users
        FROM users 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    ''')
    user_growth = cursor.fetchall()
    
    # Project success rate metrics
    cursor.execute('''
        SELECT 
            p.status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM projects), 2) as percentage
        FROM projects p
        GROUP BY p.status
    ''')
    project_status_distribution = cursor.fetchall()
    
    # Contractor performance analytics
    cursor.execute('''
        SELECT 
            CONCAT(u.first_name, ' ', u.last_name) as contractor_name,
            c.company,
            COUNT(b.id) as total_bids,
            COUNT(CASE WHEN b.status = 'Accepted' THEN 1 END) as accepted_bids,
            ROUND(COUNT(CASE WHEN b.status = 'Accepted' THEN 1 END) * 100.0 / COUNT(b.id), 2) as success_rate,
            AVG(b.amount) as avg_bid_amount
        FROM contractors c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN bids b ON c.id = b.contractor_id
        GROUP BY c.id, u.first_name, u.last_name, c.company
        HAVING COUNT(b.id) > 0
        ORDER BY success_rate DESC, total_bids DESC
        LIMIT 20
    ''')
    contractor_performance = cursor.fetchall()
    
    # Revenue tracking
    cursor.execute('''
        SELECT 
            DATE_FORMAT(b.created_at, '%Y-%m') as month,
            SUM(CASE WHEN b.status = 'Accepted' THEN b.amount ELSE 0 END) as revenue,
            COUNT(CASE WHEN b.status = 'Accepted' THEN 1 END) as completed_projects
        FROM bids b
        WHERE b.created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(b.created_at, '%Y-%m')
        ORDER BY month DESC
    ''')
    revenue_trends = cursor.fetchall()
    
    # Geographic distribution
    cursor.execute('''
        SELECT 
            COALESCE(h.location, 'Unknown') as location,
            COUNT(*) as homeowner_count
        FROM homeowners h
        GROUP BY h.location
        ORDER BY homeowner_count DESC
        LIMIT 10
    ''')
    homeowner_distribution = cursor.fetchall()
    
    cursor.execute('''
        SELECT 
            COALESCE(c.location, 'Unknown') as location,
            COUNT(*) as contractor_count
        FROM contractors c
        GROUP BY c.location
        ORDER BY contractor_count DESC
        LIMIT 10
    ''')
    contractor_distribution = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Log admin activity
    log_admin_activity(user['id'], 'Viewed Analytics Dashboard', 'system')
    
    return render_template('admin/analytics.html',
                         user_growth=user_growth,
                         project_status_distribution=project_status_distribution,
                         contractor_performance=contractor_performance,
                         revenue_trends=revenue_trends,
                         homeowner_distribution=homeowner_distribution,
                         contractor_distribution=contractor_distribution)

@app.route('/admin/moderation')
@admin_required
def admin_moderation():
    """Content Moderation Interface"""
    user = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get pending content for moderation
    cursor.execute('''
        SELECT cm.*, 
               CASE 
                   WHEN cm.content_type = 'project' THEN p.title
                   WHEN cm.content_type = 'contractor_profile' THEN CONCAT(u.first_name, ' ', u.last_name, ' - ', c.company)
                   ELSE 'Other Content'
               END as content_title,
               CASE 
                   WHEN cm.content_type = 'project' THEN p.description
                   WHEN cm.content_type = 'contractor_profile' THEN c.business_info
                   ELSE NULL
               END as content_description
        FROM content_moderation cm
        LEFT JOIN projects p ON cm.content_type = 'project' AND cm.content_id = p.id
        LEFT JOIN contractors c ON cm.content_type = 'contractor_profile' AND cm.content_id = c.id
        LEFT JOIN users u ON c.user_id = u.id
        WHERE cm.status = 'pending'
        ORDER BY cm.created_at ASC
    ''')
    pending_content = cursor.fetchall()
    
    # Get recent moderation actions
    cursor.execute('''
        SELECT cm.*, 
               CONCAT(u.first_name, ' ', u.last_name) as reviewer_name,
               CASE 
                   WHEN cm.content_type = 'project' THEN p.title
                   WHEN cm.content_type = 'contractor_profile' THEN CONCAT(cu.first_name, ' ', cu.last_name)
                   ELSE 'Other Content'
               END as content_title
        FROM content_moderation cm
        LEFT JOIN admin_users au ON cm.reviewed_by = au.id
        LEFT JOIN users u ON au.user_id = u.id
        LEFT JOIN projects p ON cm.content_type = 'project' AND cm.content_id = p.id
        LEFT JOIN contractors c ON cm.content_type = 'contractor_profile' AND cm.content_id = c.id
        LEFT JOIN users cu ON c.user_id = cu.id
        WHERE cm.status != 'pending'
        ORDER BY cm.reviewed_at DESC
        LIMIT 20
    ''')
    recent_actions = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Log admin activity
    log_admin_activity(user['id'], 'Viewed Content Moderation', 'system')
    
    return render_template('admin/moderation.html',
                         pending_content=pending_content,
                         recent_actions=recent_actions)

@app.route('/admin/user/<int:user_id>/toggle_status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    """Toggle user account status (activate/deactivate)"""
    admin_user = session['user']
    action = request.json.get('action')  # 'activate' or 'deactivate'
    
    if action not in ['activate', 'deactivate']:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user details
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # For now, we'll use a simple approach since we don't have an 'active' column
    # In a production system, you'd add an 'is_active' column to the users table
    
    # Log the action
    log_admin_activity(admin_user['id'], f'User {action.title()}', 'user', user_id, {
        'target_user_email': user['email'],
        'target_user_name': f"{user['first_name']} {user['last_name']}"
    })
    
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': f'User {action}d successfully'})

@app.route('/admin/create_admin', methods=['POST'])
@admin_required
def admin_create_admin():
    """Create new admin user"""
    admin_user = session['user']
    admin_level = get_admin_level(admin_user['id'])
    
    # Only super_admin can create other admins
    if admin_level != 'super_admin':
        return jsonify({'success': False, 'message': 'Only super admins can create admin users'}), 403
    
    user_id = request.json.get('user_id')
    new_admin_level = request.json.get('admin_level', 'admin')
    
    if new_admin_level not in ['super_admin', 'admin', 'moderator']:
        return jsonify({'success': False, 'message': 'Invalid admin level'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Check if user is already an admin
    cursor.execute('SELECT * FROM admin_users WHERE user_id = %s', (user_id,))
    existing_admin = cursor.fetchone()
    if existing_admin:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User is already an admin'}), 400
    
    # Create admin user
    cursor.execute('''
        INSERT INTO admin_users (user_id, admin_level, created_by)
        VALUES (%s, %s, %s)
    ''', (user_id, new_admin_level, admin_user['id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Log the action
    log_admin_activity(admin_user['id'], 'Created Admin User', 'user', user_id, {
        'target_user_email': user['email'],
        'admin_level': new_admin_level
    })
    
    return jsonify({'success': True, 'message': 'Admin user created successfully'})

# def create_demo_users():
#     """Adapted for Cognito - run manually or via script"""

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

if __name__ == '__main__':
    # Initialize database tables
    print("Initializing database...")
    init_database()
    
    # Expire old bids on startup
    print("Checking for expired bids...")
    expired_count = expire_old_bids()
    if expired_count > 0:
        print(f"Expired {expired_count} old bids")
    
    # Cleanup expired guest projects on startup
    print("Cleaning up expired guest projects...")
    cleanup_count = cleanup_expired_guest_projects()
    if cleanup_count > 0:
        print(f"Marked {cleanup_count} expired guest projects")
    
    # Tables should be created in RDS separately
    # create_demo_users()  # If needed, adapt and run separately
    app.run(host='0.0.0.0', port=8000, debug=True)