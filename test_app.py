"""
Test application to verify imports are working correctly
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Testing the imports
from template_formatter import generate_211_file, REQUIRED_FIELDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create directories if they don't exist
for directory in ["temp", "static", "templates"]:
    Path(directory).mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(title="Test App - 211 File Generator")

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render a simple test page"""
    logger.info("Test app is running!")
    return {"message": "Test app is running! Imports are working correctly."}

@app.get("/test_imports")
async def test_imports():
    """Test that imports are working"""
    # Test field structure
    field_count = sum(len(fields) for section, fields in REQUIRED_FIELDS.items())
    
    # Test generate function with minimal data
    test_data = {
        "comprador": {"nombre_completo": "Test Buyer", "tipo_documento": "F", "nif_nie": "12345678Z", "direccion": "Test Address", "pais": "ESPAÑA"},
        "vendedor": {"nombre_completo": "Test Seller", "tipo_documento": "F", "nif_nie": "87654321X", "direccion": "Test Address", "pais": "ESPAÑA"},
        "inmueble": {"direccion": "Test Property", "referencia_catastral": "1234567890ABCDEFGH", "municipio": "Test City", "provincia": "Test Province"},
        "operacion": {"fecha_documento": "01/05/2025", "importe": 150000, "porcentaje_adquirido": 100}
    }
    
    # Generate a 211 file with test data
    file_content = generate_211_file(test_data)
    
    return {
        "status": "success",
        "message": "Imports are working correctly",
        "fields_count": field_count,
        "generated_file_lines": file_content.count('\n') + 1
    }

# Run server if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
