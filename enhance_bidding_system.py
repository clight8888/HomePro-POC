#!/usr/bin/env python3
"""
Database migration script to enhance the bidding system with:
1. Bid negotiation messaging
2. Enhanced bid comparison features
3. Automatic bid expiration handling
"""

import mysql.connector
import sqlite3
import os
from datetime import datetime, timedelta
from app import get_db_connection

def enhance_bidding_system():
    """Add new tables and features for advanced bidding"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Enhancing bidding system...")
        
        # Create bid_messages table for negotiation
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bid_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bid_id INT NOT NULL,
                    sender_id INT NOT NULL,
                    receiver_id INT NOT NULL,
                    message_type ENUM('negotiation', 'question', 'clarification', 'counter_offer') DEFAULT 'negotiation',
                    message_text TEXT NOT NULL,
                    proposed_amount DECIMAL(10,2) NULL,
                    proposed_timeline VARCHAR(255) NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_bid (bid_id),
                    INDEX idx_sender (sender_id),
                    INDEX idx_receiver (receiver_id),
                    INDEX idx_created (created_at),
                    INDEX idx_read (is_read)
                )
            ''')
            print("✓ Created bid_messages table")
        except Exception as e:
            print(f"Note: bid_messages table may already exist: {e}")
        
        # Create bid_comparisons table to save comparison sessions
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bid_comparisons (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    homeowner_id INT NOT NULL,
                    bid_ids JSON NOT NULL,
                    comparison_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE,
                    INDEX idx_project (project_id),
                    INDEX idx_homeowner (homeowner_id),
                    INDEX idx_created (created_at)
                )
            ''')
            print("✓ Created bid_comparisons table")
        except Exception as e:
            print(f"Note: bid_comparisons table may already exist: {e}")
        
        # Create bid_notifications table for automated notifications
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bid_notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bid_id INT NOT NULL,
                    user_id INT NOT NULL,
                    notification_type ENUM('expiring_soon', 'expired', 'new_message', 'counter_offer', 'bid_accepted', 'bid_rejected') NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_bid (bid_id),
                    INDEX idx_user (user_id),
                    INDEX idx_type (notification_type),
                    INDEX idx_read (is_read),
                    INDEX idx_created (created_at)
                )
            ''')
            print("✓ Created bid_notifications table")
        except Exception as e:
            print(f"Note: bid_notifications table may already exist: {e}")
        
        # Add new columns to bids table if they don't exist
        try:
            # Check if negotiation_allowed column exists
            cursor.execute("SHOW COLUMNS FROM bids LIKE 'negotiation_allowed'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bids ADD COLUMN negotiation_allowed BOOLEAN DEFAULT TRUE")
                print("✓ Added negotiation_allowed column to bids table")
        except Exception as e:
            print(f"Note: negotiation_allowed column may already exist: {e}")
        
        try:
            # Check if auto_expire_enabled column exists
            cursor.execute("SHOW COLUMNS FROM bids LIKE 'auto_expire_enabled'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bids ADD COLUMN auto_expire_enabled BOOLEAN DEFAULT TRUE")
                print("✓ Added auto_expire_enabled column to bids table")
        except Exception as e:
            print(f"Note: auto_expire_enabled column may already exist: {e}")
        
        try:
            # Check if last_activity_at column exists
            cursor.execute("SHOW COLUMNS FROM bids LIKE 'last_activity_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bids ADD COLUMN last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
                print("✓ Added last_activity_at column to bids table")
        except Exception as e:
            print(f"Note: last_activity_at column may already exist: {e}")
        
        # Update existing bids to have expiration dates if they don't
        cursor.execute("UPDATE bids SET expires_at = DATE_ADD(created_at, INTERVAL 30 DAY) WHERE expires_at IS NULL")
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            print(f"✓ Updated {updated_rows} bids with expiration dates")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Bidding system enhancement completed successfully!")
        
    except Exception as e:
        print(f"❌ Error enhancing bidding system: {e}")
        if 'conn' in locals():
            conn.rollback()
            cursor.close()
            conn.close()

def enhance_sqlite_bidding():
    """Enhance SQLite database for local testing"""
    
    if not os.path.exists('homepro.db'):
        print("SQLite database not found. Run init_sqlite.py first.")
        return
    
    conn = sqlite3.connect('homepro.db')
    cursor = conn.cursor()
    
    try:
        # Create bid_messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bid_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bid_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message_type TEXT DEFAULT 'negotiation' CHECK (message_type IN ('negotiation', 'question', 'clarification', 'counter_offer')),
                message_text TEXT NOT NULL,
                proposed_amount REAL NULL,
                proposed_timeline TEXT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create bid_comparisons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bid_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                homeowner_id INTEGER NOT NULL,
                bid_ids TEXT NOT NULL,
                comparison_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE
            )
        ''')
        
        # Create bid_notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bid_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bid_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL CHECK (notification_type IN ('expiring_soon', 'expired', 'new_message', 'counter_offer', 'bid_accepted', 'bid_rejected')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bid_id) REFERENCES bids(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Add new columns to bids table if they don't exist
        try:
            cursor.execute("ALTER TABLE bids ADD COLUMN negotiation_allowed BOOLEAN DEFAULT TRUE")
        except:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE bids ADD COLUMN auto_expire_enabled BOOLEAN DEFAULT TRUE")
        except:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE bids ADD COLUMN last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
            pass  # Column already exists
        
        # Update existing bids to have expiration dates
        cursor.execute("UPDATE bids SET expires_at = datetime(created_at, '+30 days') WHERE expires_at IS NULL")
        
        conn.commit()
        print("✅ SQLite bidding system enhancement completed!")
        
    except Exception as e:
        print(f"❌ Error enhancing SQLite bidding system: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Enhancing bidding system...")
    print("1. Trying MySQL/RDS connection...")
    try:
        enhance_bidding_system()
    except Exception as e:
        print(f"MySQL failed: {e}")
        print("2. Falling back to SQLite...")
        enhance_sqlite_bidding()