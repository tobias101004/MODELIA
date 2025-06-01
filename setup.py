"""
Setup script for the 211 File Generator application
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess

def print_header(text):
    """Print formatted header text"""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "="))
    print("=" * 80)

def print_step(text):
    """Print step information"""
    print(f"\n>> {text}")

def create_directory(path):
    """Create directory if it doesn't exist"""
    if not Path(path).exists():
        print(f"Creating directory: {path}")
        Path(path).mkdir(parents=True)
    else:
        print(f"Directory already exists: {path}")

def run_command(command, description=None):
    """Run a shell command and display output"""
    if description:
        print_step(description)
    
    print(f"Running: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def install_packages():
    """Install required Python packages"""
    print_step("Installing required Python packages")
    
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
        "pdfminer.six",
        "httpx",
        "jinja2",
        "unidecode"
    ]
    
    return run_command([sys.executable, "-m", "pip", "install", "--upgrade"] + packages,
                      "Installing packages")

def setup_directories():
    """Set up necessary directories"""
    print_step("Setting up directories")
    
    directories = ["static", "templates", "temp"]
    for directory in directories:
        create_directory(directory)
    
    return True

def create_html_template():
    """Create HTML template file"""
    print_step("Creating HTML template file")
    
    # Copy index.html to templates directory
    if Path("index.html").exists():
        shutil.copy("index.html", "templates/index.html")
        print("Copied index.html to templates directory")
    else:
        print("Warning: index.html not found. Please create it manually.")
    
    return True

def copy_sample_pdf():
    """Copy sample PDF if it exists"""
    print_step("Checking for sample PDF")
    
    sample_path = Path("temp.pdf")
    if sample_path.exists():
        dest_path = Path("temp") / "sample.pdf"
        shutil.copy(sample_path, dest_path)
        print(f"Copied sample PDF to: {dest_path}")
        return True
    else:
        print("No sample PDF found at temp.pdf")
        return False

def run_tests():
    """Run tests to verify format"""
    print_step("Running format verification tests")
    
    return run_command([sys.executable, "test_exact_format.py"],
                     "Testing exact 211 file format")

def main():
    """Main setup function"""
    print_header("211 File Generator - Setup")
    
    # Step 1: Install required packages
    if not install_packages():
        print("Failed to install required packages. Installation aborted.")
        return
    
    # Step 2: Set up directories
    if not setup_directories():
        print("Failed to set up directories. Installation aborted.")
        return
    
    # Step 3: Create HTML template
    if not create_html_template():
        print("Failed to create HTML template. Installation aborted.")
        return
    
    # Step 4: Copy sample PDF if available
    copy_sample_pdf()
    
    # Step 5: Run tests
    if not run_tests():
        print("Warning: Format verification tests failed. The application may not generate files in the exact format required.")
    
    print_header("Setup Completed Successfully")
    print("\nYou can now start the application with:")
    print("  uvicorn final_app:app --reload")
    
    # Ask if user wants to start the application now
    response = input("\nDo you want to start the application now? (y/n): ")
    if response.lower() in ["y", "yes"]:
        print("\nStarting the application...")
        os.system("uvicorn final_app:app --reload")

if __name__ == "__main__":
    main()
