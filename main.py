"""
Updated main application with simplified workflow for 211 file generation
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import uuid
from pathlib import Path
from pdfminer.high_level import extract_text
import logging
import json

# Import our modules
from enhanced_extractors import extract_data_with_ai
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
app = FastAPI(title="Generador de Archivos 211 para Hacienda")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the main page with the form to upload a PDF"""
    logger.info("Rendering index page")
    return templates.TemplateResponse("simplified_index.html", {"request": request})

@app.post("/proceso_completo")
async def proceso_completo(
    pdf_file: UploadFile = File(...),
    ai_provider: str = Form("openai"),
    api_key: str = Form(...)
):
    """Process PDF file, extract data, and generate 211 file in one step"""
    try:
        # Create a temporary file to store the PDF
        pdf_path = Path("temp") / f"{uuid.uuid4()}.pdf"
        
        # Save uploaded file to temporary location
        with open(pdf_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)
        
        logger.info(f"PDF saved to {pdf_path}")
        
        # Extract text from PDF
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            text = extract_text(pdf_path)
            text_length = len(text)
            logger.info(f"Extracted {text_length} characters from PDF")
            
            # Save extracted text for debugging
            with open(Path("temp") / f"{pdf_path.stem}_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error al extraer texto del PDF: {str(e)}"}
            )
        
        # Extract structured data with AI
        try:
            logger.info(f"Extracting structured data with {ai_provider}")
            extracted_data = await extract_data_with_ai(text, api_key, ai_provider)
            
            # Save extracted data for debugging
            with open(Path("temp") / f"{pdf_path.stem}_data.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            if "error" in extracted_data:
                logger.error(f"Error in AI extraction: {extracted_data['error']}")
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Error en la extracción de datos: {extracted_data['error']}"}
                )
                
            logger.info("Data extraction successful")
            
            # Generate 211 file
            try:
                logger.info("Generating 211 file from extracted data")
                file_content = generate_211_file(extracted_data)
                
                # Create a temporary file for the 211 content
                file_id = uuid.uuid4()
                file_path = Path("temp") / f"{file_id}.211"
                
                # Write content to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                    
                logger.info(f"211 file generated successfully: {file_path}")
                
                # Return file path for download
                return {"file_id": str(file_id), "message": "Archivo .211 generado correctamente"}
                
            except Exception as e:
                logger.error(f"Error generating 211 file: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Error al generar el archivo .211: {str(e)}"}
                )
            
        except Exception as e:
            logger.error(f"Error in AI extraction: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error en la extracción de datos con IA: {str(e)}"}
            )
        
    except Exception as e:
        logger.error(f"Unexpected error in process_pdf: {str(e)}")
        # Return error response
        return JSONResponse(
            status_code=500,
            content={"error": f"Error inesperado al procesar la solicitud: {str(e)}"}
        )

@app.get("/descargar/{file_id}")
async def descargar_211(file_id: str):
    """Download generated .211 file"""
    try:
        # Construct file path
        file_path = Path("temp") / f"{file_id}.211"
        
        # Check if file exists
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "Archivo no encontrado"}
            )
        
        # Return file for download
        return FileResponse(
            path=file_path,
            filename="declaracion.211",
            media_type="application/octet-stream"
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al descargar el archivo: {str(e)}"}
        )

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {"status": "ok", "message": "API funcionando correctamente"}

# Background task to clean up temporary files
@app.on_event("startup")
async def startup_event():
    """Clean temp directory on startup"""
    logger.info("Cleaning up temporary files on startup")
    for file in Path("temp").glob("*"):
        try:
            if file.suffix in [".pdf", ".211", ".txt", ".json"]:
                file.unlink()
                logger.info(f"Deleted temporary file: {file}")
        except Exception as e:
            logger.error(f"Error deleting temporary file {file}: {str(e)}")

# Run server if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
