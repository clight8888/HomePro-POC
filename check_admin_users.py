#!/usr/bin/env python3
"""
Script to check existing users and admin status in the RDS MySQL database.
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            port=int(os.environ.get('DB_PORT', 3306)),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USERNAME'),
            password=os.environ.get('DB_PASSWORD'),
            autocommit=True
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def check_users():
    """Check existing users and their admin status"""
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        print("HomePro RDS MySQL - User Status Check")
        print("====================================")
        print()
        
        # Get all users
        cursor.execute("""
            SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.created_at,
                   au.id as admin_id, au.admin_level, au.permissions
            FROM users u
            LEFT JOIN admin_users au ON u.id = au.user_id
            ORDER BY u.created_at DESC
        """)
        
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
            return True
        
        print(f"Found {len(users)} user(s):")
        print()
        
        for user in users:
            user_id, email, first_name, last_name, role, created_at, admin_id, admin_level, permissions = user
            
            print(f"User ID: {user_id}")
            print(f"Email: {email}")
            print(f"Name: {first_name} {last_name}")
            print(f"Role: {role}")
            print(f"Created: {created_at}")
            
            if admin_id:
                print(f"✅ ADMIN STATUS: {admin_level}")
                print(f"Admin ID: {admin_id}")
                print(f"Permissions: {permissions}")
            else:
                print("❌ Not an admin user")
            
            print("-" * 50)
        
        # Check admin activity logs
        cursor.execute("""
            SELECT COUNT(*) as log_count
            FROM admin_activity_logs
        """)
        
        log_count = cursor.fetchone()[0]
        print(f"\nAdmin Activity Logs: {log_count} entries")
        
        cursor.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    check_users()