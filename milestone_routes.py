from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from functools import wraps
from datetime import datetime, timedelta
import json

def register_milestone_routes(app, get_db_connection, login_required):
    """Register all milestone-related routes with the Flask app"""
    
    @app.route('/api/project/<int:project_id>/milestones')
    @login_required
    def get_project_milestones(project_id):
        """Get all milestones for a specific project"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            if session['user']['role'] == 'contractor':
                cursor.execute("""
                    SELECT p.id FROM projects p 
                    JOIN bids b ON p.id = b.project_id 
                    WHERE p.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
                """, (project_id, session['user']['id']))
            else:  # homeowner
                cursor.execute("""
                    SELECT id FROM projects WHERE id = ? AND homeowner_id = ?
                """, (project_id, session['user']['id']))
            
            if not cursor.fetchone():
                return jsonify({'error': 'Access denied'}), 403
            
            # Get milestones
            cursor.execute("""
                SELECT id, title, description, due_date, status, payment_amount, 
                       created_at, updated_at, completion_date
                FROM project_milestones 
                WHERE project_id = ? 
                ORDER BY due_date ASC
            """, (project_id,))
            
            milestones = []
            for row in cursor.fetchall():
                milestone = {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'due_date': row[3],
                    'status': row[4],
                    'payment_amount': float(row[5]) if row[5] else 0,
                    'created_at': row[6],
                    'updated_at': row[7],
                    'completion_date': row[8]
                }
                milestones.append(milestone)
            
            conn.close()
            return jsonify({'milestones': milestones})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/project/<int:project_id>/milestones', methods=['POST'])
    @login_required
    def create_milestone(project_id):
        """Create a new milestone for a project (contractor only)"""
        if session['user']['role'] != 'contractor':
            return jsonify({'error': 'Only contractors can create milestones'}), 403
        
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['title', 'description', 'due_date']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify contractor has access to this project
            cursor.execute("""
                SELECT p.id FROM projects p 
                JOIN bids b ON p.id = b.project_id 
                WHERE p.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
            """, (project_id, session['user']['id']))
            
            if not cursor.fetchone():
                return jsonify({'error': 'Access denied'}), 403
            
            # Create milestone
            cursor.execute("""
                INSERT INTO project_milestones 
                (project_id, title, description, due_date, status, payment_amount, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (
                project_id,
                data['title'],
                data['description'],
                data['due_date'],
                data.get('payment_amount', 0),
                datetime.now().isoformat()
            ))
            
            milestone_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'milestone_id': milestone_id,
                'message': 'Milestone created successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/milestone/<int:milestone_id>', methods=['PUT'])
    @login_required
    def update_milestone(milestone_id):
        """Update a milestone (contractor only)"""
        if session['user']['role'] != 'contractor':
            return jsonify({'error': 'Only contractors can update milestones'}), 403
        
        try:
            data = request.get_json()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify contractor owns this milestone
            cursor.execute("""
                SELECT pm.id FROM project_milestones pm
                JOIN projects p ON pm.project_id = p.id
                JOIN bids b ON p.id = b.project_id
                WHERE pm.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
            """, (milestone_id, session['user']['id']))
            
            if not cursor.fetchone():
                return jsonify({'error': 'Access denied'}), 403
            
            # Update milestone
            update_fields = []
            params = []
            
            if 'title' in data:
                update_fields.append('title = ?')
                params.append(data['title'])
            
            if 'description' in data:
                update_fields.append('description = ?')
                params.append(data['description'])
            
            if 'due_date' in data:
                update_fields.append('due_date = ?')
                params.append(data['due_date'])
            
            if 'payment_amount' in data:
                update_fields.append('payment_amount = ?')
                params.append(data['payment_amount'])
            
            if update_fields:
                update_fields.append('updated_at = ?')
                params.append(datetime.now().isoformat())
                params.append(milestone_id)
                
                cursor.execute(f"""
                    UPDATE project_milestones 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, params)
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Milestone updated successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/milestone/<int:milestone_id>', methods=['DELETE'])
    @login_required
    def delete_milestone(milestone_id):
        """Delete a milestone (contractor only)"""
        if session['user']['role'] != 'contractor':
            return jsonify({'error': 'Only contractors can delete milestones'}), 403
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify contractor owns this milestone and it's not completed
            cursor.execute("""
                SELECT pm.status FROM project_milestones pm
                JOIN projects p ON pm.project_id = p.id
                JOIN bids b ON p.id = b.project_id
                WHERE pm.id = ? AND b.contractor_id = ? AND b.status = 'Accepted'
            """, (milestone_id, session['user']['id']))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Access denied'}), 403
            
            if result[0] == 'completed':
                return jsonify({'error': 'Cannot delete completed milestones'}), 400
            
            # Delete milestone
            cursor.execute('DELETE FROM project_milestones WHERE id = ?', (milestone_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Milestone deleted successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/project/<int:project_id>/milestones')
    @login_required
    def project_milestones_page(project_id):
        """Display milestones page for a project"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get project details
            cursor.execute("""
                SELECT p.title, p.description, p.homeowner_id,
                       u.first_name as homeowner_first, u.last_name as homeowner_last
                FROM projects p
                JOIN users u ON p.homeowner_id = u.id
                WHERE p.id = ?
            """, (project_id,))
            
            project = cursor.fetchone()
            if not project:
                abort(404)
            
            # Verify user has access
            has_access = False
            user_role = session['user']['role']
            
            if user_role == 'homeowner' and project[2] == session['user']['id']:
                has_access = True
            elif user_role == 'contractor':
                cursor.execute("""
                    SELECT id FROM bids 
                    WHERE project_id = ? AND contractor_id = ? AND status = 'Accepted'
                """, (project_id, session['user']['id']))
                if cursor.fetchone():
                    has_access = True
            
            if not has_access:
                abort(403)
            
            # Get contractor info if user is homeowner
            contractor_info = None
            if user_role == 'homeowner':
                cursor.execute("""
                    SELECT u.first_name, u.last_name, u.email
                    FROM users u
                    JOIN bids b ON u.id = b.contractor_id
                    WHERE b.project_id = ? AND b.status = 'Accepted'
                """, (project_id,))
                contractor_row = cursor.fetchone()
                if contractor_row:
                    contractor_info = {
                        'name': f"{contractor_row[0]} {contractor_row[1]}",
                        'email': contractor_row[2]
                    }
            
            conn.close()
            
            return render_template('project_milestones.html', 
                                 project_id=project_id,
                                 project_title=project[0],
                                 project_description=project[1],
                                 homeowner_name=f"{project[3]} {project[4]}",
                                 contractor_info=contractor_info,
                                 user_role=user_role)
            
        except Exception as e:
            flash(f'Error loading milestones: {str(e)}', 'error')
            return redirect(url_for('homeowner_dashboard' if session['user']['role'] == 'homeowner' else 'contractor_dashboard'))