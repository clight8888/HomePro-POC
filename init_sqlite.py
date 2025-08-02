#!/usr/bin/env python3
"""
Initialize SQLite database with sample data for testing
"""
import sqlite3
import os
from datetime import datetime

def init_sqlite_db():
    """Initialize SQLite database with basic tables and sample data"""
    
    # Remove existing database
    if os.path.exists('homepro.db'):
        os.remove('homepro.db')
    
    conn = sqlite3.connect('homepro.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('homeowner', 'contractor')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create homeowners table
    cursor.execute('''
        CREATE TABLE homeowners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create contractors table
    cursor.execute('''
        CREATE TABLE contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT,
            company TEXT,
            specialties TEXT,
            business_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create projects table
    cursor.execute('''
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            project_type TEXT NOT NULL,
            location TEXT,
            budget_min REAL,
            budget_max REAL,
            timeline TEXT,
            status TEXT DEFAULT 'Active' CHECK (status IN ('Active', 'Completed', 'Closed')),
            original_file_path TEXT,
            ai_processed_text TEXT,
            homeowner_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (homeowner_id) REFERENCES homeowners(id) ON DELETE CASCADE
        )
    ''')
    
    # Create bids table
    cursor.execute('''
        CREATE TABLE bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            timeline TEXT,
            description TEXT,
            status TEXT DEFAULT 'Submitted' CHECK (status IN ('Submitted', 'Accepted', 'Rejected', 'Withdrawn', 'Expired')),
            project_id INTEGER NOT NULL,
            contractor_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NULL,
            withdrawn_at TIMESTAMP NULL,
            withdrawal_reason TEXT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE
        )
    ''')
    
    # Insert sample data
    # Sample user (homeowner)
    cursor.execute('''
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES ('test@example.com', 'dummy_hash', 'John', 'Doe', 'homeowner')
    ''')
    
    # Sample homeowner
    cursor.execute('''
        INSERT INTO homeowners (user_id, location)
        VALUES (1, 'San Francisco, CA')
    ''')
    
    # Sample project with audio file
    cursor.execute('''
        INSERT INTO projects (title, description, project_type, location, budget_min, budget_max, 
                            timeline, original_file_path, ai_processed_text, homeowner_id)
        VALUES ('Kitchen Renovation', 'Complete kitchen remodel with new cabinets and appliances', 
                'Kitchen', 'San Francisco, CA', 15000, 25000, '2-3 months', 
                'uploads/sample_audio.mp3', 'AI processed description of kitchen renovation project', 1)
    ''')
    
    # Sample contractor
    cursor.execute('''
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES ('contractor@example.com', 'dummy_hash', 'Jane', 'Smith', 'contractor')
    ''')
    
    cursor.execute('''
        INSERT INTO contractors (user_id, location, company, specialties)
        VALUES (2, 'San Francisco, CA', 'Smith Construction', 'Kitchen, Bathroom, General Contracting')
    ''')
    
    # Sample bid
    cursor.execute('''
        INSERT INTO bids (amount, timeline, description, project_id, contractor_id)
        VALUES (20000, '6-8 weeks', 'Complete kitchen renovation with premium materials', 1, 1)
    ''')
    
    conn.commit()
    conn.close()
    
    print("SQLite database initialized successfully!")
    print("Sample data created:")
    print("- 1 homeowner (test@example.com)")
    print("- 1 contractor (contractor@example.com)")
    print("- 1 project with audio file")
    print("- 1 bid")

if __name__ == "__main__":
    init_sqlite_db()