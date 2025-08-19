#!/usr/bin/env python3
"""
Database schema update for evidence system
This script updates the milestone_evidence table and creates the evidence_files table
to support the new evidence submission and review system.
"""

import sqlite3
import os
from datetime import datetime

def get_db_connection():
    """Get database connection"""
    db_path = 'homepro.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def update_evidence_schema():
    """Update the evidence schema to support the new system"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Updating evidence schema...")
        
        # Check if milestone_evidence table exists and get its current structure
        cursor.execute("PRAGMA table_info(milestone_evidence)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add new columns if they don't exist
        new_columns = {
            'status': "TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected'))",
            'submitted_at': "TEXT",
            'reviewed_at': "TEXT",
            'reviewer_notes': "TEXT"
        }
        
        for column_name, column_def in new_columns.items():
            if column_name not in columns:
                print(f"Adding column {column_name} to milestone_evidence table...")
                cursor.execute(f"ALTER TABLE milestone_evidence ADD COLUMN {column_name} {column_def}")
        
        # Update existing records to have submitted_at timestamp
        cursor.execute("""
            UPDATE milestone_evidence 
            SET submitted_at = upload_date 
            WHERE submitted_at IS NULL AND upload_date IS NOT NULL
        """)
        
        # Update existing records to have current timestamp if no upload_date
        cursor.execute("""
            UPDATE milestone_evidence 
            SET submitted_at = ? 
            WHERE submitted_at IS NULL
        """, (datetime.now().isoformat(),))
        
        # Create evidence_files table for multiple file support
        print("Creating evidence_files table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                thumbnail_path TEXT,
                file_size INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES milestone_evidence (id) ON DELETE CASCADE
            )
        """)
        
        # Migrate existing file data to evidence_files table
        print("Migrating existing file data...")
        cursor.execute("""
            SELECT id, file_path, original_filename, file_size, upload_date
            FROM milestone_evidence 
            WHERE file_path IS NOT NULL AND original_filename IS NOT NULL
        """)
        
        existing_files = cursor.fetchall()
        for row in existing_files:
            evidence_id, file_path, original_filename, file_size, upload_date = row
            
            # Extract stored filename from file_path
            stored_filename = os.path.basename(file_path) if file_path else original_filename
            
            # Insert into evidence_files table
            cursor.execute("""
                INSERT INTO evidence_files 
                (evidence_id, original_filename, stored_filename, file_path, file_size, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                evidence_id,
                original_filename,
                stored_filename,
                file_path,
                file_size or 0,
                upload_date or datetime.now().isoformat()
            ))
        
        # Create uploads directory structure
        print("Creating upload directories...")
        upload_dirs = [
            'static/uploads',
            'static/uploads/evidence'
        ]
        
        for directory in upload_dirs:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        
        conn.commit()
        print("Evidence schema update completed successfully!")
        
        # Display updated table structure
        print("\nUpdated milestone_evidence table structure:")
        cursor.execute("PRAGMA table_info(milestone_evidence)")
        for row in cursor.fetchall():
            print(f"  {row[1]} {row[2]} {row[3] if row[3] else ''}")
        
        print("\nEvidence_files table structure:")
        cursor.execute("PRAGMA table_info(evidence_files)")
        for row in cursor.fetchall():
            print(f"  {row[1]} {row[2]} {row[3] if row[3] else ''}")
            
    except Exception as e:
        print(f"Error updating evidence schema: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting evidence schema update...")
    update_evidence_schema()
    print("Evidence schema update completed!")