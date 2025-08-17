#!/usr/bin/env python3
"""
Database migration script for contractor enhanced onboarding features.
Adds new columns to the contractors table to support the new onboarding flow.
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'homepro'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def migrate_contractors_table():
    """Add new columns to contractors table for enhanced onboarding"""
    connection = get_db_connection()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        print("Starting contractor onboarding migration...")
        
        # Check and add onboarding_completed column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'onboarding_completed'")
        if not cursor.fetchone():
            print("Adding onboarding_completed column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE AFTER business_info")
            print("✓ Added onboarding_completed column")
        else:
            print("✓ onboarding_completed column already exists")
        
        # Check and add service_area_lat column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'service_area_lat'")
        if not cursor.fetchone():
            print("Adding service_area_lat column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN service_area_lat DECIMAL(10, 8) NULL AFTER onboarding_completed")
            print("✓ Added service_area_lat column")
        else:
            print("✓ service_area_lat column already exists")
        
        # Check and add service_area_lng column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'service_area_lng'")
        if not cursor.fetchone():
            print("Adding service_area_lng column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN service_area_lng DECIMAL(11, 8) NULL AFTER service_area_lat")
            print("✓ Added service_area_lng column")
        else:
            print("✓ service_area_lng column already exists")
        
        # Check and add service_radius column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'service_radius'")
        if not cursor.fetchone():
            print("Adding service_radius column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN service_radius INT DEFAULT 25 AFTER service_area_lng")
            print("✓ Added service_radius column")
        else:
            print("✓ service_radius column already exists")
        
        # Check and add portfolio_images column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'portfolio_images'")
        if not cursor.fetchone():
            print("Adding portfolio_images column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN portfolio_images JSON NULL AFTER service_radius")
            print("✓ Added portfolio_images column")
        else:
            print("✓ portfolio_images column already exists")
        
        # Check and add license_number column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'license_number'")
        if not cursor.fetchone():
            print("Adding license_number column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN license_number VARCHAR(100) NULL AFTER portfolio_images")
            print("✓ Added license_number column")
        else:
            print("✓ license_number column already exists")
        
        # Check and add license_state column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'license_state'")
        if not cursor.fetchone():
            print("Adding license_state column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN license_state VARCHAR(2) NULL AFTER license_number")
            print("✓ Added license_state column")
        else:
            print("✓ license_state column already exists")
        
        # Check and add insurance_provider column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'insurance_provider'")
        if not cursor.fetchone():
            print("Adding insurance_provider column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN insurance_provider VARCHAR(255) NULL AFTER license_state")
            print("✓ Added insurance_provider column")
        else:
            print("✓ insurance_provider column already exists")
        
        # Check and add insurance_policy column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'insurance_policy'")
        if not cursor.fetchone():
            print("Adding insurance_policy column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN insurance_policy VARCHAR(100) NULL AFTER insurance_provider")
            print("✓ Added insurance_policy column")
        else:
            print("✓ insurance_policy column already exists")
        
        # Check and add profile_completion_score column
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'profile_completion_score'")
        if not cursor.fetchone():
            print("Adding profile_completion_score column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN profile_completion_score INT DEFAULT 0 AFTER insurance_policy")
            print("✓ Added profile_completion_score column")
        else:
            print("✓ profile_completion_score column already exists")
        
        # Check and add bio column if it doesn't exist
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'bio'")
        if not cursor.fetchone():
            print("Adding bio column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN bio TEXT NULL AFTER profile_completion_score")
            print("✓ Added bio column")
        else:
            print("✓ bio column already exists")
        
        # Check and add years_experience column if it doesn't exist
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'years_experience'")
        if not cursor.fetchone():
            print("Adding years_experience column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN years_experience INT DEFAULT 0 AFTER bio")
            print("✓ Added years_experience column")
        else:
            print("✓ years_experience column already exists")
        
        # Check and add portfolio column if it doesn't exist
        cursor.execute("SHOW COLUMNS FROM contractors LIKE 'portfolio'")
        if not cursor.fetchone():
            print("Adding portfolio column...")
            cursor.execute("ALTER TABLE contractors ADD COLUMN portfolio TEXT NULL AFTER years_experience")
            print("✓ Added portfolio column")
        else:
            print("✓ portfolio column already exists")
        
        connection.commit()
        print("\n✅ Contractor onboarding migration completed successfully!")
        
        # Show updated table structure
        print("\nUpdated contractors table structure:")
        cursor.execute("DESCRIBE contractors")
        columns = cursor.fetchall()
        for column in columns:
            print(f"  {column[0]}: {column[1]}")
        
        return True
        
    except Error as e:
        print(f"❌ Error during migration: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("HomePro Contractor Onboarding Migration")
    print("=" * 50)
    
    success = migrate_contractors_table()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("New contractors will now be redirected to the enhanced onboarding flow.")
    else:
        print("\n💥 Migration failed. Please check the error messages above.")