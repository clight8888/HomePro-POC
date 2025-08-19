#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_users_table():
    """Check the structure of the users table"""
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        
        cursor.execute('DESCRIBE users')
        print('USERS TABLE STRUCTURE:')
        print('=' * 50)
        for row in cursor.fetchall():
            print(f'  {row[0]} - {row[1]} - {row[2]} - {row[3]} - {row[4]} - {row[5]}')
        
        # Check if there are any users
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        print(f'\nTotal users in table: {count}')
        
        if count > 0:
            cursor.execute('SELECT id, email, first_name, last_name, role FROM users LIMIT 5')
            print('\nSample users:')
            for row in cursor.fetchall():
                print(f'  ID: {row[0]}, Email: {row[1]}, Name: {row[2]} {row[3]}, Role: {row[4]}')
        
        conn.close()
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    check_users_table()