#!/usr/bin/env python3
"""
Test script to directly test the audio upload flow
"""

import requests
import os

def test_direct_upload():
    """Test direct audio upload to the running server"""
    base_url = "http://127.0.0.1:8000"
    
    print("=== Testing Direct Audio Upload ===")
    
    # Check if test audio file exists
    test_audio_path = "test_audio.mp3"
    if not os.path.exists(test_audio_path):
        print(f"Test audio file {test_audio_path} not found!")
        return False
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        # First, get the submit page to establish session
        print("1. Getting submit page...")
        response = session.get(f"{base_url}/submit_project")
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return False
        
        # Upload the audio file
        print("2. Uploading audio file...")
        with open(test_audio_path, 'rb') as audio_file:
            files = {
                'file': ('test_audio.mp3', audio_file, 'audio/mpeg')
            }
            data = {
                'submission_method': 'audio'
            }
            
            response = session.post(f"{base_url}/submit_project", files=files, data=data)
            print(f"   Status: {response.status_code}")
            print(f"   URL: {response.url}")
            
            # Check if we were redirected to review page
            if "review_project" in response.url:
                print("   ✓ Successfully redirected to review page!")
                
                # Try to access the review page
                print("3. Accessing review page...")
                review_response = session.get(f"{base_url}/review_project")
                print(f"   Status: {review_response.status_code}")
                
                if "No project data found" in review_response.text:
                    print("   ✗ Error: No project data found on review page!")
                    return False
                elif review_response.status_code == 200:
                    print("   ✓ Review page loaded successfully!")
                    return True
                else:
                    print(f"   ✗ Review page error: {review_response.status_code}")
                    return False
            else:
                print(f"   ✗ Not redirected to review page. Response content:")
                print(f"   {response.text[:500]}...")
                return False
                
    except Exception as e:
        print(f"   ✗ Error during upload: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_upload()
    if success:
        print("\n✓ Direct upload test passed!")
    else:
        print("\n✗ Direct upload test failed!")