#!/usr/bin/env python3
"""
Agreement Management Routes
Handles project agreement creation, review, and management
"""

from flask import request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime
import json

# login_required and get_db_connection will be passed as parameters from app.py

def register_agreement_routes(app, get_db_connection, login_required):
    """Register all agreement-related routes"""
    
    @app.route('/project/<int:project_id>/agreement/create')
    @login_required
    def create_agreement_form(project_id):
        """Display agreement creation form"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.title, p.homeowner_id,
                       CASE WHEN p.homeowner_id = %s THEN 'homeowner'
                            WHEN EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = %s AND b.status = 'Accepted') THEN 'contractor'
                            ELSE NULL END as user_role
                FROM projects p
                WHERE p.id = %s
            """, (session['user']['id'], session['user']['id'], project_id))
            
            project = cursor.fetchone()
            if not project or not project['user_role']:  # user_role is None
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            # Get project milestones for agreement context
            cursor.execute("""
                SELECT id, title, description, due_date, payment_amount
                FROM project_milestones
                WHERE project_id = %s
                ORDER BY due_date
            """, (project_id,))
            
            milestones = cursor.fetchall()
            
            conn.close()
            
            return render_template('create_agreement.html', 
                                 project=project,
                                 milestones=milestones,
                                 user_role=project['user_role'])
            
        except Exception as e:
            flash(f'Error loading agreement form: {str(e)}', 'error')
            return redirect(url_for('view_project', project_id=project_id))
    
    @app.route('/api/agreement/create', methods=['POST'])
    @login_required
    def submit_agreement():
        """Submit a new agreement"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['project_id', 'title', 'terms']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            project_id = data['project_id']
            title = data['title']
            terms = data['terms']
            payment_schedule = data.get('payment_schedule', '')
            total_amount = data.get('total_amount', 0)
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.homeowner_id
                FROM projects p
                WHERE p.id = %s AND (
                    p.homeowner_id = %s OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = %s AND b.status = 'Accepted')
                )
            """, (project_id, session['user']['id'], session['user']['id']))
            
            project = cursor.fetchone()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            # Insert agreement record
            cursor.execute("""
                INSERT INTO project_agreements (
                    project_id, title, terms, payment_schedule, total_amount,
                    start_date, end_date, status, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft', %s, %s, %s)
            """, (
                project_id, title, terms, payment_schedule, total_amount,
                start_date, end_date, session['user']['id'],
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            agreement_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'agreement_id': agreement_id,
                'message': 'Agreement created successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/project/<int:project_id>/agreements')
    @login_required
    def view_project_agreements(project_id):
        """View all agreements for a project"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.title, p.homeowner_id,
                       CASE WHEN p.homeowner_id = %s THEN 'homeowner'
                            WHEN EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = %s AND b.status = 'Accepted') THEN 'contractor'
                            ELSE NULL END as user_role
                FROM projects p
                WHERE p.id = %s
            """, (session['user']['id'], session['user']['id'], project_id))
            
            project = cursor.fetchone()
            if not project or not project['user_role']:  # user_role is None
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            # Get all agreements for this project
            cursor.execute("""
                SELECT a.id, a.title, a.terms, a.payment_schedule, a.total_amount,
                       a.start_date, a.end_date, a.status, a.created_at, a.updated_at,
                       a.signed_date, a.homeowner_signature, a.contractor_signature,
                       u.first_name, u.last_name
                FROM project_agreements a
                JOIN users u ON a.created_by = u.id
                WHERE a.project_id = %s
                ORDER BY a.created_at DESC
            """, (project_id,))
            
            agreements = cursor.fetchall()
            
            conn.close()
            
            return render_template('project_agreements.html',
                                 project=project,
                                 agreements=agreements,
                                 user_role=project['user_role'])
            
        except Exception as e:
            flash(f'Error loading agreements: {str(e)}', 'error')
            return redirect(url_for('view_project', project_id=project_id))
    
    @app.route('/api/agreement/<int:agreement_id>/sign', methods=['POST'])
    @login_required
    def sign_agreement(agreement_id):
        """Sign an agreement"""
        try:
            data = request.get_json()
            signature = data.get('signature')
            
            if not signature:
                return jsonify({'error': 'Signature is required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get agreement details
            cursor.execute("""
                SELECT a.id, a.project_id, p.homeowner_id
                FROM project_agreements a
                JOIN projects p ON a.project_id = p.id
                WHERE a.id = %s
            """, (agreement_id,))
            
            agreement = cursor.fetchone()
            if not agreement:
                return jsonify({'error': 'Agreement not found'}), 404
            
            # Determine user role and update appropriate signature field
            if session['user']['id'] == agreement['homeowner_id']:  # homeowner
                cursor.execute("""
                    UPDATE project_agreements 
                    SET homeowner_signature = %s, updated_at = %s
                    WHERE id = %s
                """, (signature, datetime.now().isoformat(), agreement_id))
                role = 'homeowner'
            else:
                # Check if user is the contractor
                cursor.execute("""
                    SELECT 1 FROM bids b 
                    WHERE b.project_id = %s AND b.contractor_id = %s AND b.status = 'Accepted'
                """, (agreement['project_id'], session['user']['id']))
                
                if not cursor.fetchone():
                    return jsonify({'error': 'Access denied'}), 403
                
                cursor.execute("""
                    UPDATE project_agreements 
                    SET contractor_signature = %s, updated_at = %s
                    WHERE id = %s
                """, (signature, datetime.now().isoformat(), agreement_id))
                role = 'contractor'
            
            # Check if both parties have signed
            cursor.execute("""
                SELECT homeowner_signature, contractor_signature
                FROM project_agreements
                WHERE id = %s
            """, (agreement_id,))
            
            signatures = cursor.fetchone()
            if signatures[0] and signatures[1]:  # Both signatures present
                cursor.execute("""
                    UPDATE project_agreements 
                    SET status = 'signed', signed_date = %s, updated_at = %s
                    WHERE id = %s
                """, (datetime.now().isoformat(), datetime.now().isoformat(), agreement_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Agreement signed successfully as {role}'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/agreement/<int:agreement_id>')
    @login_required
    def get_agreement(agreement_id):
        """Get agreement details"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get agreement with project info
            cursor.execute("""
                SELECT a.*, p.title as project_title, p.homeowner_id
                FROM project_agreements a
                JOIN projects p ON a.project_id = p.id
                WHERE a.id = %s
            """, (agreement_id,))
            
            agreement = cursor.fetchone()
            if not agreement:
                return jsonify({'error': 'Agreement not found'}), 404
            
            # Verify user has access
            has_access = False
            if session['user']['id'] == agreement['homeowner_id']:  # homeowner
                has_access = True
            else:
                # Check if user is the contractor
                cursor.execute("""
                    SELECT 1 FROM bids b 
                    WHERE b.project_id = %s AND b.contractor_id = %s AND b.status = 'Accepted'
                """, (agreement['project_id'], session['user']['id']))
                
                if cursor.fetchone():
                    has_access = True
            
            if not has_access:
                return jsonify({'error': 'Access denied'}), 403
            
            conn.close()
            
            # Convert to dict for JSON response
            agreement_dict = dict(agreement)
            
            return jsonify({'agreement': agreement_dict})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500