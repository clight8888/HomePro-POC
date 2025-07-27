#!/usr/bin/env python3
"""
AWS Elastic Beanstalk entry point for HomePro application
"""
from app import app, db
import os

# AWS Elastic Beanstalk looks for an 'application' variable
application = app

# Initialize database tables only if not in production startup
# This prevents timeout issues during EB deployment
def init_db():
    """Initialize database tables safely"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        # Don't fail startup if database isn't ready yet

# Only run database initialization in specific contexts
if __name__ == "__main__":
    # Running locally
    init_db()
    application.run(debug=False)
elif os.environ.get('FLASK_ENV') != 'production':
    # Development environment
    init_db()