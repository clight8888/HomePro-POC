#!/usr/bin/env python3
"""
Script to check the projects table structure and data
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection using the same method as Flask app"""
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def check_projects_table():
    """Check projects table structure and data"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Checking projects table structure...")
        
        # Show table structure
        cursor.execute("DESCRIBE projects")
        columns = cursor.fetchall()
        
        print("\nPROJECTS TABLE STRUCTURE:")
        print("=" * 40)
        for column in columns:
            print(f"  {column['Field']} - {column['Type']} - {column['Null']} - {column['Key']} - {column['Default']}")
        
        # Check existing projects
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        total_projects = cursor.fetchone()['count']
        print(f"\n📊 Total projects in database: {total_projects}")
        
        if total_projects > 0:
            # Show recent projects
            cursor.execute("""
                SELECT id, title, description, created_at 
                FROM projects 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_projects = cursor.fetchall()
            
            print("\n📋 Recent projects:")
            for project in recent_projects:
                print(f"  - ID: {project['id']}")
                print(f"    Title: {project['title']}")
                print(f"    Description: {project['description'][:100]}...")
                print(f"    Created: {project['created_at']}")
                print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_projects_table()