#!/usr/bin/env python3
"""
Startup script for MODEL.IA application
This script checks dependencies and starts the server
"""

import sys
import subprocess
import os
from pathlib import Path

def print_header(text):
    """Print formatted header text"""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60, "="))
    print("=" * 60)

def print_step(text):
    """Print step information"""
    print(f"\n>> {text}")

def check_python_version():
    """Check if Python version is compatible"""
    print_step("Checking Python version")
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_and_install_packages():
    """Check and install required packages"""
    print_step("Checking required packages")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "python-multipart",
        "pdfminer.six",
        "httpx",
        "jinja2",
        "unidecode"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (missing)")
    
    if missing_packages:
        print_step("Installing missing packages")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade"
            ] + missing_packages)
            print("✓ All packages installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install packages: {e}")
            return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print_step("Creating directories")
    
    directories = ["temp", "static", "templates"]
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True)
            print(f"✓ Created {directory}/")
        else:
            print(f"✓ {directory}/ exists")
    
    return True

def check_template_files():
    """Check if template files exist"""
    print_step("Checking template files")
    
    required_templates = [
        "index.html",
        "cuenta.html",
        "contacto.html",
        "modelo-211.html",
        "modelo-600.html",
        "modelo-211-edit.html",
        "modelo-211-exito.html",
        "modelo-600-resultados.html"
    ]
    
    missing_templates = []
    templates_dir = Path("templates")
    
    for template in required_templates:
        template_path = templates_dir / template
        if template_path.exists():
            print(f"✓ {template}")
        else:
            missing_templates.append(template)
            print(f"✗ {template} (missing)")
    
    if missing_templates:
        print(f"\nWARNING: Missing template files: {', '.join(missing_templates)}")
        print("The application may not work correctly without these files.")
        return False
    
    return True

def check_python_files():
    """Check if required Python files exist"""
    print_step("Checking Python files")
    
    required_files = [
        "main.py",
        "enhanced_extractors.py",
        "template_formatter.py",
        "country_utils.py",
        "model_600_extractor.py"
    ]
    
    missing_files = []
    
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            missing_files.append(file)
            print(f"✗ {file} (missing)")
    
    if missing_files:
        print(f"\nERROR: Missing required files: {', '.join(missing_files)}")
        return False
    
    return True

def start_server():
    """Start the FastAPI server"""
    print_step("Starting the server")
    
    try:
        print("Starting MODEL.IA on http://127.0.0.1:8000")
        print("Press Ctrl+C to stop the server")
        print("\nServer logs:")
        print("-" * 50)
        
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
        
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nERROR: Failed to start server: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    print_header("MODEL.IA Startup")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check and install packages
    if not check_and_install_packages():
        print("\nERROR: Package installation failed")
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        print("\nERROR: Directory creation failed")
        sys.exit(1)
    
    # Check Python files
    if not check_python_files():
        print("\nERROR: Missing required Python files")
        sys.exit(1)
    
    # Check template files
    template_check = check_template_files()
    if not template_check:
        response = input("\nSome template files are missing. Continue anyway? (y/n): ")
        if response.lower() not in ['y', 'yes']:
            sys.exit(1)
    
    print_header("All checks passed! Starting server...")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()
