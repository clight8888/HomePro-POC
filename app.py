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
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
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
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp3', 'wav']
    elif file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov']
    return False

def process_ai_submission(file_path, file_type, text_content=None):
    """
    Process uploaded file or text using AWS AI services
    """
    try:
        print(f"Processing AI submission: file_path={file_path}, file_type={file_type}, AWS_AVAILABLE={AWS_AVAILABLE}")
        transcribed_text = ""
        
        if text_content:
            transcribed_text = text_content
        elif file_type in ['audio', 'video'] and AWS_AVAILABLE:
            # Upload audio files to the specific S3 bucket 'new_audio_files'
            if file_type == 'audio':
                s3_bucket = 'homepro0723'
                s3_key = f"projects/audios/new/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
            else:
                s3_bucket = app.config.get('AWS_S3_BUCKET', 'default-bucket')
                s3_key = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
            s3_client.upload_file(file_path, s3_bucket, s3_key)
            
            print(f"File uploaded to S3 bucket: {s3_bucket}, key: {s3_key}")
            
            # Start transcription job
            job_name = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': f"s3://{s3_bucket}/{s3_key}"},
                MediaFormat=file_path.split('.')[-1].lower(),
                LanguageCode='en-US'
            )
            
            # Wait for transcription to complete (simplified for demo)
            import time
            while True:
                response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    # Download and parse transcript (simplified)
                    transcribed_text = "Sample transcribed text from audio/video"
                    break
                elif status == 'FAILED':
                    raise Exception("Transcription failed")
                time.sleep(5)
        elif file_type in ['audio', 'video'] and not AWS_AVAILABLE:
            # Mock transcription for development
            print("Using mock transcription for development")
            transcribed_text = "Mock transcribed text: I need to fix my kitchen sink. It's been leaking for a week and I think it needs a new faucet. My budget is around $200-500 and I'd like it done within 2 weeks."
        
        print(f"Transcribed text: {transcribed_text}")
        
        # Use Comprehend to analyze the text or mock analysis
        if transcribed_text:
            if AWS_AVAILABLE:
                entities_response = comprehend_client.detect_entities(
                    Text=transcribed_text,
                    LanguageCode='en'
                )
                
                key_phrases_response = comprehend_client.detect_key_phrases(
                    Text=transcribed_text,
                    LanguageCode='en'
                )
            else:
                # Mock responses for development
                entities_response = {'Entities': []}
                key_phrases_response = {'KeyPhrases': []}
            
            # Extract project details (simplified logic)
            project_data = {
                'transcribed_text': transcribed_text,
                'title': extract_project_title(transcribed_text),
                'project_type': extract_project_type(transcribed_text, entities_response),
                'location': extract_location(entities_response),
                'description': transcribed_text,
                'budget_min': extract_budget_range(transcribed_text)[0],
                'budget_max': extract_budget_range(transcribed_text)[1],
                'timeline': extract_timeline(transcribed_text),
                'confidence': 0.85 if AWS_AVAILABLE else 0.75,  # Lower confidence for mock data
                's3_key': s3_key if 's3_key' in locals() else None
            }
            
            print(f"Generated project data: {project_data}")
            return project_data
        else:
            print("No transcribed text available")
            return None
    
    except Exception as e:
        print(f"AI processing error: {e}")
        import traceback
        traceback.print_exc()
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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        location = request.form.get('location', '')
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
            
            # Hash the password
            password_hash = generate_password_hash(password)
            
            # Insert new user into database
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name, role, location, specialties, business_info, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (email, password_hash, first_name, last_name, user_type, location, specialties, business_info, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            
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
            flash('Please log in to access this page')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.context_processor
def inject_user():
    return dict(user=session.get('user'))


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

def init_database():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                role ENUM('homeowner', 'contractor') NOT NULL,
                location VARCHAR(255),
                specialties TEXT,
                business_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_role (role)
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
                FOREIGN KEY (homeowner_id) REFERENCES users(id),
                INDEX idx_status (status),
                INDEX idx_homeowner (homeowner_id),
                INDEX idx_created (created_at)
            )
        ''')
        
        # Create bids table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bids (
                id INT AUTO_INCREMENT PRIMARY KEY,
                amount DECIMAL(10,2) NOT NULL,
                timeline VARCHAR(255),
                description TEXT,
                status ENUM('Submitted', 'Accepted', 'Rejected') DEFAULT 'Submitted',
                project_id INT NOT NULL,
                contractor_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (contractor_id) REFERENCES users(id),
                INDEX idx_project (project_id),
                INDEX idx_contractor (contractor_id),
                INDEX idx_status (status)
            )
        ''')
        
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
        cursor.execute('SELECT p.*, (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id) as bid_count FROM projects p WHERE homeowner_id = %s ORDER BY created_at DESC', (user['id'],))
        projects = cursor.fetchall()
        cursor.execute('SELECT b.*, p.title as project_title FROM bids b JOIN projects p ON b.project_id = p.id WHERE p.homeowner_id = %s ORDER BY b.created_at DESC LIMIT 15', (user['id'],))
        recent_bids = cursor.fetchall()
        template = 'homeowner_dashboard.html'
        render_args = {'projects': projects, 'recent_bids': recent_bids}
    else:
        cursor.execute('SELECT p.*, (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id) as bid_count, (SELECT COUNT(*) FROM bids b WHERE b.project_id = p.id AND b.contractor_id = %s) as has_user_bid FROM projects p WHERE status = \'Active\' ORDER BY created_at DESC', (user['id'],))
        projects = cursor.fetchall()
        cursor.execute('SELECT b.*, p.title, p.project_type FROM bids b JOIN projects p ON b.project_id = p.id WHERE b.contractor_id = %s ORDER BY b.created_at DESC', (user['id'],))
        bids = cursor.fetchall()
        template = 'contractor_dashboard.html'
        render_args = {'projects': projects, 'bids': bids}
    cursor.close()
    conn.close()
    return render_template(template, **render_args)

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
        project_data = None
        
        if submission_method == 'audio':
            if not file or not file.filename:
                flash('Please upload an audio file for audio submission.')
                return render_template('submit_project.html')
                
            filename = secure_filename(file.filename)
            print(f'Processing audio file: {filename}')
            
            # Check if file type is allowed before saving
            if not allowed_file(filename, 'audio'):
                flash('Invalid file type. Please upload an MP3 or WAV audio file.')
                return render_template('submit_project.html')
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f'File saved to: {file_path}')
            
            # Process the audio file
            project_data = process_ai_submission(file_path, 'audio')
            if not project_data:
                flash('Failed to process audio file. Please try again or use text submission.')
                return render_template('submit_project.html')
        
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
        
        if project_data:
            session['ai_results'] = project_data  # Using same key for consistency
            session['file_path'] = filename if submission_method == 'audio' else None
            return redirect(url_for('review_project'))
        else:
            if submission_method == 'audio':
                flash('Failed to process audio file. Please check the file format and try again.')
            elif submission_method == 'text':
                flash('Please provide the required information: Project Title and Description are required.')
            else:
                flash('Please select a submission method and provide the required information.')
            return render_template('submit_project.html')
    
    return render_template('submit_project.html')

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
    cursor.execute('''
        INSERT INTO projects (title, description, project_type, location, budget_min, budget_max, timeline, status, original_file_path, ai_processed_text, created_at, homeowner_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active', %s, %s, NOW(), %s)
    ''', (title, description, project_type, location, budget_min, budget_max, timeline, original_file_path, ai_results.get('transcribed_text'), user['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Project submitted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/project/<int:project_id>')
def view_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch project with homeowner information
    cursor.execute('''
        SELECT p.*, u.first_name as homeowner_first_name, u.last_name as homeowner_last_name, u.location as homeowner_location
        FROM projects p 
        JOIN users u ON p.homeowner_id = u.id 
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
    
    audio_url = None
    if project['original_file_path']:
        if s3_client:
            # Determine the correct bucket based on the file path
            if project['original_file_path'].startswith('projects/audios/'):
                # This is an S3 key for audio files uploaded to homepro0723 bucket
                bucket_name = 'homepro0723'
            else:
                # Use the default configured bucket for other files
                bucket_name = app.config.get('AWS_S3_BUCKET', 'homepro-uploads')
            
            # For S3 stored files
            audio_url = s3_client.generate_presigned_url('get_object',
                Params={'Bucket': bucket_name, 'Key': project['original_file_path']},
                ExpiresIn=3600)
        else:
            # For locally stored files, generate URL using our uploaded_file route
            # Extract filename from the stored path
            import os
            filename = os.path.basename(project['original_file_path'])
            audio_url = url_for('uploaded_file', filename=filename)
    
    bids = []
    show_bids = 'user' in session
    if show_bids:
        # Fetch bids with contractor information
        cursor.execute('''
            SELECT b.*, u.first_name as contractor_first_name, u.last_name as contractor_last_name, u.location as contractor_location
            FROM bids b 
            JOIN users u ON b.contractor_id = u.id 
            WHERE b.project_id = %s 
            ORDER BY b.amount ASC
        ''', (project_id,))
        bids_raw = cursor.fetchall()
        
        # Create nested structure for contractor data to match template expectations
        for bid in bids_raw:
            bid['contractor'] = {
                'id': bid['contractor_id'],
                'first_name': bid['contractor_first_name'],
                'last_name': bid['contractor_last_name'],
                'location': bid['contractor_location']
            }
            bids.append(bid)
    
    cursor.close()
    conn.close()
    
    return render_template('project_detail.html', project=project, bids=bids, show_bids=show_bids, audio_url=audio_url)

@app.route('/submit_bid/<int:project_id>', methods=['POST'])
@login_required
def submit_bid(project_id):
    user = session['user']
    if user['role'] != 'contractor':
        flash('Only contractors can submit bids')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        abort(404)
    
    cursor.execute('SELECT * FROM bids WHERE project_id = %s AND contractor_id = %s', (project_id, user['id']))
    existing_bid = cursor.fetchone()
    if existing_bid:
        flash('You have already submitted a bid for this project')
        return redirect(url_for('view_project', project_id=project_id))
    
    amount = float(request.form['amount'])
    timeline = request.form['timeline']
    description = request.form['description']
    
    cursor.execute('''
        INSERT INTO bids (amount, timeline, description, status, created_at, project_id, contractor_id)
        VALUES (%s, %s, %s, 'Submitted', NOW(), %s, %s)
    ''', (amount, timeline, description, project_id, user['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Bid submitted successfully!')
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/accept_bid/<int:bid_id>', methods=['POST'])
@login_required
def accept_bid(bid_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bids WHERE id = %s', (bid_id,))
    bid = cursor.fetchone()
    if not bid:
        abort(404)
    cursor.execute('SELECT * FROM projects WHERE id = %s', (bid['project_id'],))
    project = cursor.fetchone()
    
    if project['homeowner_id'] != user['id']:
        return jsonify({'success': False, 'message': 'You can only accept bids for your own projects'}), 403
    
    if project['status'] != 'Active':
        return jsonify({'success': False, 'message': 'This project is no longer active'}), 400
    
    cursor.execute("UPDATE bids SET status = 'Accepted' WHERE id = %s", (bid_id,))
    cursor.execute("UPDATE bids SET status = 'Rejected' WHERE project_id = %s AND id != %s AND status = 'Submitted'", (project['id'], bid_id))
    conn.commit()
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
    cursor.execute('SELECT * FROM bids WHERE id = %s', (bid_id,))
    bid = cursor.fetchone()
    if not bid:
        abort(404)
    cursor.execute('SELECT * FROM projects WHERE id = %s', (bid['project_id'],))
    project = cursor.fetchone()
    
    if project['homeowner_id'] != user['id']:
        return jsonify({'success': False, 'message': 'You can only reject bids for your own projects'}), 403
    
    cursor.execute("UPDATE bids SET status = 'Rejected' WHERE id = %s", (bid_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Bid rejected successfully'})

@app.route('/complete_project/<int:project_id>', methods=['POST'])
@login_required
def complete_project(project_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        abort(404)
    cursor.execute("SELECT * FROM bids WHERE project_id = %s AND status = 'Accepted'", (project_id,))
    accepted_bid = cursor.fetchone()
    
    can_complete = (user['id'] == project['homeowner_id']) or (accepted_bid and user['id'] == accepted_bid['contractor_id'])
    if not can_complete:
        return jsonify({'success': False, 'message': 'You do not have permission to complete this project'}), 403
    
    if not accepted_bid:
        return jsonify({'success': False, 'message': 'Project must have an accepted bid before it can be completed'}), 400
    
    cursor.execute("UPDATE projects SET status = 'Completed' WHERE id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project marked as completed successfully!'})

@app.route('/close_project/<int:project_id>', methods=['POST'])
@login_required
def close_project(project_id):
    user = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cursor.fetchone()
    if not project:
        abort(404)
    
    if project['homeowner_id'] != user['id']:
        flash('You can only close your own projects')
        return redirect(url_for('dashboard'))
    
    cursor.execute("UPDATE projects SET status = 'Closed' WHERE id = %s", (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Project closed successfully!')
    return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files from the uploads directory"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)

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
    
    # Tables should be created in RDS separately
    # create_demo_users()  # If needed, adapt and run separately
    app.run(host='0.0.0.0', port=8000, debug=True)