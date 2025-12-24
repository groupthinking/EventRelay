#!/usr/bin/env python3
"""
ENVIRONMENT SETUP SCRIPT
Installs dependencies and configures environment for YouTube video processing tests
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} failed: {e}")
        if e.stdout:
            print(f"   STDOUT: {e.stdout}")
        if e.stderr:
            print(f"   STDERR: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"   ❌ Python {version.major}.{version.minor} detected. Python 3.8+ required.")
        return False
    else:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True

def install_dependencies():
    """Install required dependencies via pyproject extras"""
    print("\n📦 Installing dependencies...")
    # Prefer editable install with extras
    success = run_command("pip install -e .[youtube,ml,postgres]", "Installing project with extras")
    if not success:
        print("   💡 Try running: pip install --upgrade pip")
        print("   💡 Then run: pip install -e .[youtube,ml,postgres]")
        return False
    return True

def create_env_file():
    """Create .env file template"""
    print("\n🔑 Creating environment file...")
    
    env_content = """# YouTube Extension Development Platform Environment Variables
# Copy this file to .env and fill in your API keys

# YouTube Data API v3 Key
# Get from: https://console.developers.google.com/apis/credentials
YOUTUBE_API_KEY=your_youtube_api_key_here

# OpenAI API Key
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Real mode only (prevents simulation)
REAL_MODE_ONLY=true

# Logging level
LOG_LEVEL=INFO

# Processing settings
MAX_PROCESSING_TIME=300
MIN_PROCESSING_TIME=0.5

# Rate limiting (seconds between requests)
RATE_LIMIT_DELAY=1.0
"""
    
    env_file = Path('.env')
    if env_file.exists():
        print("   ⚠️ .env file already exists")
        return True
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("   ✅ .env file created")
        print("   📝 Please edit .env file and add your API keys")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create .env file: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        'batch_test_results',
        'gdrive_results',
        'logs'
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Created {directory}/")
        else:
            print(f"   ⚠️ {directory}/ already exists")

def test_imports():
    """Test if key modules can be imported"""
    print("\n🧪 Testing imports...")
    
    modules = [
        'asyncio',
        'json',
        'logging',
        'pathlib',
        'typing',
        'datetime'
    ]
    
    failed_imports = []
    for module in modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"   ❌ Failed imports: {failed_imports}")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 ENVIRONMENT SETUP")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Python version incompatible. Please upgrade to Python 3.8+")
        return False
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        return False
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed")
        return False
    
    # Create environment file
    create_env_file()
    
    print("\n" + "=" * 50)
    print("✅ ENVIRONMENT SETUP COMPLETED")
    print("=" * 50)
    print("\n📋 Next steps:")
    print("   1. Edit .env file and add your API keys")
    print("   2. Run: python test_environment_setup.py")
    print("   3. Run: python run_comprehensive_test.py --mode quick")
    print("   4. Run: python run_comprehensive_test.py --mode full")
    print("\n🔑 Required API Keys:")
    print("   • YouTube Data API v3: https://console.developers.google.com/apis/credentials")
    print("   • OpenAI API: https://platform.openai.com/api-keys")
    print("\n📚 Documentation:")
    print("   • README.md - Project overview")
    print("   • process_video_with_mcp.py - Main processing logic")
    print("   • test_100_technical_videos.py - Batch testing")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)