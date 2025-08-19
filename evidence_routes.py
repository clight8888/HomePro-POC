from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort, send_file
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import io

# Allowed file extensions for evidence uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_evidence_routes(app, get_db_connection, login_required):
    """Register all evidence-related routes with the Flask app"""
    
    @app.route('/api/milestone/<int:milestone_id>/evidence', methods=['POST'])
    @login_required
    def submit_milestone_evidence(milestone_id):
        """Submit evidence for milestone completion (contractor only)"""
        if session['user']['role'] != 'contractor':
            return jsonify({'error': 'Only contractors can submit evidence'}), 403
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify contractor owns this milestone
            cursor.execute("""
                SELECT pm.id, pm.title, pm.status, p.id as project_id
                FROM project_milestones pm
                JOIN projects p ON pm.project_id = p.id
                JOIN bids b ON p.id = b.project_id
                WHERE pm.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
            """, (milestone_id, session['user']['id']))
            
            milestone = cursor.fetchone()
            if not milestone:
                return jsonify({'error': 'Access denied'}), 403
            
            if milestone[2] == 'completed':
                return jsonify({'error': 'Cannot submit evidence for completed milestones'}), 400
            
            # Get form data
            description = request.form.get('description', '')
            evidence_type = request.form.get('evidence_type', 'photo')
            
            if not description:
                return jsonify({'error': 'Description is required'}), 400
            
            # Handle file uploads
            uploaded_files = []
            if 'files' in request.files:
                files = request.files.getlist('files')
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        # Check file size
                        file.seek(0, os.SEEK_END)
                        file_size = file.tell()
                        file.seek(0)
                        
                        if file_size > MAX_FILE_SIZE:
                            return jsonify({'error': f'File {file.filename} is too large. Maximum size is 10MB.'}), 400
                        
                        # Generate unique filename
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        
                        # Create evidence directory if it doesn't exist
                        evidence_dir = os.path.join('static', 'uploads', 'evidence')
                        os.makedirs(evidence_dir, exist_ok=True)
                        
                        # Save file
                        file_path = os.path.join(evidence_dir, unique_filename)
                        file.save(file_path)
                        
                        # If it's an image, create a thumbnail
                        thumbnail_path = None
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            try:
                                with Image.open(file_path) as img:
                                    img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                                    thumbnail_filename = f"thumb_{unique_filename}"
                                    thumbnail_path = os.path.join(evidence_dir, thumbnail_filename)
                                    img.save(thumbnail_path)
                            except Exception as e:
                                print(f"Error creating thumbnail: {e}")
                        
                        uploaded_files.append({
                            'filename': filename,
                            'unique_filename': unique_filename,
                            'file_path': file_path,
                            'thumbnail_path': thumbnail_path,
                            'file_size': file_size
                        })
            
            # Insert evidence record
            cursor.execute("""
                INSERT INTO milestone_evidence 
                (milestone_id, evidence_type, description, submitted_at)
                VALUES (?, ?, ?, ?)
            """, (
                milestone_id,
                evidence_type,
                description,
                datetime.now().isoformat()
            ))
            
            evidence_id = cursor.lastrowid
            
            # Insert file records
            for file_info in uploaded_files:
                cursor.execute("""
                    INSERT INTO evidence_files 
                    (evidence_id, original_filename, stored_filename, file_path, 
                     thumbnail_path, file_size, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    evidence_id,
                    file_info['filename'],
                    file_info['unique_filename'],
                    file_info['file_path'],
                    file_info['thumbnail_path'],
                    file_info['file_size'],
                    datetime.now().isoformat()
                ))
            
            # Update milestone status to 'submitted' if not already
            if milestone[2] == 'pending':
                cursor.execute("""
                    UPDATE project_milestones 
                    SET status = 'submitted', updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), milestone_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'evidence_id': evidence_id,
                'files_uploaded': len(uploaded_files),
                'message': 'Evidence submitted successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/milestone/<int:milestone_id>/evidence')
    @login_required
    def get_milestone_evidence(milestone_id):
        """Get all evidence for a specific milestone"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this milestone
            if session['user']['role'] == 'contractor':
                cursor.execute("""
                    SELECT pm.id FROM project_milestones pm
                    JOIN projects p ON pm.project_id = p.id
                    JOIN bids b ON p.id = b.project_id
                    WHERE pm.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
                """, (milestone_id, session['user']['id']))
            else:  # homeowner
                cursor.execute("""
                    SELECT pm.id FROM project_milestones pm
                    JOIN projects p ON pm.project_id = p.id
                    WHERE pm.id = ? AND p.homeowner_id = ?
                """, (milestone_id, session['user']['id']))
            
            if not cursor.fetchone():
                return jsonify({'error': 'Access denied'}), 403
            
            # Get evidence records
            cursor.execute("""
                SELECT id, evidence_type, description, status, submitted_at, 
                       reviewed_at, reviewer_notes
                FROM milestone_evidence 
                WHERE milestone_id = ? 
                ORDER BY submitted_at DESC
            """, (milestone_id,))
            
            evidence_list = []
            for row in cursor.fetchall():
                evidence_id = row[0]
                
                # Get files for this evidence
                cursor.execute("""
                    SELECT original_filename, stored_filename, file_path, 
                           thumbnail_path, file_size
                    FROM evidence_files 
                    WHERE evidence_id = ?
                """, (evidence_id,))
                
                files = []
                for file_row in cursor.fetchall():
                    files.append({
                        'original_filename': file_row[0],
                        'stored_filename': file_row[1],
                        'file_path': file_row[2],
                        'thumbnail_path': file_row[3],
                        'file_size': file_row[4]
                    })
                
                evidence = {
                    'id': evidence_id,
                    'evidence_type': row[1],
                    'description': row[2],
                    'status': row[3],
                    'submitted_at': row[4],
                    'reviewed_at': row[5],
                    'reviewer_notes': row[6],
                    'files': files
                }
                evidence_list.append(evidence)
            
            conn.close()
            return jsonify({'evidence': evidence_list})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/evidence/<int:evidence_id>/review', methods=['POST'])
    @login_required
    def review_evidence(evidence_id):
        """Review submitted evidence (homeowner only)"""
        if session['user']['role'] != 'homeowner':
            return jsonify({'error': 'Only homeowners can review evidence'}), 403
        
        try:
            data = request.get_json()
            action = data.get('action')  # 'approve' or 'reject'
            notes = data.get('notes', '')
            
            if action not in ['approve', 'reject']:
                return jsonify({'error': 'Invalid action. Must be approve or reject'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify homeowner owns this evidence's project
            cursor.execute("""
                SELECT me.id, pm.id as milestone_id, pm.title
                FROM milestone_evidence me
                JOIN project_milestones pm ON me.milestone_id = pm.id
                JOIN projects p ON pm.project_id = p.id
                WHERE me.id = ? AND p.homeowner_id = ?
            """, (evidence_id, session['user']['id']))
            
            evidence = cursor.fetchone()
            if not evidence:
                return jsonify({'error': 'Access denied'}), 403
            
            # Update evidence status
            new_status = 'approved' if action == 'approve' else 'rejected'
            cursor.execute("""
                UPDATE milestone_evidence 
                SET status = ?, reviewed_at = ?, reviewer_notes = ?
                WHERE id = ?
            """, (
                new_status,
                datetime.now().isoformat(),
                notes,
                evidence_id
            ))
            
            # If approved, check if all evidence for milestone is approved
            if action == 'approve':
                milestone_id = evidence[1]
                
                # Check if all evidence for this milestone is approved
                cursor.execute("""
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved
                    FROM milestone_evidence 
                    WHERE milestone_id = ?
                """, (milestone_id,))
                
                counts = cursor.fetchone()
                if counts and counts[0] > 0 and counts[0] == counts[1]:
                    # All evidence approved, mark milestone as completed
                    cursor.execute("""
                        UPDATE project_milestones 
                        SET status = 'completed', completion_date = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        milestone_id
                    ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Evidence {action}d successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/evidence/file/<filename>')
    @login_required
    def serve_evidence_file(filename):
        """Serve evidence files with access control"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get file info and verify access
            cursor.execute("""
                SELECT ef.file_path, pm.project_id
                FROM evidence_files ef
                JOIN milestone_evidence me ON ef.evidence_id = me.id
                JOIN project_milestones pm ON me.milestone_id = pm.id
                WHERE ef.stored_filename = ?
            """, (filename,))
            
            file_info = cursor.fetchone()
            if not file_info:
                abort(404)
            
            file_path, project_id = file_info
            
            # Verify user has access to this project
            has_access = False
            if session['user']['role'] == 'homeowner':
                cursor.execute('SELECT id FROM projects WHERE id = ? AND homeowner_id = ?', 
                             (project_id, session['user']['id']))
                has_access = cursor.fetchone() is not None
            elif session['user']['role'] == 'contractor':
                cursor.execute("""
                    SELECT id FROM bids 
                    WHERE project_id = ? AND contractor_id = ? AND status = 'Accepted'
                """, (project_id, session['user']['id']))
                has_access = cursor.fetchone() is not None
            
            conn.close()
            
            if not has_access:
                abort(403)
            
            # Serve the file
            if os.path.exists(file_path):
                return send_file(file_path)
            else:
                abort(404)
                
        except Exception as e:
            abort(500)
    
    @app.route('/milestone/<int:milestone_id>/evidence')
    @login_required
    def milestone_evidence_page(milestone_id):
        """Display evidence page for a milestone"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get milestone details
            cursor.execute("""
                SELECT pm.title, pm.description, pm.due_date, pm.status,
                       p.id as project_id, p.title as project_title,
                       p.homeowner_id
                FROM project_milestones pm
                JOIN projects p ON pm.project_id = p.id
                WHERE pm.id = ?
            """, (milestone_id,))
            
            milestone = cursor.fetchone()
            if not milestone:
                abort(404)
            
            # Verify user has access
            has_access = False
            user_role = session['user']['role']
            
            if user_role == 'homeowner' and milestone[6] == session['user']['id']:
                has_access = True
            elif user_role == 'contractor':
                cursor.execute("""
                    SELECT id FROM bids 
                    WHERE project_id = ? AND contractor_id = ? AND status = 'Accepted'
                """, (milestone[4], session['user']['id']))
                if cursor.fetchone():
                    has_access = True
            
            if not has_access:
                abort(403)
            
            conn.close()
            
            return render_template('milestone_evidence.html',
                                 milestone_id=milestone_id,
                                 milestone_title=milestone[0],
                                 milestone_description=milestone[1],
                                 milestone_due_date=milestone[2],
                                 milestone_status=milestone[3],
                                 project_id=milestone[4],
                                 project_title=milestone[5],
                                 user_role=user_role)
            
        except Exception as e:
            flash(f'Error loading evidence page: {str(e)}', 'error')
            return redirect(url_for('homeowner_dashboard' if session['user']['role'] == 'homeowner' else 'contractor_dashboard'))

    # Initialize evidence_files table if it doesn't exist
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Detect database type for proper SQL syntax
        is_sqlite = hasattr(conn, 'row_factory')
        
        if is_sqlite:
            # SQLite version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id INTEGER NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    file_size INTEGER NOT NULL,
                    uploaded_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (evidence_id) REFERENCES milestone_evidence (id) ON DELETE CASCADE
                )
            """)
        else:
            # MySQL version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_files (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    evidence_id INTEGER NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    stored_filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    thumbnail_path VARCHAR(500),
                    file_size INTEGER NOT NULL,
                    uploaded_at DATETIME NOT NULL,
                    FOREIGN KEY (evidence_id) REFERENCES milestone_evidence (id) ON DELETE CASCADE
                )
            """)
        
        conn.commit()
        conn.close()
        print("Evidence files table initialized successfully")
    except Exception as e:
        print(f"Error creating evidence_files table: {e}")