#!/usr/bin/env python3
"""
Auto Expire Bids Script
This script automatically expires bids that have passed their expiration date.
Can be run as a cron job or scheduled task.
"""

import sys
import os
from datetime import datetime, timedelta
import logging
import sqlite3

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Get database connection - simplified version for standalone script"""
    try:
        # Try to import pymysql for MySQL connection
        import pymysql
        from app import get_db_connection as app_get_db_connection
        return app_get_db_connection()
    except ImportError:
        # Fall back to SQLite
        db_path = os.path.join(os.path.dirname(__file__), 'homepro.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_expire_bids.log'),
        logging.StreamHandler()
    ]
)

def expire_old_bids():
    """Expire bids that have passed their expiration date"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current timestamp
        current_time = datetime.now()
        
        # Find bids that should be expired
        cursor.execute("""
            SELECT id, project_id, contractor_id, amount, expires_at
            FROM bids 
            WHERE status = 'Submitted' 
            AND expires_at IS NOT NULL 
            AND expires_at <= %s
        """, (current_time,))
        
        expired_bids = cursor.fetchall()
        
        if not expired_bids:
            logging.info("No bids to expire")
            return
        
        logging.info(f"Found {len(expired_bids)} bids to expire")
        
        for bid in expired_bids:
            bid_id, project_id, contractor_id, amount, expires_at = bid
            
            # Update bid status to expired
            cursor.execute("""
                UPDATE bids 
                SET status = 'Expired', last_activity_at = %s
                WHERE id = %s
            """, (current_time, bid_id))
            
            # Get project and contractor details for notifications
            cursor.execute("""
                SELECT p.title, p.homeowner_user_id, c.user_id, c.first_name, c.last_name
                FROM projects p
                JOIN contractors c ON c.id = %s
                WHERE p.id = %s
            """, (contractor_id, project_id))
            
            project_data = cursor.fetchone()
            if project_data:
                project_title, homeowner_user_id, contractor_user_id, contractor_first, contractor_last = project_data
                
                # Create notification for contractor
                cursor.execute("""
                    INSERT INTO bid_notifications (user_id, bid_id, title, message, type, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    contractor_user_id,
                    bid_id,
                    "Bid Expired",
                    f"Your bid of ${amount:.0f} for '{project_title}' has expired.",
                    "bid_expired",
                    current_time
                ))
                
                # Create notification for homeowner
                cursor.execute("""
                    INSERT INTO bid_notifications (user_id, bid_id, title, message, type, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    homeowner_user_id,
                    bid_id,
                    "Bid Expired",
                    f"A bid from {contractor_first} {contractor_last} for '{project_title}' has expired.",
                    "bid_expired",
                    current_time
                ))
                
                logging.info(f"Expired bid {bid_id} for project '{project_title}' (${amount:.0f})")
        
        conn.commit()
        logging.info(f"Successfully expired {len(expired_bids)} bids")
        
    except Exception as e:
        logging.error(f"Error expiring bids: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_old_notifications():
    """Clean up notifications older than 30 days"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete notifications older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        
        cursor.execute("""
            DELETE FROM bid_notifications 
            WHERE created_at < %s
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} old notifications")
        
    except Exception as e:
        logging.error(f"Error cleaning up notifications: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logging.info("Starting auto expire bids task")
    expire_old_bids()
    cleanup_old_notifications()
    logging.info("Auto expire bids task completed")