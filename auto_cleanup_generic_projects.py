#!/usr/bin/env python3
"""
Script to automatically clean up projects with generic transcription messages
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

def auto_cleanup_generic_projects():
    """Automatically find and clean up projects with generic transcription messages"""
    
    generic_patterns = [
        "I need help with a home improvement project. Please provide professional services and a quote for the work needed.",
        "Bathroom Renovation",
        "Mock transcribed text: I need to fix my kitchen sink. It's been leaking for a week and I think it needs professional attention.",
        "Mock transcribed text: I need to fix my kitchen..."
    ]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Automatically cleaning up projects with generic transcription messages...")
        
        total_deleted_projects = 0
        total_deleted_bids = 0
        
        # Find and delete projects with generic messages
        for pattern in generic_patterns:
            cursor.execute("""
                SELECT id, title, description, created_at 
                FROM projects 
                WHERE description = %s OR title = %s OR description LIKE %s
            """, (pattern, pattern, f"{pattern}%"))
            
            projects = cursor.fetchall()
            
            if projects:
                print(f"\n📋 Found {len(projects)} projects with pattern: '{pattern[:50]}...'")
                
                for project in projects:
                    print(f"  - Deleting Project ID: {project['id']} | {project['title'][:50]}...")
                
                # Delete related bids first (foreign key constraint)
                project_ids = [project['id'] for project in projects]
                placeholders = ','.join(['%s'] * len(project_ids))
                
                cursor.execute(f"DELETE FROM bids WHERE project_id IN ({placeholders})", project_ids)
                deleted_bids = cursor.rowcount
                total_deleted_bids += deleted_bids
                
                # Delete the projects
                cursor.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", project_ids)
                deleted_projects = cursor.rowcount
                total_deleted_projects += deleted_projects
                
                print(f"  ✅ Deleted {deleted_projects} projects and {deleted_bids} related bids")
            else:
                print(f"✅ No projects found with pattern: '{pattern[:50]}...'")
        
        # Commit all changes
        conn.commit()
        
        print(f"\n🎯 CLEANUP SUMMARY:")
        print(f"   Total projects deleted: {total_deleted_projects}")
        print(f"   Total bids deleted: {total_deleted_bids}")
        
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
            
            print("\n📋 Recent projects remaining:")
            for project in recent_projects:
                print(f"  - ID: {project['id']} | {project['title'][:50]} | {project['created_at']}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Cleanup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    auto_cleanup_generic_projects()