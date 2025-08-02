#!/usr/bin/env python3
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USERNAME', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'homepro_db')
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, title, original_file_path FROM projects WHERE original_file_path IS NOT NULL LIMIT 5')
    projects = cursor.fetchall()
    
    print('Projects with audio files:')
    for project in projects:
        print(f'ID: {project["id"]}, Title: {project["title"]}, File Path: {project["original_file_path"]}')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'Error: {e}')