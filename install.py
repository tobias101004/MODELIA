"""
Installation script for the 211 File Generator application
"""

import os
import sys
from pathlib import Path
import shutil
import subprocess
import platform

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
        "uvicorn",
        "python-multipart",
        "pdfminer.six",
        "httpx",
        "jinja2",
        "pydantic",
        "unidecode"
    ]
    
    return run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"] + packages,
                      "Upgrading pip and installing packages")

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
    
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generador de Archivos 211 para Hacienda</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding-top: 2rem;
            padding-bottom: 3rem;
            background-color: #f8f9fa;
            color: #333;
        }
        .container {
            max-width: 1140px;
        }
        .card {
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            border: none;
            overflow: hidden;
        }
        .card-header {
            background-color: #e7f1ff;
            border-bottom: 1px solid #d0e2ff;
            padding: 1rem 1.5rem;
        }
        .card-body {
            padding: 1.5rem;
        }
        #loadingSpinner {
            display: none;
            padding: 2rem 0;
            text-align: center;
        }
        .success-icon {
            display: block;
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #198754;
        }
        .btn-primary {
            background-color: #0d6efd;
            border-color: #0d6efd;
            padding: 0.6rem 1.5rem;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }
        .btn-success {
            background-color: #198754;
            border-color: #198754;
            padding: 0.6rem 1.5rem;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }
        .btn-outline-secondary {
            color: #6c757d;
            border-color: #6c757d;
            padding: 0.6rem 1.5rem;
        }
        #downloadSection {
            display: none;
        }
        #errorMessage {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">Generador de Archivos 211 para Hacienda</h1>
        <p class="text-center mb-4">
            Esta aplicación procesa escrituras de compraventa inmobiliaria y genera el archivo plano .211 
            con el formato requerido por la Agencia Tributaria.
        </p>

        <div class="card">
            <div class="card-header">
                <h3>Subir escritura de compraventa (PDF)</h3>
            </div>
            <div class="card-body">
                <form id="uploadForm" action="/proceso_completo" method="post" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="pdfFile" class="form-label">Seleccione el archivo PDF con la escritura:</label>
                        <input type="file" class="form-control" id="pdfFile" name="pdf_file" accept=".pdf" required>
                    </div>
                    <div class="mb-3">
                        <label for="aiProvider" class="form-label">Seleccione el proveedor de IA para extracción:</label>
                        <select class="form-select" id="aiProvider" name="ai_provider">
                            <option value="openai" selected>OpenAI (GPT-4)</option>
                            <option value="deepseek">DeepSeek</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="apiKey" class="form-label">API Key:</label>
                        <input type="password" class="form-control" id="apiKey" name="api_key" required>
                        <div class="form-text">
                            Ingrese su API Key para el proveedor seleccionado.
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary" id="processButton">
                        Procesar y Generar Archivo 211
                    </button>
                </form>
                
                <div class="text-center mt-3" id="loadingSpinner">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p>Procesando el documento y generando archivo 211, por favor espere...</p>
                </div>
                
                <div class="alert alert-danger mt-3" id="errorMessage">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <span id="errorText"></span>
                </div>
                
                <div id="downloadSection" class="text-center mt-4">
                    <div class="alert alert-success" role="alert">
                        <i class="bi bi-check-circle-fill success-icon"></i>
                        <h4>¡Archivo generado correctamente!</h4>
                        <p>El archivo .211 ha sido generado según los datos extraídos de la escritura.</p>
                    </div>
                    <a id="downloadLink" href="#" class="btn btn-success">
                        <i class="bi bi-download"></i> Descargar Archivo .211
                    </a>
                    <button id="resetButton" class="btn btn-outline-secondary mt-3">
                        <i class="bi bi-arrow-clockwise"></i> Procesar otro documento
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript for interactivity -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // References to DOM elements
            const uploadForm = document.getElementById('uploadForm');
            const processButton = document.getElementById('processButton');
            const loadingSpinner = document.getElementById('loadingSpinner');
            const downloadSection = document.getElementById('downloadSection');
            const downloadLink = document.getElementById('downloadLink');
            const resetButton = document.getElementById('resetButton');
            const errorMessage = document.getElementById('errorMessage');
            const errorText = document.getElementById('errorText');
            
            // Override the default form submission and use fetch API instead
            uploadForm.addEventListener('submit', async function(e) {
                e.preventDefault(); // Prevent default form submission
                
                // Hide error message if it was previously shown
                errorMessage.style.display = 'none';
                
                // Show loading spinner
                processButton.disabled = true;
                loadingSpinner.style.display = 'block';
                
                // Get form data
                const formData = new FormData(uploadForm);
                
                try {
                    console.log("Sending POST request to /proceso_completo");
                    
                    // Send request to server using POST method
                    const response = await fetch('/proceso_completo', {
                        method: 'POST',
                        body: formData
                    });
                    
                    console.log("Response received", response.status);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    console.log("Response data:", data);
                    
                    if (data.error) {
                        // Show error message
                        errorText.textContent = data.error;
                        errorMessage.style.display = 'block';
                        downloadSection.style.display = 'none';
                    } else {
                        // Show download section
                        downloadSection.style.display = 'block';
                        downloadLink.href = `/descargar/${data.file_id}`;
                    }
                } catch (error) {
                    console.error("Error in fetch:", error);
                    errorText.textContent = error.message;
                    errorMessage.style.display = 'block';
                    downloadSection.style.display = 'none';
                } finally {
                    // Hide spinner
                    processButton.disabled = false;
                    loadingSpinner.style.display = 'none';
                }
            });
            
            // Reset button handler
            if (resetButton) {
                resetButton.addEventListener('click', function() {
                    console.log("Reset button clicked");
                    
                    // Reset form
                    uploadForm.reset();
                    
                    // Hide sections
                    downloadSection.style.display = 'none';
                    errorMessage.style.display = 'none';
                });
            }
        });
    </script>
</body>
</html>"""

    template_path = Path("templates") / "simplified_index.html"
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Created template file: {template_path}")
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

def start_application():
    """Start the FastAPI application with uvicorn"""
    print_step("Starting the application")
    
    print("The application will start now. Press Ctrl+C to stop it.")
    print("Access the application at: http://127.0.0.1:8000")
    
    # Platform-specific command
    if platform.system() == "Windows":
        os.system("start http://127.0.0.1:8000")
    elif platform.system() == "Darwin":  # macOS
        os.system("open http://127.0.0.1:8000")
    elif platform.system() == "Linux":
        os.system("xdg-open http://127.0.0.1:8000")
    
    # Start uvicorn
    os.system("uvicorn updated_main:app --reload")

def main():
    """Main installation function"""
    print_header("211 File Generator - Instalación")
    
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
    
    print_header("Installation Completed Successfully")
    print("\nYou can now start the application with:")
    print("  uvicorn updated_main:app --reload")
    
    # Ask if user wants to start the application now
    response = input("\nDo you want to start the application now? (y/n): ")
    if response.lower() in ["y", "yes"]:
        start_application()

if __name__ == "__main__":
    main()
