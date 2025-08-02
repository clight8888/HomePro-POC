#!/usr/bin/env python3
"""
Script to clean up projects with generic transcription messages
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

def cleanup_generic_projects():
    """Find and clean up projects with generic transcription messages"""
    
    generic_messages = [
        "I need help with a home improvement project. Please provide professional services and a quote for the work needed.",
        "Bathroom Renovation",  # The old hardcoded title
        "Mock transcribed text: I need to fix my kitchen sink. It's been leaking for a week and I think it needs professional attention.",
        "Mock transcribed text: I need to fix my kitchen..."
    ]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Checking for projects with generic transcription messages...")
        
        # Find projects with generic messages
        for message in generic_messages:
            cursor.execute("""
                SELECT id, title, description, created_at 
                FROM projects 
                WHERE description = %s OR title = %s OR description LIKE %s
            """, (message, message, f"{message}%"))
            
            projects = cursor.fetchall()
            
            if projects:
                print(f"\n📋 Found {len(projects)} projects with generic message: '{message[:50]}...'")
                
                for project in projects:
                    print(f"  - Project ID: {project['id']}")
                    print(f"    Title: {project['title']}")
                    print(f"    Created: {project['created_at']}")
                    print(f"    Description: {project['description'][:100]}...")
                
                # Ask for confirmation to delete
                response = input(f"\n❓ Delete these {len(projects)} projects? (y/N): ").strip().lower()
                
                if response == 'y':
                    # Delete the projects
                    project_ids = [str(p['id']) for p in projects]
                    placeholders = ','.join(['%s'] * len(project_ids))
                    
                    # Delete related bids first (foreign key constraint)
                    cursor.execute(f"DELETE FROM bids WHERE project_id IN ({placeholders})", project_ids)
                    deleted_bids = cursor.rowcount
                    
                    # Delete the projects
                    cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
                    deleted_projects = cursor.rowcount
                    
                    conn.commit()
                    
                    print(f"✅ Deleted {deleted_projects} projects and {deleted_bids} related bids")
                else:
                    print("❌ Skipped deletion")
            else:
                print(f"✅ No projects found with message: '{message[:50]}...'")
        
        # Show remaining projects
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        total_projects = cursor.fetchone()['count']
        print(f"\n📊 Total projects remaining in database: {total_projects}")
        
        if total_projects > 0:
            cursor.execute("""
                SELECT id, title, description, created_at 
                FROM projects 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_projects = cursor.fetchall()
            
            print("\n📋 Recent projects:")
            for project in recent_projects:
                print(f"  - ID: {project['id']} | {project['title']} | {project['created_at']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_generic_projects()