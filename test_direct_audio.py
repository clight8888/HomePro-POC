#!/usr/bin/env python3

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the function from app.py
from app import process_ai_submission

def test_direct_audio_processing():
    """Test the process_ai_submission function directly"""
    print("=== DIRECT AUDIO PROCESSING TEST ===")
    
    # Create a dummy audio file path (doesn't need to exist for mock processing)
    test_file_path = "test_audio.mp3"
    
    print(f"Testing with file_path: {test_file_path}")
    print(f"Testing with file_type: audio")
    
    # Call the function directly
    result = process_ai_submission(test_file_path, 'audio')
    
    print(f"Result: {result}")
    
    if result:
        print("✓ Audio processing succeeded")
        print(f"Title: {result.get('title')}")
        print(f"Project Type: {result.get('project_type')}")
        print(f"Description: {result.get('description')}")
        print(f"Budget: ${result.get('budget_min')} - ${result.get('budget_max')}")
        print(f"Timeline: {result.get('timeline')}")
    else:
        print("✗ Audio processing failed")

if __name__ == "__main__":
    test_direct_audio_processing()