#!/usr/bin/env python3
"""
Dispute Management Routes
Handles project dispute filing, tracking, and resolution
"""

from flask import request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime
import os
# login_required and get_db_connection will be passed as parameters from app.py

def register_dispute_routes(app, get_db_connection, login_required):
    """Register all dispute-related routes"""
    
    @app.route('/project/<int:project_id>/dispute/file')
    @login_required
    def file_dispute_form(project_id):
        """Display dispute filing form"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.title, p.homeowner_id,
                       CASE WHEN p.homeowner_id = ? THEN 'homeowner'
                            WHEN EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted') THEN 'contractor'
                            ELSE NULL END as user_role
                FROM projects p
                WHERE p.id = ?
            """, (session['user']['id'], session['user']['id'], project_id))
            
            project = cursor.fetchone()
            if not project or not project[3]:  # user_role is None
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            # Get project milestones for dispute context
            cursor.execute("""
                SELECT id, title, status, due_date
                FROM project_milestones
                WHERE project_id = ?
                ORDER BY due_date
            """, (project_id,))
            
            milestones = cursor.fetchall()
            
            # Get project agreements
            cursor.execute("""
                SELECT id, title, status
                FROM project_agreements
                WHERE project_id = ?
                ORDER BY created_at DESC
            """, (project_id,))
            
            agreements = cursor.fetchall()
            
            conn.close()
            
            return render_template('file_dispute.html', 
                                 project=project,
                                 milestones=milestones,
                                 agreements=agreements,
                                 user_role=project[3])
            
        except Exception as e:
            flash(f'Error loading dispute form: {str(e)}', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
    
    @app.route('/api/dispute/file', methods=['POST'])
    @login_required
    def submit_dispute():
        """Submit a new dispute"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['project_id', 'dispute_category', 'title', 'description']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            project_id = data['project_id']
            milestone_id = data.get('milestone_id')
            agreement_id = data.get('agreement_id')
            dispute_category = data['dispute_category']
            title = data['title']
            description = data['description']
            requested_resolution = data.get('requested_resolution', '')
            priority = data.get('priority', 'medium')
            
            # Validate category and priority
            valid_categories = ['quality', 'timeline', 'payment', 'scope', 'communication', 'other']
            valid_priorities = ['low', 'medium', 'high', 'urgent']
            
            if dispute_category not in valid_categories:
                return jsonify({'error': 'Invalid dispute category'}), 400
            
            if priority not in valid_priorities:
                return jsonify({'error': 'Invalid priority level'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.homeowner_id
                FROM projects p
                WHERE p.id = ? AND (
                    p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (project_id, session['user']['id'], session['user']['id']))
            
            project = cursor.fetchone()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            # Insert dispute record
            cursor.execute("""
                INSERT INTO project_disputes (
                    project_id, milestone_id, agreement_id, filed_by,
                    dispute_category, title, description, requested_resolution,
                    priority, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'filed', ?, ?)
            """, (
                project_id, milestone_id, agreement_id, session['user']['id'],
                dispute_category, title, description, requested_resolution,
                priority, datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            dispute_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'dispute_id': dispute_id,
                'message': 'Dispute filed successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/project/<int:project_id>/disputes')
    @login_required
    def view_project_disputes(project_id):
        """View all disputes for a project"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.title, p.homeowner_id,
                       CASE WHEN p.homeowner_id = ? THEN 'homeowner'
                            WHEN EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted') THEN 'contractor'
                            ELSE NULL END as user_role
                FROM projects p
                WHERE p.id = ?
            """, (session['user']['id'], session['user']['id'], project_id))
            
            project = cursor.fetchone()
            if not project or not project[3]:  # user_role is None
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            # Get all disputes for this project
            cursor.execute("""
                SELECT d.id, d.dispute_category, d.title, d.description,
                       d.requested_resolution, d.status, d.priority,
                       d.created_at, d.updated_at, d.resolution_date,
                       d.resolution_notes,
                       u.first_name, u.last_name,
                       pm.title as milestone_title,
                       pa.title as agreement_title
                FROM project_disputes d
                JOIN users u ON d.filed_by = u.id
                LEFT JOIN project_milestones pm ON d.milestone_id = pm.id
                LEFT JOIN project_agreements pa ON d.agreement_id = pa.id
                WHERE d.project_id = ?
                ORDER BY d.created_at DESC
            """, (project_id,))
            
            disputes = cursor.fetchall()
            conn.close()
            
            return render_template('project_disputes.html',
                                 project=project,
                                 disputes=disputes,
                                 user_role=project[3])
            
        except Exception as e:
            flash(f'Error loading disputes: {str(e)}', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
    
    @app.route('/api/disputes/<int:dispute_id>/evidence', methods=['POST'])
    @login_required
    def upload_dispute_evidence(dispute_id):
        """Upload evidence for a dispute"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this dispute
            cursor.execute("""
                SELECT d.id, d.project_id, d.filed_by, p.homeowner_id
                FROM project_disputes d
                JOIN projects p ON d.project_id = p.id
                WHERE d.id = ? AND (
                    d.filed_by = ? OR p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (dispute_id, session['user']['id'], session['user']['id'], session['user']['id']))
            
            dispute = cursor.fetchone()
            if not dispute:
                return jsonify({'error': 'Access denied'}), 403
            
            # Handle file uploads (similar to evidence_routes.py)
            if 'files' not in request.files:
                return jsonify({'error': 'No files provided'}), 400
            
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({'error': 'No files selected'}), 400
            
            evidence_type = request.form.get('evidence_type', 'document')
            title = request.form.get('title', '')
            description = request.form.get('description', '')
            
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('static', 'uploads', 'disputes')
            os.makedirs(upload_dir, exist_ok=True)
            
            uploaded_files = []
            
            for file in files:
                if file and file.filename:
                    # Generate unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"dispute_{dispute_id}_{timestamp}_{file.filename}"
                    file_path = os.path.join(upload_dir, filename)
                    
                    # Save file
                    file.save(file_path)
                    
                    # Insert evidence record
                    cursor.execute("""
                        INSERT INTO dispute_evidence (
                            dispute_id, evidence_type, file_path, original_filename,
                            file_size, title, description, uploaded_by, upload_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dispute_id, evidence_type, file_path, file.filename,
                        os.path.getsize(file_path), title, description,
                        session['user']['id'], datetime.now().isoformat()
                    ))
                    
                    uploaded_files.append({
                        'filename': file.filename,
                        'stored_filename': filename
                    })
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'{len(uploaded_files)} file(s) uploaded successfully',
                'files': uploaded_files
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500