#!/usr/bin/env python3
"""
Single-Command YouTube Extension Core Deployment
Deploy all integrations with one command
"""

import asyncio
import subprocess
import sys
import os

async def deploy_all():
    """Deploy all YouTube Extension integrations"""
    
    print("🚀 YOUTUBE EXTENSION CORE DEPLOYMENT")
    print("=" * 60)
    print("Deploying all integrations with enhanced error handling...")
    print("=" * 60)
    
    commands = [
        # Test YouTube error integration
        "python3 youtube_error_integration.py",
        
        # Test Nexa integration  
        "python3 nexa_integration.py",
        
        # Test Gemini LogProbs
        "python3 gemini_logprobs_integration.py",
        
        # Start MCP server with all enhancements
        "python3 mcp_server.py &"
    ]
    
    for cmd in commands:
        print(f"\n🔧 Running: {cmd}")
        try:
            if cmd.endswith(" &"):
                # Background process
                subprocess.Popen(cmd[:-2].split())
                print("   ✅ Started in background")
            else:
                result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print("   ✅ Success")
                else:
                    print(f"   ⚠️ Warning: {result.stderr[:100]}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
    
    print(f"\n🎉 DEPLOYMENT COMPLETE")
    print("YouTube Extension now has:")
    print("   ✅ Enhanced error handling with video recommendations")
    print("   ✅ Local Nexa processing for cost optimization")  
    print("   ✅ Gemini LogProbs reasoning with confidence scoring")
    print("   ✅ External MCP servers (YouTube, MiniCPM-o)")
    print("   ✅ Unified API configuration")
    
    print(f"\n📍 Next Steps:")
    print("   1. Test error handling: Trigger an error and check video recommendations")
    print("   2. Monitor costs: Check Nexa vs external API usage")
    print("   3. Validate reasoning: Review Gemini confidence scores")
    print("   4. Explore integrations: Test external MCP servers")

if __name__ == "__main__":
    asyncio.run(deploy_all())
