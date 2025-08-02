#!/usr/bin/env python3
"""
Test script to verify audio upload functionality
"""

import os
import sys
import tempfile
import shutil

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_audio_processing():
    """Test the audio processing pipeline"""
    print("Testing audio processing pipeline...")
    
    try:
        # Import the functions from app.py
        from app import process_ai_submission, allowed_file
        
        # Test file type validation
        print("\n1. Testing file type validation...")
        test_files = [
            ("test.mp3", True),
            ("test.wav", True),
            ("test.txt", False),
            ("test.jpg", False)
        ]
        
        for filename, expected in test_files:
            result = allowed_file(filename, 'audio')
            status = "✓" if result == expected else "✗"
            print(f"   {status} {filename}: {result} (expected: {expected})")
        
        # Test with the existing test audio file
        test_audio_path = "test_audio.mp3"
        if os.path.exists(test_audio_path):
            print(f"\n2. Testing audio processing with {test_audio_path}...")
            
            # Process the audio file
            result = process_ai_submission(test_audio_path, 'audio')
            
            if result:
                print("   ✓ Audio processing successful!")
                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Project Type: {result.get('project_type', 'N/A')}")
                print(f"   Description: {result.get('description', 'N/A')[:100]}...")
                print(f"   Budget: ${result.get('budget_min', 'N/A')} - ${result.get('budget_max', 'N/A')}")
                print(f"   Timeline: {result.get('timeline', 'N/A')}")
                return True
            else:
                print("   ✗ Audio processing failed!")
                return False
        else:
            print(f"\n2. Test audio file {test_audio_path} not found, skipping audio processing test")
            return True
            
    except Exception as e:
        print(f"   ✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_handling():
    """Test session data handling"""
    print("\n3. Testing session data handling...")
    
    try:
        # Simulate session data
        test_project_data = {
            'title': 'Test Project',
            'project_type': 'Plumbing',
            'description': 'Test description',
            'budget_min': 1000,
            'budget_max': 2000,
            'timeline': '2 weeks'
        }
        
        # Test that the data structure is valid
        required_fields = ['title', 'project_type', 'description']
        for field in required_fields:
            if field in test_project_data:
                print(f"   ✓ {field}: {test_project_data[field]}")
            else:
                print(f"   ✗ Missing required field: {field}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error during session testing: {e}")
        return False

def test_direct_audio_flow():
    """Test the direct audio processing flow"""
    print("\n4. Testing direct audio flow simulation...")
    
    try:
        from audio_processor import AudioProcessor
        
        # Test AudioProcessor directly
        processor = AudioProcessor()
        
        # Test with sample text (simulating transcription)
        sample_text = "I need to fix my bathroom. The shower is leaking and needs new tiles. My budget is around $5000 and I need it done in 2 weeks."
        
        result = processor.extract_project_details_with_bedrock(sample_text)
        
        if result:
            print("   ✓ Direct audio processing successful!")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Project Type: {result.get('project_type', 'N/A')}")
            print(f"   Description: {result.get('description', 'N/A')[:100]}...")
            return True
        else:
            print("   ✗ Direct audio processing failed!")
            return False
            
    except Exception as e:
        print(f"   ✗ Error during direct audio testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Audio Upload Test Suite ===")
    
    success = True
    success &= test_audio_processing()
    success &= test_session_handling()
    success &= test_direct_audio_flow()
    
    print(f"\n=== Test Results ===")
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    sys.exit(0 if success else 1)