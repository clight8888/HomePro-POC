#!/usr/bin/env python3
"""
Test script to demonstrate the comprehensive logging system
that shows AWS credential usage and fallback scenarios.
"""

import os
import sys
import logging

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to show all levels
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_logging_system():
    """Test the logging system with different file types"""
    print("=" * 80)
    print("🧪 TESTING COMPREHENSIVE LOGGING SYSTEM")
    print("=" * 80)
    
    from app import process_ai_submission
    
    # Test cases with different file types and names
    test_cases = [
        {
            'file_path': 'kitchen_renovation_project.mp3',
            'file_type': 'audio',
            'description': 'Kitchen renovation audio file'
        },
        {
            'file_path': 'bathroom_repair_emergency.wav',
            'file_type': 'audio', 
            'description': 'Bathroom emergency audio file'
        },
        {
            'file_path': 'plumbing_leak_urgent.mp4',
            'file_type': 'video',
            'description': 'Plumbing emergency video file'
        },
        {
            'file_path': None,
            'file_type': None,
            'text_content': 'I need help with electrical work in my living room. The outlets are not working and I need a professional electrician to fix them. My budget is around $500-800.',
            'description': 'Text submission for electrical work'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST CASE {i}: {test_case['description']}")
        print(f"{'='*60}")
        
        try:
            if test_case.get('text_content'):
                # Test text submission
                result = process_ai_submission(
                    file_path=None,
                    file_type=None,
                    text_content=test_case['text_content']
                )
            else:
                # Test file submission
                result = process_ai_submission(
                    file_path=test_case['file_path'],
                    file_type=test_case['file_type']
                )
            
            if result:
                print(f"✅ Processing successful!")
                print(f"📋 Project Title: {result.get('title', 'N/A')}")
                print(f"🏗️ Project Type: {result.get('project_type', 'N/A')}")
                print(f"🔧 Extraction Method: {result.get('extraction_method', 'N/A')}")
            else:
                print("❌ Processing failed - no result returned")
                
        except Exception as e:
            print(f"❌ Test case failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("🏁 LOGGING SYSTEM TEST COMPLETED")
    print("=" * 80)
    print("\n📊 LOGGING LEGEND:")
    print("☁️  = AWS services available and being used")
    print("🚫 = AWS services not available, using fallback")
    print("🎭 = Mock transcription (filename-based)")
    print("🤖 = AWS Bedrock Claude extraction")
    print("🔧 = Fallback text analysis")
    print("🎵 = Audio file processing")
    print("📹 = Video file processing")
    print("📝 = Text submission processing")
    print("✅ = Successful completion")
    print("❌ = Error occurred")
    print("🔄 = Fallback scenario")

if __name__ == "__main__":
    test_logging_system()