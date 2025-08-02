#!/usr/bin/env python3
"""
Script to upgrade an existing user to admin status in the RDS MySQL database.
"""

import mysql.connector
import os
from datetime import datetime
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

def upgrade_user_to_admin():
    """Upgrade an existing user to admin status"""
    
    print("HomePro RDS MySQL - Upgrade User to Admin")
    print("=========================================")
    print()
    
    email = input("Enter email of user to upgrade to admin: ").strip()
    if not email:
        print("Error: Email is required")
        return False
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email, first_name, last_name, role FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User with email {email} not found")
            return False
        
        user_id, user_email, first_name, last_name, role = user
        
        print(f"Found user: {first_name} {last_name} ({user_email})")
        print(f"Current role: {role}")
        print()
        
        # Check if user is already an admin
        cursor.execute("SELECT id FROM admin_users WHERE user_id = %s", (user_id,))
        if cursor.fetchone():
            print(f"Error: User {email} is already an admin")
            return False
        
        # Confirm upgrade
        confirm = input(f"Upgrade {first_name} {last_name} to super admin? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Upgrade cancelled")
            return False
        
        now = datetime.now()
        
        # Create admin user record
        cursor.execute("""
            INSERT INTO admin_users (user_id, admin_level, permissions, created_by, created_at)
            VALUES (%s, 'super_admin', %s, %s, %s)
        """, (user_id, '{"all": true}', user_id, now))
        
        admin_user_id = cursor.lastrowid
        
        # Log admin creation
        cursor.execute("""
            INSERT INTO admin_activity_logs (admin_user_id, action, target_type, target_id, 
                                           details, ip_address, created_at)
            VALUES (%s, 'upgrade_to_admin', 'user', %s, %s, 'upgrade_script', %s)
        """, (admin_user_id, user_id, f'{{"message": "Upgraded user to super admin: {email}"}}', now))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print()
        print("✅ User successfully upgraded to admin!")
        print(f"Email: {email}")
        print(f"Name: {first_name} {last_name}")
        print(f"Admin Level: Super Admin")
        print(f"Admin User ID: {admin_user_id}")
        print()
        print("The user can now access the admin portal at /admin")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if upgrade_user_to_admin():
        print("✅ Upgrade completed successfully!")
    else:
        print("❌ Upgrade failed!")