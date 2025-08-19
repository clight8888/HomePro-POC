import sqlite3

conn = sqlite3.connect('homepro.db')
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check all projects
cursor.execute('SELECT id, title, homeowner_id FROM projects')
projects = cursor.fetchall()
print('\nAll projects:')
for project in projects:
    print(f'  ID: {project[0]}, Title: {project[1]}, Homeowner: {project[2]}')

# Check users table structure
cursor.execute('PRAGMA table_info(users)')
user_columns = cursor.fetchall()
print('\nUsers table columns:')
for col in user_columns:
    print(f'  {col[1]} ({col[2]})')

# Check users data
cursor.execute('SELECT * FROM users LIMIT 5')
users = cursor.fetchall()
print('\nUsers data:')
for user in users:
    print(f'  {user}')

conn.close()