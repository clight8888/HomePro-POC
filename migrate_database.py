#!/usr/bin/env python3
"""
Database migration script to add new columns for bid withdrawal and expiration functionality
"""

import os
import pymysql
from datetime import datetime, timedelta

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def migrate_database():
    """Add new columns and tables for bid withdrawal and expiration functionality"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # Check if expires_at column exists in bids table
        cursor.execute("SHOW COLUMNS FROM bids LIKE 'expires_at'")
        if not cursor.fetchone():
            print("Adding expires_at column to bids table...")
            cursor.execute("ALTER TABLE bids ADD COLUMN expires_at DATETIME NULL AFTER created_at")
            
            # Set expires_at for existing bids (30 days from created_at)
            cursor.execute("""
                UPDATE bids 
                SET expires_at = DATE_ADD(created_at, INTERVAL 30 DAY) 
                WHERE expires_at IS NULL
            """)
            print("✓ Added expires_at column and set values for existing bids")
        
        # Check if withdrawn_at column exists
        cursor.execute("SHOW COLUMNS FROM bids LIKE 'withdrawn_at'")
        if not cursor.fetchone():
            print("Adding withdrawn_at column to bids table...")
            cursor.execute("ALTER TABLE bids ADD COLUMN withdrawn_at DATETIME NULL AFTER expires_at")
            print("✓ Added withdrawn_at column")
        
        # Check if withdrawal_reason column exists
        cursor.execute("SHOW COLUMNS FROM bids LIKE 'withdrawal_reason'")
        if not cursor.fetchone():
            print("Adding withdrawal_reason column to bids table...")
            cursor.execute("ALTER TABLE bids ADD COLUMN withdrawal_reason TEXT NULL AFTER withdrawn_at")
            print("✓ Added withdrawal_reason column")
        
        # Check if status enum includes new values
        cursor.execute("SHOW COLUMNS FROM bids LIKE 'status'")
        status_column = cursor.fetchone()
        if status_column and 'Withdrawn' not in status_column['Type']:
            print("Updating status enum to include Withdrawn and Expired...")
            cursor.execute("""
                ALTER TABLE bids 
                MODIFY COLUMN status ENUM('Submitted', 'Accepted', 'Rejected', 'Withdrawn', 'Expired') 
                DEFAULT 'Submitted'
            """)
            print("✓ Updated status enum")
        
        # Check if bid_history table exists
        cursor.execute("SHOW TABLES LIKE 'bid_history'")
        if not cursor.fetchone():
            print("Creating bid_history table...")
            cursor.execute('''
                CREATE TABLE bid_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bid_id INT NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    old_status VARCHAR(20),
                    new_status VARCHAR(20),
                    old_amount DECIMAL(10,2),
                    new_amount DECIMAL(10,2),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
                    INDEX idx_bid_id (bid_id),
                    INDEX idx_created_at (created_at)
                )
            ''')
            print("✓ Created bid_history table")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    migrate_database()