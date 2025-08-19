#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_homeowners_table():
    """Check the homeowners table"""
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USERNAME'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        
        # Check homeowners count
        cursor.execute('SELECT COUNT(*) FROM homeowners')
        count = cursor.fetchone()[0]
        print(f'Total homeowners: {count}')
        
        if count > 0:
            cursor.execute('''
                SELECT h.id, h.user_id, u.email, u.first_name, u.last_name 
                FROM homeowners h 
                JOIN users u ON h.user_id = u.id 
                LIMIT 5
            ''')
            print('Sample homeowners:')
            for row in cursor.fetchall():
                print(f'  ID: {row[0]}, User ID: {row[1]}, Email: {row[2]}, Name: {row[3]} {row[4]}')
        else:
            print('No homeowners found in the homeowners table!')
            print('This explains the "Homeowner profile not found" error.')
            
            # Check if there are users with homeowner role
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'homeowner'")
            homeowner_users = cursor.fetchone()[0]
            print(f'Users with homeowner role: {homeowner_users}')
            
            if homeowner_users > 0:
                print('There are users with homeowner role but no homeowner profiles!')
                print('Need to create homeowner profiles for existing homeowner users.')
        
        conn.close()
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    check_homeowners_table()