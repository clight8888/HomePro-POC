#!/usr/bin/env python3
"""
Project Completion Routes
Handles project completion checklist and final project completion
"""

from flask import request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime
import json

# login_required and get_db_connection will be passed as parameters from app.py

def register_completion_routes(app, get_db_connection, login_required):
    """Register all completion-related routes"""
    
    @app.route('/project/<int:project_id>/completion')
    @login_required
    def project_completion_checklist(project_id):
        """Display project completion checklist"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.title, p.description, p.homeowner_id,
                       CASE WHEN p.homeowner_id = ? THEN 'homeowner'
                            WHEN EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted') THEN 'contractor'
                            ELSE NULL END as user_role
                FROM projects p
                WHERE p.id = ?
            """, (session['user']['id'], session['user']['id'], project_id))
            
            project = cursor.fetchone()
            if not project or not project[4]:  # user_role is None
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            
            # Get completion checklist items
            cursor.execute("""
                SELECT cc.id, cc.checklist_item, cc.description, cc.is_required, cc.is_completed,
                       cc.created_at, cc.completed_at, cc.verification_notes, cc.completed_by,
                       u.first_name, u.last_name, u.role
                FROM completion_checklist cc
                LEFT JOIN users u ON cc.completed_by = u.id
                WHERE cc.project_id = ?
                ORDER BY cc.is_required DESC, cc.created_at ASC
            """, (project_id,))
            
            checklist_items = cursor.fetchall()
            
            conn.close()
            
            return render_template('project_completion.html', 
                                 project=project,
                                 checklist_items=checklist_items,
                                 user_role=project[4])
            
        except Exception as e:
            flash(f'Error loading completion checklist: {str(e)}', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
    
    @app.route('/api/completion/<int:project_id>/add-item', methods=['POST'])
    @login_required
    def add_completion_item(project_id):
        """Add a new completion checklist item"""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get('checklist_item'):
                return jsonify({'error': 'Checklist item is required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id FROM projects p
                WHERE p.id = ? AND (
                    p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (project_id, session['user']['id'], session['user']['id']))
            
            project = cursor.fetchone()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            # Insert checklist item
            cursor.execute("""
                INSERT INTO completion_checklist (
                    project_id, checklist_item, description, is_required, 
                    is_completed, created_by, created_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (
                project_id,
                data['checklist_item'],
                data.get('description', ''),
                1 if data.get('is_required') else 0,
                session['user']['id'],
                datetime.now().isoformat()
            ))
            
            item_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'item_id': item_id,
                'message': 'Checklist item added successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/completion/<int:item_id>/toggle', methods=['POST'])
    @login_required
    def toggle_completion_item(item_id):
        """Toggle completion status of a checklist item"""
        try:
            data = request.get_json()
            is_completed = data.get('is_completed', False)
            verification_notes = data.get('verification_notes', '')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this item
            cursor.execute("""
                SELECT cc.project_id, cc.is_completed FROM completion_checklist cc
                JOIN projects p ON cc.project_id = p.id
                WHERE cc.id = ? AND (
                    p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (item_id, session['user']['id'], session['user']['id']))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Access denied'}), 403
            
            project_id = result[0]
            
            # Update completion status
            if is_completed:
                cursor.execute("""
                    UPDATE completion_checklist 
                    SET is_completed = 1, completed_at = ?, completed_by = ?, verification_notes = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), session['user']['id'], verification_notes, item_id))
            else:
                cursor.execute("""
                    UPDATE completion_checklist 
                    SET is_completed = 0, completed_at = NULL, completed_by = NULL, verification_notes = NULL
                    WHERE id = ?
                """, (item_id,))
            
            # Check if all required items are completed
            cursor.execute("""
                SELECT COUNT(*) as total_required,
                       SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_required
                FROM completion_checklist
                WHERE project_id = ? AND is_required = 1
            """, (project_id,))
            
            counts = cursor.fetchone()
            all_required_completed = False
            
            if counts and counts[0] > 0 and counts[0] == counts[1]:
                all_required_completed = True
                # Mark project as completed if all required items are done
                cursor.execute("""
                    UPDATE projects 
                    SET status = 'Completed', completion_date = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), project_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'all_required_completed': all_required_completed,
                'message': 'Item updated successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/completion/<int:item_id>/delete', methods=['DELETE'])
    @login_required
    def delete_completion_item(item_id):
        """Delete a completion checklist item"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this item and it's not completed
            cursor.execute("""
                SELECT cc.project_id, cc.is_completed FROM completion_checklist cc
                JOIN projects p ON cc.project_id = p.id
                WHERE cc.id = ? AND (
                    p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (item_id, session['user']['id'], session['user']['id']))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Access denied'}), 403
            
            if result[1]:  # is_completed
                return jsonify({'error': 'Cannot delete completed items'}), 400
            
            # Delete the item
            cursor.execute('DELETE FROM completion_checklist WHERE id = ?', (item_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Item deleted successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/project/<int:project_id>/complete', methods=['POST'])
    @login_required
    def complete_project_final(project_id):
        """Mark project as finally completed (admin override or when all requirements met)"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verify user has access to this project
            cursor.execute("""
                SELECT p.id, p.status FROM projects p
                WHERE p.id = ? AND (
                    p.homeowner_id = ? OR
                    EXISTS (SELECT 1 FROM bids b WHERE b.project_id = p.id AND b.contractor_id = ? AND b.status = 'Accepted')
                )
            """, (project_id, session['user']['id'], session['user']['id']))
            
            project = cursor.fetchone()
            if not project:
                return jsonify({'error': 'Access denied'}), 403
            
            if project[1] == 'Completed':
                return jsonify({'error': 'Project is already completed'}), 400
            
            # Mark project as completed
            cursor.execute("""
                UPDATE projects 
                SET status = 'Completed', completion_date = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), project_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Project marked as completed successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500