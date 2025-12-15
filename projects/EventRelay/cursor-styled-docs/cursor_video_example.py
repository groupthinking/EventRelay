#!/usr/bin/env python3
"""
Cursor Video Generation Example
Shows how to use video generation directly in Cursor workspace
"""

import json
import os
from mcp_video_server import CursorVideoIntegration

def main():
    """
    Example of using video generation in Cursor
    """
    print("🎬 Cursor Video Generation Example")
    print("=" * 50)
    
    # Initialize the video integration
    video_tool = CursorVideoIntegration()
    
    # Example 1: List available models
    print("\n📋 Available Video Models:")
    print("-" * 30)
    models = video_tool.list_available_models()
    for model in models["models"]:
        print(f"  • {model['name']}: {model['description']}")
        print(f"    Max duration: {model['max_duration']} seconds")
    
    # Example 2: Generate a simple video
    print("\n🎥 Generating Sample Video...")
    print("-" * 30)
    
    # You can customize these parameters
    prompt = "A beautiful sunset over mountains with clouds"
    model = "veo3"  # or "cogvideo", "animatediff", "stable-video"
    duration = 5     # seconds
    width = 512      # pixels
    height = 512     # pixels
    
    print(f"Prompt: {prompt}")
    print(f"Model: {model}")
    print(f"Duration: {duration} seconds")
    print(f"Resolution: {width}x{height}")
    
    # Generate the video
    result = video_tool.generate_video_in_cursor(
        prompt=prompt,
        model=model,
        duration=duration,
        width=width,
        height=height
    )
    
    # Display results
    if result["status"] == "success":
        print(f"\n✅ Video Generated Successfully!")
        print(f"📁 File: {result['local_path']}")
        print(f"📊 Size: {result['file_size']} bytes")
        print(f"⏱️ Duration: {result['duration']} seconds")
        print(f"📐 Dimensions: {result['dimensions']}")
        print(f"🕒 Generated at: {result['timestamp']}")
        
        # Get additional file info
        file_info = video_tool.get_video_details(result['local_path'])
        if file_info["status"] == "success":
            print(f"📅 Created: {file_info['created']}")
            print(f"📅 Modified: {file_info['modified']}")
        
        # Instructions for viewing
        print(f"\n🎬 To view your video:")
        print(f"   open {result['local_path']}")
        print(f"   # or use any video player")
        
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        
        if "HUGGING_FACE_TOKEN" not in result.get('error', ''):
            print("\n💡 To fix this:")
            print("   1. Get a Hugging Face token from https://huggingface.co/settings/tokens")
            print("   2. Set environment variable: export HUGGING_FACE_TOKEN='your_token'")
            print("   3. Run this script again")

def generate_custom_video(prompt, model="veo3", duration=5, width=512, height=512):
    """
    Generate a custom video with your specifications
    
    Usage:
        result = generate_custom_video(
            "A cat playing with a ball",
            model="cogvideo",
            duration=10,
            width=768,
            height=432
        )
    """
    video_tool = CursorVideoIntegration()
    
    print(f"🎬 Generating: {prompt}")
    print(f"📊 Settings: {model}, {duration}s, {width}x{height}")
    
    result = video_tool.generate_video_in_cursor(
        prompt=prompt,
        model=model,
        duration=duration,
        width=width,
        height=height
    )
    
    if result["status"] == "success":
        print(f"✅ Success! Video saved to: {result['local_path']}")
        return result
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return None

# Example usage patterns
if __name__ == "__main__":
    # Run the main example
    main()
    
    # Additional examples you can uncomment:
    
    # Example 1: Generate a landscape video
    # result = generate_custom_video(
    #     "A serene mountain landscape with snow-capped peaks",
    #     model="cogvideo",
    #     duration=8,
    #     width=768,
    #     height=432
    # )
    
    # Example 2: Generate an animated video
    # result = generate_custom_video(
    #     "A cartoon character dancing in a colorful world",
    #     model="animatediff",
    #     duration=6,
    #     width=512,
    #     height=512
    # )
    
    # Example 3: Generate a short clip
    # result = generate_custom_video(
    #     "Ocean waves crashing on a sandy beach",
    #     model="stable-video",
    #     duration=3,
    #     width=640,
    #     height=480
    # ) 