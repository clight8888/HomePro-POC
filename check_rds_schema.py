#!/usr/bin/env python3
"""
Check the current RDS MySQL database schema to understand the table structure.
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

def check_table_schema():
    """Check the schema of existing tables"""
    
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        print("RDS MySQL Database Schema Check")
        print("===============================")
        print()
        
        # Check users table
        print("USERS TABLE STRUCTURE:")
        print("----------------------")
        cursor.execute("DESCRIBE users")
        for row in cursor.fetchall():
            print(f"  {row[0]} - {row[1]} - {row[2]} - {row[3]} - {row[4]} - {row[5]}")
        print()
        
        # Check if admin tables exist
        tables_to_check = ['admin_users', 'admin_activity_logs', 'system_metrics', 'user_verification', 'content_moderation']
        
        for table in tables_to_check:
            cursor.execute("SHOW TABLES LIKE %s", (table,))
            if cursor.fetchone():
                print(f"{table.upper()} TABLE STRUCTURE:")
                print("-" * (len(table) + 17))
                cursor.execute(f"DESCRIBE {table}")
                for row in cursor.fetchall():
                    print(f"  {row[0]} - {row[1]} - {row[2]} - {row[3]} - {row[4]} - {row[5]}")
                print()
            else:
                print(f"❌ Table '{table}' does not exist")
                print()
        
        cursor.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    check_table_schema()