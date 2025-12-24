#!/usr/bin/env python3
"""
SETUP SCRIPT FOR LLAMA BACKGROUND AGENT
Installs dependencies and configures the Llama 3.1 8B agent

This script:
1. Installs required Python packages
2. Downloads the Llama model
3. Sets up configuration
4. Tests the installation
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

# Colors for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message: str, color: str = Colors.BLUE):
    """Print a status message with color"""
    print(f"{color}{message}{Colors.END}")

def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_header(message: str):
    """Print a header message"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}{Colors.END}\n")

def run_command(command: List[str], description: str) -> bool:
    """Run a shell command and return success status"""
    try:
        print_status(f"Running: {description}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print_success(f"Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed: {description}")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print_error(f"Command not found: {command[0]}")
        return False

def install_python_packages() -> bool:
    """Install required Python packages"""
    print_header("Installing Python Dependencies")
    
    packages = [
        "llama-cpp-python[server]>=0.2.0",
        "sentence-transformers>=2.2.0",
        "numpy>=1.24.0",
        "huggingface_hub>=0.16.0",
        "mcp>=1.0.0"
    ]
    
    success = True
    for package in packages:
        if not run_command([sys.executable, "-m", "pip", "install", package], f"Installing {package}"):
            success = False
    
    return success

def create_directories() -> bool:
    """Create necessary directories"""
    print_header("Creating Directory Structure")
    
    directories = [
        "models/llama-3.1-8b-instruct",
        "workflow_results",
        "workflow_results/videos",
        "workflow_results/failures",
        "workflow_results/learning_logs",
        "workflow_results/implementation_plans",
        "logs",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print_success(f"Created directory: {directory}")
    
    return True

def download_llama_model() -> bool:
    """Download the Llama 3.1 8B model"""
    print_header("Downloading Llama 3.1 8B Model")
    
    try:
        from huggingface_hub import hf_hub_download
        
        model_dir = Path("models/llama-3.1-8b-instruct")
        model_file = model_dir / "model.gguf"
        
        if model_file.exists():
            print_success(f"Model already exists: {model_file}")
            return True
        
        print_status("Downloading model (this may take a while)...")
        downloaded_file = hf_hub_download(
            repo_id="TheBloke/Llama-3.1-8B-Instruct-GGUF",
            filename="llama-3.1-8b-instruct.Q4_K_M.gguf",
            local_dir=model_dir,
            local_dir_use_symlinks=False
        )
        
        print_success(f"Model downloaded successfully: {downloaded_file}")
        return True
        
    except ImportError:
        print_error("huggingface_hub not available. Please install it first.")
        return False
    except Exception as e:
        print_error(f"Failed to download model: {e}")
        return False

def create_environment_file() -> bool:
    """Create .env file with required environment variables"""
    print_header("Creating Environment Configuration")
    
    env_file = Path(".env")
    if env_file.exists():
        print_warning(".env file already exists, skipping creation")
        return True
    
    env_content = """# Llama Background Agent Configuration
USE_LLAMA=true
BATCH_SIZE=10
SLEEP_INTERVAL=60

# API Keys (fill these in)
YOUTUBE_API_KEY=your_youtube_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Model Configuration
LLAMA_MODEL_PATH=models/llama-3.1-8b-instruct/model.gguf

# Processing Configuration
REAL_MODE_ONLY=false
USE_PROXY_ONLY=false
"""
    
    try:
        env_file.write_text(env_content)
        print_success("Created .env file")
        print_warning("Please update .env with your actual API keys")
        return True
    except Exception as e:
        print_error(f"Failed to create .env file: {e}")
        return False

def test_installation() -> bool:
    """Test the Llama agent installation"""
    print_header("Testing Installation")
    
    try:
        # Test imports
        print_status("Testing imports...")
        from agents.llama_background_agent import LlamaBackgroundAgent
        print_success("Llama agent imports successfully")
        
        # Test model loading (if model exists)
        model_path = Path("models/llama-3.1-8b-instruct/model.gguf")
        if model_path.exists():
            print_status("Testing model loading...")
            # Note: We won't actually load the model here as it's resource-intensive
            print_success("Model file exists and is accessible")
        else:
            print_warning("Model file not found, skipping model test")
        
        return True
        
    except ImportError as e:
        print_error(f"Import test failed: {e}")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False

def create_startup_script() -> bool:
    """Create a startup script for the enhanced runner"""
    print_header("Creating Startup Scripts")
    
    # Create enhanced runner startup script
    startup_script = """#!/bin/bash
# Enhanced Continuous Runner Startup Script

echo "🚀 Starting Llama Background Agent Enhanced Runner..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set environment variables
export USE_LLAMA=true
export BATCH_SIZE=10
export SLEEP_INTERVAL=60

# Start the enhanced runner
python3 scripts/enhanced_continuous_runner.py
"""
    
    try:
        startup_file = Path("start_enhanced_runner.sh")
        startup_file.write_text(startup_script)
        startup_file.chmod(0o755)  # Make executable
        print_success("Created startup script: start_enhanced_runner.sh")
        
        # Create MCP server startup script
        mcp_script = """#!/bin/bash
# Llama Agent MCP Server Startup Script

echo "🔮 Starting Llama Agent MCP Server..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start the MCP server
python3 mcp_servers/llama_agent_mcp_server.py
"""
        
        mcp_file = Path("start_llama_mcp_server.sh")
        mcp_file.write_text(mcp_script)
        mcp_file.chmod(0o755)
        print_success("Created MCP server script: start_llama_mcp_server.sh")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to create startup scripts: {e}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print_header("Setup Complete! Next Steps")
    
    print(f"{Colors.GREEN}🎉 Llama Background Agent has been installed successfully!{Colors.END}")
    print()
    print(f"{Colors.BOLD}Next steps:{Colors.END}")
    print("1. Update .env file with your API keys")
    print("2. Test the installation: python3 scripts/setup_llama_agent.py --test")
    print("3. Start the enhanced runner: ./start_enhanced_runner.sh")
    print("4. Start the MCP server: ./start_llama_mcp_server.sh")
    print()
    print(f"{Colors.BOLD}Usage examples:{Colors.END}")
    print("• Process videos: python3 scripts/enhanced_continuous_runner.py")
    print("• MCP integration: python3 mcp_servers/llama_agent_mcp_server.py")
    print("• Test agent: python3 agents/llama_background_agent.py")
    print()
    print(f"{Colors.BOLD}Configuration:{Colors.END}")
    print("• Edit config/llama_agent_config.json for advanced settings")
    print("• Modify .env for environment-specific configuration")
    print("• Check logs/llama_agent.log for runtime information")

async def main():
    """Main setup function"""
    print_header("Llama Background Agent Setup")
    
    print(f"{Colors.BLUE}This script will install and configure the Llama 3.1 8B Background Agent{Colors.END}")
    print(f"{Colors.BLUE}for enhanced video processing with MCP integration.{Colors.END}")
    print()
    
    # Check if running in test mode
    if "--test" in sys.argv:
        print_status("Running in test mode...")
        return test_installation()
    
    # Run setup steps
    steps = [
        ("Installing Python packages", install_python_packages),
        ("Creating directories", create_directories),
        ("Downloading Llama model", download_llama_model),
        ("Creating environment file", create_environment_file),
        ("Creating startup scripts", create_startup_script),
        ("Testing installation", test_installation)
    ]
    
    success = True
    for step_name, step_func in steps:
        print(f"\n{Colors.BOLD}Step: {step_name}{Colors.END}")
        if not step_func():
            success = False
            print_error(f"Setup step failed: {step_name}")
            break
    
    if success:
        print_next_steps()
        return True
    else:
        print_error("Setup failed. Please check the errors above and try again.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
