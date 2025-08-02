#!/usr/bin/env python3
"""
Test script to demonstrate filename-based mock transcription
"""

from audio_processor import AudioProcessor

def test_filename_context():
    """Test how different filenames generate different mock transcriptions"""
    
    processor = AudioProcessor()
    
    # Test different filename patterns
    test_files = [
        "kitchen_renovation_project.mp3",
        "bathroom_repair_needed.wav",
        "plumbing_emergency_leak.m4a",
        "electrical_outlet_installation.mp3",
        "roofing_storm_damage.wav",
        "flooring_hardwood_install.mp3",
        "painting_interior_walls.wav",
        "hvac_heating_repair.mp3",
        "generic_audio_file.mp3",
        "no_keywords_here.wav"
    ]
    
    print("🎯 Testing Filename-Based Mock Transcription")
    print("=" * 60)
    
    for filename in test_files:
        print(f"\n📁 File: {filename}")
        mock_transcript = processor._mock_transcription(filename)
        print(f"📝 Generated transcript: {mock_transcript}")
        print("-" * 40)

if __name__ == "__main__":
    test_filename_context()