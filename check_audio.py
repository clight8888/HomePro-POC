#!/usr/bin/env python3

import mysql.connector
import os
from config import *

def get_db_connection():
    """Get database connection with fallback to SQLite"""
    try:
        # Try MySQL connection first
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USERNAME', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'homepro'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        print("Connected to MySQL database")
        return connection
    except mysql.connector.Error as e:
        print(f"MySQL connection failed: {e}")
        print("Falling back to SQLite...")
        import sqlite3
        connection = sqlite3.connect('homepro.db')
        connection.row_factory = sqlite3.Row
        print("Connected to SQLite database")
        return connection

def check_project_audio():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # List all projects first
    cursor.execute('SELECT id, title, original_file_path FROM projects ORDER BY id')
    projects = cursor.fetchall()
    
    print(f"Found {len(projects)} projects:")
    for project in projects:
        project_id = project[0] if len(project) > 0 else project['id']
        title = project[1] if len(project) > 1 else project['title']
        audio_path = project[2] if len(project) > 2 else project['original_file_path']
        
        print(f"  Project {project_id}: {title}")
        if audio_path:
            print(f"    Audio file: {audio_path}")
            # Check if file exists locally
            if audio_path.startswith('uploads/'):
                local_path = os.path.join('static', audio_path)
                print(f"    Local file exists: {os.path.exists(local_path)}")
        else:
            print(f"    No audio file")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_project_audio()