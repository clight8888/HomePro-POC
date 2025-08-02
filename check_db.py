import sqlite3

conn = sqlite3.connect('homepro.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"- {table[0]}")

# Check if projects table exists and has data
try:
    cursor.execute("SELECT COUNT(*) FROM projects")
    count = cursor.fetchone()[0]
    print(f"\nProjects table has {count} records")
    
    # Check for projects with audio
    cursor.execute("SELECT id, title, original_file_path FROM projects WHERE original_file_path IS NOT NULL LIMIT 3")
    projects = cursor.fetchall()
    print("\nProjects with audio files:")
    for project in projects:
        print(f"ID: {project[0]}, Title: {project[1]}, Path: {project[2]}")
        
except Exception as e:
    print(f"Error checking projects: {e}")

conn.close()