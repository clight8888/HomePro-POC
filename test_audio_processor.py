#!/usr/bin/env python3
"""
Test script for AudioProcessor functionality
"""

import os
import sys

def test_audio_processor():
    """Test the AudioProcessor class"""
    try:
        print("Testing AudioProcessor import...")
        from audio_processor import AudioProcessor
        print("✓ AudioProcessor imported successfully")
        
        print("\nTesting AudioProcessor initialization...")
        processor = AudioProcessor()
        print("✓ AudioProcessor initialized successfully")
        
        print(f"✓ AWS available: {processor.aws_available}")
        print(f"✓ S3 client: {processor.s3_client is not None}")
        print(f"✓ Transcribe client: {processor.transcribe_client is not None}")
        print(f"✓ Bedrock client: {processor.bedrock_client is not None}")
        
        # Test text analysis
        print("\nTesting text analysis with Bedrock...")
        test_text = "I need to renovate my kitchen. The cabinets are old and the countertops need replacing. My budget is around $15,000 and I'd like it done within 2 months."
        
        result = processor.extract_project_details_with_bedrock(test_text)
        print(f"✓ Text analysis result: {result}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== AudioProcessor Test ===")
    success = test_audio_processor()
    
    if success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)