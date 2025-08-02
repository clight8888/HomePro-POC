#!/usr/bin/env python3
"""
Generate sample data for testing the HomePro admin portal.
This script creates sample users, projects, bids, and other data for demonstration.
"""

import sqlite3
import hashlib
import random
from datetime import datetime, timedelta
import os

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_sample_data():
    """Generate comprehensive sample data for testing"""
    
    # Get database path
    db_path = os.environ.get('DATABASE_URL', 'homepro.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Generating sample data...")
        
        # Sample data
        homeowner_names = [
            ("John", "Smith"), ("Sarah", "Johnson"), ("Michael", "Brown"), 
            ("Emily", "Davis"), ("David", "Wilson"), ("Lisa", "Miller"),
            ("Robert", "Garcia"), ("Jennifer", "Martinez"), ("William", "Anderson"),
            ("Jessica", "Taylor")
        ]
        
        contractor_names = [
            ("Mike", "Thompson"), ("Anna", "Rodriguez"), ("Chris", "Lee"),
            ("Maria", "Gonzalez"), ("James", "White"), ("Linda", "Harris"),
            ("Kevin", "Clark"), ("Susan", "Lewis"), ("Brian", "Walker"),
            ("Karen", "Hall")
        ]
        
        project_types = [
            "Kitchen Renovation", "Bathroom Remodel", "Roof Repair", 
            "Plumbing Installation", "Electrical Work", "Flooring",
            "Painting", "HVAC Installation", "Deck Construction", "Landscaping"
        ]
        
        cities = [
            "Seattle", "Portland", "San Francisco", "Los Angeles", "Denver",
            "Austin", "Chicago", "New York", "Boston", "Miami"
        ]
        
        # Create homeowners
        homeowner_ids = []
        for i, (first, last) in enumerate(homeowner_names):
            email = f"{first.lower()}.{last.lower()}@email.com"
            password_hash = hash_password("password123")
            created_at = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            
            cursor.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, role,
                                 is_verified, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'homeowner', 1, 1, ?, ?)
            """, (email, password_hash, first, last, created_at, created_at))
            
            user_id = cursor.lastrowid
            homeowner_ids.append(user_id)
            
            # Create homeowner profile
            cursor.execute("""
                INSERT INTO homeowners (user_id, phone, address, city, state, zip_code, created_at)
                VALUES (?, ?, ?, ?, 'WA', ?, ?)
            """, (user_id, f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}", 
                  f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St",
                  random.choice(cities), f"{random.randint(10000, 99999)}", created_at))
        
        # Create contractors
        contractor_ids = []
        for i, (first, last) in enumerate(contractor_names):
            email = f"{first.lower()}.{last.lower()}.contractor@email.com"
            password_hash = hash_password("password123")
            created_at = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            
            cursor.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, role,
                                 is_verified, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'contractor', 1, 1, ?, ?)
            """, (email, password_hash, first, last, created_at, created_at))
            
            user_id = cursor.lastrowid
            contractor_ids.append(user_id)
            
            # Create contractor profile
            cursor.execute("""
                INSERT INTO contractors (user_id, company_name, license_number, phone, 
                                       address, city, state, zip_code, specialties, 
                                       years_experience, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'WA', ?, ?, ?, ?)
            """, (user_id, f"{first} {last} Construction", f"LIC{random.randint(10000, 99999)}",
                  f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                  f"{random.randint(100, 9999)} Business Ave", random.choice(cities),
                  f"{random.randint(10000, 99999)}", random.choice(project_types),
                  random.randint(1, 20), created_at))
        
        # Create projects
        project_ids = []
        statuses = ['open', 'in_progress', 'completed', 'cancelled']
        
        for i in range(25):  # Create 25 projects
            homeowner_id = random.choice(homeowner_ids)
            project_type = random.choice(project_types)
            status = random.choice(statuses)
            created_at = (datetime.now() - timedelta(days=random.randint(1, 180))).isoformat()
            
            budget_min = random.randint(1000, 5000)
            budget_max = budget_min + random.randint(1000, 10000)
            
            cursor.execute("""
                INSERT INTO projects (homeowner_id, title, description, project_type,
                                    budget_min, budget_max, timeline, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (homeowner_id, f"{project_type} Project", 
                  f"Professional {project_type.lower()} needed for residential property.",
                  project_type, budget_min, budget_max, f"{random.randint(1, 8)} weeks",
                  status, created_at, created_at))
            
            project_ids.append(cursor.lastrowid)
        
        # Create bids
        for project_id in project_ids:
            # Get project details
            cursor.execute("SELECT budget_min, budget_max FROM projects WHERE id = ?", (project_id,))
            budget_min, budget_max = cursor.fetchone()
            
            # Create 2-5 bids per project
            num_bids = random.randint(2, 5)
            selected_contractors = random.sample(contractor_ids, min(num_bids, len(contractor_ids)))
            
            for contractor_id in selected_contractors:
                bid_amount = random.randint(budget_min, budget_max + 2000)
                timeline = f"{random.randint(1, 12)} weeks"
                created_at = (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
                
                cursor.execute("""
                    INSERT INTO bids (project_id, contractor_id, amount, timeline, 
                                    message, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (project_id, contractor_id, bid_amount, timeline,
                      f"I can complete this project within {timeline} with high quality materials.",
                      created_at, created_at))
        
        # Create system metrics
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):  # 30 days of metrics
            date = base_date + timedelta(days=i)
            
            cursor.execute("""
                INSERT INTO system_metrics (metric_name, metric_value, metric_date, created_at)
                VALUES (?, ?, ?, ?)
            """, ("daily_active_users", random.randint(50, 200), date.date().isoformat(), date.isoformat()))
            
            cursor.execute("""
                INSERT INTO system_metrics (metric_name, metric_value, metric_date, created_at)
                VALUES (?, ?, ?, ?)
            """, ("new_projects", random.randint(1, 10), date.date().isoformat(), date.isoformat()))
            
            cursor.execute("""
                INSERT INTO system_metrics (metric_name, metric_value, metric_date, created_at)
                VALUES (?, ?, ?, ?)
            """, ("revenue", random.randint(1000, 5000), date.date().isoformat(), date.isoformat()))
        
        # Create some user verification requests
        for i in range(5):
            user_id = random.choice(contractor_ids)
            created_at = (datetime.now() - timedelta(days=random.randint(1, 7))).isoformat()
            
            cursor.execute("""
                INSERT INTO user_verification (user_id, verification_type, status, 
                                             submitted_at, documents)
                VALUES (?, 'license', 'pending', ?, ?)
            """, (user_id, created_at, "license.pdf,insurance.pdf"))
        
        # Create some content moderation items
        content_items = [
            ("project", "Inappropriate project description"),
            ("profile", "Suspicious contractor profile"),
            ("bid", "Spam bid message"),
            ("review", "Fake review content")
        ]
        
        for i in range(8):
            content_type, reason = random.choice(content_items)
            target_id = random.randint(1, 25)
            created_at = (datetime.now() - timedelta(days=random.randint(1, 14))).isoformat()
            
            cursor.execute("""
                INSERT INTO content_moderation (content_type, content_id, reported_by,
                                              reason, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (content_type, target_id, random.choice(homeowner_ids + contractor_ids),
                  reason, created_at))
        
        conn.commit()
        conn.close()
        
        print("✅ Sample data generated successfully!")
        print(f"Created:")
        print(f"  - {len(homeowner_names)} homeowners")
        print(f"  - {len(contractor_names)} contractors") 
        print(f"  - 25 projects")
        print(f"  - Multiple bids per project")
        print(f"  - 30 days of system metrics")
        print(f"  - 5 verification requests")
        print(f"  - 8 content moderation items")
        print()
        print("Sample login credentials:")
        print("Homeowner: john.smith@email.com / password123")
        print("Contractor: mike.thompson.contractor@email.com / password123")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("HomePro Sample Data Generator")
    print("============================")
    print()
    
    # Check if database exists
    db_path = os.environ.get('DATABASE_URL', 'homepro.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        print("Please run the application first to initialize the database")
        exit(1)
    
    # Generate sample data
    if generate_sample_data():
        print("Sample data generation completed successfully!")
    else:
        print("Sample data generation failed!")
        exit(1)