#!/usr/bin/env python3
"""
Setup script to create the first admin user for the HomePro platform on RDS MySQL.
Run this script to create an initial admin account directly on the AWS RDS database.
"""

import mysql.connector
import hashlib
import getpass
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

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

def create_admin_user():
    """Create the first admin user on RDS MySQL"""
    
    print("HomePro Admin Setup (RDS MySQL)")
    print("===============================")
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
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            print(f"Error: User with email {email} already exists")
            return False
        
        # Create user (using actual RDS schema)
        hashed_password = hash_password(password)
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role, created_at)
            VALUES (%s, %s, %s, %s, 'homeowner', %s)
        """, (email, hashed_password, first_name, last_name, now))
        
        user_id = cursor.lastrowid
        
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
            VALUES (%s, 'create_admin', 'user', %s, %s, 'setup_script', %s)
        """, (admin_user_id, user_id, f'{{"message": "Created super admin: {email}"}}', now))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print()
        print("✅ Admin user created successfully on RDS MySQL!")
        print(f"Email: {email}")
        print(f"Name: {first_name} {last_name}")
        print(f"Admin Level: Super Admin")
        print(f"Database: {os.environ.get('DB_HOST')}")
        print()
        print("You can now log in to the admin portal at /admin")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def check_database_connection():
    """Check if we can connect to RDS MySQL and verify tables exist"""
    
    # Check environment variables
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        print(f"✅ Connected to RDS MySQL: {os.environ.get('DB_HOST')}")
        print(f"✅ Database: {os.environ.get('DB_NAME')}")
        
        # Check for required tables
        required_tables = ['users', 'admin_users', 'admin_activity_logs']
        for table in required_tables:
            cursor.execute("SHOW TABLES LIKE %s", (table,))
            if not cursor.fetchone():
                print(f"❌ Required table '{table}' not found")
                print("Please run the application first to initialize the database")
                return False
            else:
                print(f"✅ Table '{table}' exists")
        
        cursor.close()
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return False

def show_database_info():
    """Show current database configuration"""
    print("Current RDS MySQL Configuration:")
    print("================================")
    print(f"Host: {os.environ.get('DB_HOST', 'Not set')}")
    print(f"Port: {os.environ.get('DB_PORT', 'Not set')}")
    print(f"Database: {os.environ.get('DB_NAME', 'Not set')}")
    print(f"Username: {os.environ.get('DB_USERNAME', 'Not set')}")
    print(f"Password: {'*' * len(os.environ.get('DB_PASSWORD', '')) if os.environ.get('DB_PASSWORD') else 'Not set'}")
    print()

if __name__ == "__main__":
    print("HomePro Admin Setup Script (RDS MySQL)")
    print("======================================")
    print()
    
    # Show database info
    show_database_info()
    
    # Check database connection
    if not check_database_connection():
        print("\n❌ Database connection failed!")
        print("Please check your RDS configuration and ensure the database is accessible.")
        sys.exit(1)
    
    print()
    
    # Create admin user
    if create_admin_user():
        print("✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print("❌ Setup failed!")
        sys.exit(1)