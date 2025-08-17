#!/usr/bin/env python3
"""
Fix contractor table by adding missing columns for enhanced onboarding.
This script will add the new columns to the existing contractors table.
"""

import sqlite3
import os

def get_db_connection():
    """Get SQLite database connection"""
    db_path = 'homepro.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def add_missing_columns():
    """Add missing columns to contractors table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        print("Checking and adding missing columns to contractors table...")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(contractors)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Define new columns to add
        new_columns = [
            ("onboarding_completed", "BOOLEAN DEFAULT FALSE"),
            ("service_area_lat", "REAL"),
            ("service_area_lng", "REAL"),
            ("service_radius", "INTEGER DEFAULT 25"),
            ("portfolio_images", "TEXT"),
            ("license_number", "TEXT"),
            ("license_state", "TEXT"),
            ("insurance_provider", "TEXT"),
            ("insurance_policy", "TEXT"),
            ("profile_completion_score", "INTEGER DEFAULT 0"),
            ("bio", "TEXT"),
            ("years_experience", "INTEGER DEFAULT 0"),
            ("portfolio", "TEXT")
        ]
        
        # Add missing columns
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE contractors ADD COLUMN {column_name} {column_definition}")
                print(f"✓ Added {column_name}")
            else:
                print(f"✓ Column {column_name} already exists")
        
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(contractors)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"\nUpdated table structure:")
        for column in updated_columns:
            print(f"  - {column}")
        
        print("\n✅ Successfully updated contractors table!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating table: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("HomePro Contractor Table Fix")
    print("=" * 40)
    
    success = add_missing_columns()
    
    if success:
        print("\n🎉 Table update completed successfully!")
        print("You can now register contractors with the enhanced onboarding flow.")
    else:
        print("\n💥 Table update failed. Please check the error messages above.")