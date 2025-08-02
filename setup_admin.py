#!/usr/bin/env python3
"""
Setup script to create the first admin user for the HomePro platform.
Run this script after deploying the application to create an initial admin account.
"""

import sqlite3
import hashlib
import getpass
from datetime import datetime
import os
import sys

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user():
    """Create the first admin user"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_URL', 'homepro.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]  # Remove sqlite:/// prefix
    
    print("HomePro Admin Setup")
    print("==================")
    print()
    
    # Get admin details
    print("Creating the first admin user...")
    email = input("Admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return False
    
    first_name = input("First name: ").strip()
    if not first_name:
        print("Error: First name is required")
        return False
    
    last_name = input("Last name: ").strip()
    if not last_name:
        print("Error: Last name is required")
        return False
    
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return False
    
    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("Error: Passwords do not match")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"Error: User with email {email} already exists")
            return False
        
        # Create user
        hashed_password = hash_password(password)
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role, 
                             is_verified, is_active, created_at, updated_at, is_admin)
            VALUES (?, ?, ?, ?, 'homeowner', 1, 1, ?, ?, 1)
        """, (email, hashed_password, first_name, last_name, now, now))
        
        user_id = cursor.lastrowid
        
        # Create admin user record
        cursor.execute("""
            INSERT INTO admin_users (user_id, admin_level, permissions, created_by, created_at)
            VALUES (?, 'super_admin', 'all', ?, ?)
        """, (user_id, user_id, now))
        
        # Log admin creation
        cursor.execute("""
            INSERT INTO admin_activity_logs (admin_id, action, target_type, target_id, 
                                           details, ip_address, created_at)
            VALUES (?, 'create_admin', 'user', ?, ?, 'setup_script', ?)
        """, (user_id, user_id, f"Created super admin: {email}", now))
        
        conn.commit()
        conn.close()
        
        print()
        print("✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Name: {first_name} {last_name}")
        print(f"Admin Level: Super Admin")
        print()
        print("You can now log in to the admin portal at /admin")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def check_database():
    """Check if database exists and has required tables"""
    db_path = os.environ.get('DATABASE_URL', 'homepro.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        print("Please run the application first to initialize the database")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = ['users', 'admin_users', 'admin_activity_logs']
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                print(f"Error: Required table '{table}' not found")
                print("Please run the application first to initialize the database")
                return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    print("HomePro Admin Setup Script")
    print("=========================")
    print()
    
    # Check database
    if not check_database():
        sys.exit(1)
    
    # Create admin user
    if create_admin_user():
        print("Setup completed successfully!")
        sys.exit(0)
    else:
        print("Setup failed!")
        sys.exit(1)