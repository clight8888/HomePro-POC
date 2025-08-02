#!/usr/bin/env python3
"""
Script to change password for an existing user in the RDS MySQL database.
"""

import mysql.connector
from werkzeug.security import generate_password_hash
import getpass
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

def change_user_password():
    """Change password for an existing user"""
    
    print("HomePro RDS MySQL - Change User Password")
    print("=======================================")
    print()
    
    email = input("Enter email of user to change password: ").strip()
    if not email:
        print("Error: Email is required")
        return False
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User with email {email} not found")
            return False
        
        user_id, user_email, first_name, last_name = user
        
        print(f"Found user: {first_name} {last_name} ({user_email})")
        print()
        
        # Get new password
        new_password = getpass.getpass("Enter new password: ")
        if len(new_password) < 8:
            print("Error: Password must be at least 8 characters")
            return False
        
        confirm_password = getpass.getpass("Confirm new password: ")
        if new_password != confirm_password:
            print("Error: Passwords do not match")
            return False
        
        # Confirm password change
        confirm = input(f"Change password for {first_name} {last_name}? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Password change cancelled")
            return False
        
        # Update password using Werkzeug's password hashing (same as the app)
        hashed_password = generate_password_hash(new_password)
        
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE id = %s
        """, (hashed_password, user_id))
        
        # Check if user is an admin and log the activity
        cursor.execute("SELECT id FROM admin_users WHERE user_id = %s", (user_id,))
        admin_record = cursor.fetchone()
        
        if admin_record:
            from datetime import datetime
            admin_user_id = admin_record[0]
            now = datetime.now()
            
            cursor.execute("""
                INSERT INTO admin_activity_logs (admin_user_id, action, target_type, target_id, 
                                               details, ip_address, created_at)
                VALUES (%s, 'password_change', 'user', %s, %s, 'password_script', %s)
            """, (admin_user_id, user_id, f'{{"message": "Password changed for user: {email}"}}', now))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print()
        print("✅ Password successfully changed!")
        print(f"Email: {email}")
        print(f"Name: {first_name} {last_name}")
        print("🔧 Using Werkzeug password hashing (compatible with app)")
        print()
        print("The user can now log in with the new password.")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if change_user_password():
        print("✅ Password change completed successfully!")
    else:
        print("❌ Password change failed!")