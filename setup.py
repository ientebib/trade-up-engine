#!/usr/bin/env python3
"""
Setup script for Trade-Up Engine
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e}")
        return False


def check_python_version():
    """Ensure Python 3.8+ is being used"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version}")


def setup_virtual_environment():
    """Create and activate virtual environment"""
    if os.path.exists("venv"):
        print("⚠️  Virtual environment already exists")
        response = input("Do you want to recreate it? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree("venv")
        else:
            return True
    
    return run_command(
        f"{sys.executable} -m venv venv",
        "Creating virtual environment"
    )


def install_dependencies():
    """Install Python dependencies"""
    pip_cmd = "venv/bin/pip" if os.name != 'nt' else "venv\\Scripts\\pip"
    
    # Upgrade pip first
    run_command(
        f"{pip_cmd} install --upgrade pip",
        "Upgrading pip"
    )
    
    # Install requirements
    return run_command(
        f"{pip_cmd} install -r requirements.txt",
        "Installing dependencies"
    )


def setup_environment_file():
    """Create .env file from template"""
    if os.path.exists(".env"):
        print("⚠️  .env file already exists")
        return True
    
    if not os.path.exists(".env.example"):
        print("❌ .env.example not found")
        return False
    
    shutil.copy(".env.example", ".env")
    print("✅ Created .env file from template")
    print("\n⚠️  IMPORTANT: Edit .env file with your Redshift credentials")
    return True


def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "tests/unit",
        "tests/integration",
        "tests/debug",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created necessary directories")
    return True


def run_tests():
    """Run basic tests to verify setup"""
    python_cmd = "venv/bin/python" if os.name != 'nt' else "venv\\Scripts\\python"
    
    # Test imports
    test_cmd = f'{python_cmd} -c "import fastapi; import pandas; import numpy; print(\'✅ Core imports successful\')"'
    return run_command(test_cmd, "Testing core imports")


def main():
    """Main setup process"""
    print("""
╔══════════════════════════════════════════════════════════╗
║           Trade-Up Engine Setup Script                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    steps = [
        (check_python_version, None),
        (setup_virtual_environment, None),
        (install_dependencies, None),
        (setup_environment_file, None),
        (create_directories, None),
        (run_tests, None)
    ]
    
    for step_func, args in steps:
        if args:
            result = step_func(args)
        else:
            result = step_func()
        
        if result is False:
            print("\n❌ Setup failed. Please fix the errors and try again.")
            sys.exit(1)
    
    print("""
╔══════════════════════════════════════════════════════════╗
║                  Setup Complete! 🎉                       ║
╚══════════════════════════════════════════════════════════╝

Next steps:
1. Edit .env file with your Redshift credentials
2. Activate virtual environment:
   - Linux/Mac: source venv/bin/activate
   - Windows: venv\\Scripts\\activate
3. Run the application:
   - ./run_local.sh
   - Or: python -m uvicorn app.main:app --reload

Visit http://localhost:8000 to access the application.
    """)


if __name__ == "__main__":
    main()