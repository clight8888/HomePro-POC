#!/usr/bin/env python3
"""
Script to replace MySQL-style SQL placeholders (%s) with SQLite-style placeholders (?)
in app.py file.
"""

import re

def fix_sql_placeholders(file_path):
    """Replace all %s with ? in SQL queries"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace %s with ? in SQL queries
    # This regex looks for %s that are likely SQL placeholders
    content = re.sub(r'%s', '?', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed SQL placeholders in {file_path}")

if __name__ == '__main__':
    fix_sql_placeholders('app.py')
    print("All MySQL-style placeholders (%s) have been replaced with SQLite-style placeholders (?)")