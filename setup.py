#!/usr/bin/env python3
"""
ExoStack Setup Script
This script helps set up the ExoStack environment and dependencies.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {cmd}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("🚀 ExoStack Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Install Python dependencies
    print("\n📦 Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Setup UI dependencies
    ui_dir = Path("exo_ui")
    if ui_dir.exists():
        print("\n🎨 Setting up React UI...")
        if not run_command("npm install", cwd=ui_dir):
            print("❌ Failed to install UI dependencies")
            print("Make sure Node.js and npm are installed")
        else:
            print("✓ UI dependencies installed")
    
    # Create necessary directories
    print("\n📁 Creating directories...")
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    print("✓ Directories created")
    
    # Check .env file
    print("\n⚙️ Configuration...")
    if Path(".env").exists():
        print("✓ .env file found")
    else:
        print("❌ .env file not found")
        print("Please create a .env file based on .env.example")
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Review and update .env configuration")
    print("2. Start the hub: python cli.py hub start")
    print("3. Start an agent: python cli.py agent start")
    print("4. Start the UI: cd exo_ui && npm run dev")
    print("5. Run tests: python cli.py system test")
    print("6. Check system info: python cli.py system info")

if __name__ == "__main__":
    main()
