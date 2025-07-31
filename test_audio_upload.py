import requests
import io

# Test the audio upload functionality
def test_audio_upload():
    base_url = "http://127.0.0.1:8000"
    
    print("=== TESTING AUDIO UPLOAD ===")
    
    # First, test accessing the submit page
    try:
        response = requests.get(f"{base_url}/submit_project")
        print(f"Submit page status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error accessing submit page: {response.text}")
            return
    except Exception as e:
        print(f"Error accessing submit page: {e}")
        return
    
    # Create a mock MP3 file in memory
    audio_content = b"ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    audio_file = io.BytesIO(audio_content)
    
    # Test audio upload
    try:
        files = {
            'file': ('test_audio.mp3', audio_file, 'audio/mpeg')
        }
        data = {
            'submission_method': 'audio'
        }
        
        print("Uploading audio file...")
        response = requests.post(f"{base_url}/submit_project", files=files, data=data)
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response content: {response.text[:500]}...")
        
        if "Review Project" in response.text or "review_project" in response.text:
            print("✓ Audio upload succeeded - redirected to review page")
        elif "successfully" in response.text.lower():
            print("✓ Audio upload succeeded")
        else:
            print("✗ Audio upload failed")
            
    except Exception as e:
        print(f"Error during audio upload: {e}")

if __name__ == "__main__":
    test_audio_upload()