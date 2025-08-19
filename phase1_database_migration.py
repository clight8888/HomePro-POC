#!/usr/bin/env python3
"""
Phase 1 Database Migration Script - SQLite Compatible
Adds tables for:
- Project Agreements
- Custom Milestones
- Milestone Evidence
- Dispute Management
- Completion Checklists
"""

import sqlite3
import os
from datetime import datetime

def create_phase1_tables():
    """Create new tables for Phase 1 features"""
    conn = sqlite3.connect('homepro.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        print("Creating Phase 1 database tables...")
        
        # 1. Project Agreements Table
        print("Creating project_agreements table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_agreements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                contractor_id INTEGER NOT NULL,
                homeowner_id INTEGER NOT NULL,
                agreement_type TEXT DEFAULT 'standard' CHECK (agreement_type IN ('standard', 'custom', 'template')),
                title TEXT NOT NULL,
                description TEXT,
                terms_and_conditions TEXT NOT NULL,
                total_amount REAL NOT NULL,
                payment_schedule TEXT,
                start_date TEXT,
                estimated_completion_date TEXT,
                status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'approved', 'signed', 'active', 'completed', 'terminated')),
                homeowner_signature_date TEXT,
                contractor_signature_date TEXT,
                digital_signature_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
                FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE
            )
        ''')
        
        # 2. Custom Milestones Table
        print("Creating project_milestones table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                agreement_id INTEGER,
                milestone_order INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                deliverables TEXT,
                estimated_completion_date TEXT,
                actual_completion_date TEXT,
                payment_percentage REAL DEFAULT 0.00,
                payment_amount REAL DEFAULT 0.00,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'submitted', 'approved', 'rejected', 'completed')),
                contractor_notes TEXT,
                homeowner_feedback TEXT,
                rejection_reason TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_at TEXT,
                reviewed_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (agreement_id) REFERENCES project_agreements(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 3. Milestone Evidence Table
        print("Creating milestone_evidence table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS milestone_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL CHECK (evidence_type IN ('photo', 'document', 'video', 'note')),
                file_path TEXT,
                original_filename TEXT,
                file_size INTEGER,
                mime_type TEXT,
                title TEXT,
                description TEXT,
                uploaded_by INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_before_photo INTEGER DEFAULT 0,
                is_after_photo INTEGER DEFAULT 0,
                FOREIGN KEY (milestone_id) REFERENCES project_milestones(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Dispute Management Table
        print("Creating project_disputes table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_disputes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                milestone_id INTEGER,
                agreement_id INTEGER,
                filed_by INTEGER NOT NULL,
                dispute_category TEXT NOT NULL CHECK (dispute_category IN ('quality', 'timeline', 'payment', 'scope', 'communication', 'other')),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requested_resolution TEXT,
                status TEXT DEFAULT 'filed' CHECK (status IN ('filed', 'under_review', 'investigating', 'mediation', 'resolved', 'closed')),
                priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                assigned_admin INTEGER,
                resolution_notes TEXT,
                resolution_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (milestone_id) REFERENCES project_milestones(id) ON DELETE SET NULL,
                FOREIGN KEY (agreement_id) REFERENCES project_agreements(id) ON DELETE SET NULL,
                FOREIGN KEY (filed_by) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 5. Dispute Evidence Table
        print("Creating dispute_evidence table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dispute_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispute_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL CHECK (evidence_type IN ('photo', 'document', 'screenshot', 'message', 'other')),
                file_path TEXT,
                original_filename TEXT,
                file_size INTEGER,
                title TEXT,
                description TEXT,
                uploaded_by INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dispute_id) REFERENCES project_disputes(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 6. Project Completion Checklist Table
        print("Creating project_completion_checklist table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_completion_checklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                agreement_id INTEGER,
                checklist_item TEXT NOT NULL,
                description TEXT,
                is_required INTEGER DEFAULT 1,
                is_completed INTEGER DEFAULT 0,
                completed_by INTEGER,
                completed_at TEXT,
                verification_notes TEXT,
                item_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (agreement_id) REFERENCES project_agreements(id) ON DELETE SET NULL,
                FOREIGN KEY (completed_by) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        
        # 7. Agreement Templates Table
        print("Creating agreement_templates table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agreement_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                project_type TEXT,
                template_content TEXT NOT NULL,
                default_terms TEXT,
                default_milestones TEXT,
                default_checklist TEXT,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        print("All Phase 1 tables created successfully!")
        
        # Insert default agreement templates
        print("Inserting default agreement templates...")
        default_templates = [
            {
                'name': 'Kitchen Renovation Agreement',
                'type': 'Kitchen',
                'content': 'Standard kitchen renovation agreement template with comprehensive terms and conditions.',
                'terms': 'Standard terms for kitchen renovation projects including material specifications, timeline expectations, and quality standards.',
                'milestones': '[{"title": "Design and Planning", "percentage": 10}, {"title": "Demolition", "percentage": 20}, {"title": "Plumbing and Electrical", "percentage": 40}, {"title": "Installation", "percentage": 80}, {"title": "Final Touches", "percentage": 100}]',
                'checklist': '[{"item": "All appliances installed and functional", "required": true}, {"item": "Plumbing connections tested", "required": true}, {"item": "Electrical work inspected", "required": true}, {"item": "Final cleanup completed", "required": true}]'
            },
            {
                'name': 'Bathroom Renovation Agreement',
                'type': 'Bathroom',
                'content': 'Standard bathroom renovation agreement template with plumbing and tiling specifications.',
                'terms': 'Standard terms for bathroom renovation projects including waterproofing, fixture installation, and finishing work.',
                'milestones': '[{"title": "Planning and Permits", "percentage": 15}, {"title": "Demolition", "percentage": 25}, {"title": "Plumbing and Electrical", "percentage": 50}, {"title": "Tiling and Fixtures", "percentage": 85}, {"title": "Final Inspection", "percentage": 100}]',
                'checklist': '[{"item": "Waterproofing completed and tested", "required": true}, {"item": "All fixtures installed and functional", "required": true}, {"item": "Tiling work completed", "required": true}, {"item": "Ventilation system operational", "required": true}]'
            },
            {
                'name': 'General Home Improvement Agreement',
                'type': 'General',
                'content': 'Flexible agreement template for various home improvement projects.',
                'terms': 'General terms and conditions applicable to most home improvement projects.',
                'milestones': '[{"title": "Project Planning", "percentage": 20}, {"title": "Material Procurement", "percentage": 40}, {"title": "Implementation", "percentage": 80}, {"title": "Final Review", "percentage": 100}]',
                'checklist': '[{"item": "Work completed as specified", "required": true}, {"item": "Area cleaned and restored", "required": true}, {"item": "All materials properly disposed", "required": true}]'
            }
        ]
        
        for template in default_templates:
            cursor.execute('''
                INSERT OR IGNORE INTO agreement_templates 
                (template_name, project_type, template_content, default_terms, default_milestones, default_checklist)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                template['name'], template['type'], template['content'], 
                template['terms'], template['milestones'], template['checklist']
            ))
        
        conn.commit()
        print("Default templates inserted successfully!")
        
    except Exception as e:
        print(f"Error creating Phase 1 tables: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Starting Phase 1 Database Migration...")
    print(f"Migration started at: {datetime.now()}")
    
    try:
        create_phase1_tables()
        print("\n✅ Phase 1 Database Migration completed successfully!")
        print("\nNew tables created:")
        print("- project_agreements")
        print("- project_milestones")
        print("- milestone_evidence")
        print("- project_disputes")
        print("- dispute_evidence")
        print("- project_completion_checklist")
        print("- agreement_templates")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        exit(1)
    
    print(f"\nMigration completed at: {datetime.now()}")