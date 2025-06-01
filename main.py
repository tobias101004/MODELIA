"""
MODEL.IA - Integrated application for processing real estate documents
<<<<<<< HEAD
Fixed version with proper error handling and CORS support
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
"""

from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
<<<<<<< HEAD
from fastapi.middleware.cors import CORSMiddleware
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
import uuid
from pathlib import Path
import logging
import json
import re
from typing import Dict, Any

# Import our modules
from pdfminer.high_level import extract_text
from enhanced_extractors import extract_data_with_ai
from template_formatter import generate_211_file
from country_utils import get_country_code
from model_600_extractor import extract_data_for_model_600

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
<<<<<<< HEAD
for directory in ["temp", "static", "templates"]:
=======
for directory in ["temp", "static"]:
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
    Path(directory).mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(title="MODEL.IA")

<<<<<<< HEAD
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Routes for HTML pages
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page"""
<<<<<<< HEAD
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return HTMLResponse("Error loading page", status_code=500)

@app.get("/api", response_class=HTMLResponse)
async def api_page(request: Request):
    """Render the API configuration page"""
    try:
        return templates.TemplateResponse("api.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering API page: {str(e)}")
        return HTMLResponse("Error loading page", status_code=500)
=======
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/cuenta", response_class=HTMLResponse)
async def cuenta(request: Request):
    """Render the account page"""
    return templates.TemplateResponse("cuenta.html", {"request": request})

@app.get("/contacto", response_class=HTMLResponse)
async def contacto(request: Request):
    """Render the contact page"""
    return templates.TemplateResponse("contacto.html", {"request": request})
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

@app.get("/modelo-211", response_class=HTMLResponse)
async def modelo_211(request: Request):
    """Render the modelo 211 page"""
<<<<<<< HEAD
    try:
        return templates.TemplateResponse("modelo-211.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering modelo-211 page: {str(e)}")
        return HTMLResponse("Error loading page", status_code=500)
=======
    return templates.TemplateResponse("modelo-211.html", {"request": request})
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

@app.get("/modelo-600", response_class=HTMLResponse)
async def modelo_600(request: Request):
    """Render the modelo 600 page"""
<<<<<<< HEAD
    try:
        return templates.TemplateResponse("modelo-600.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering modelo-600 page: {str(e)}")
        return HTMLResponse("Error loading page", status_code=500)
=======
    return templates.TemplateResponse("modelo-600.html", {"request": request})
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

@app.get("/modelo-211-edit", response_class=HTMLResponse)
async def modelo_211_edit(request: Request):
    """Render the modelo 211 edit page"""
    file_id = request.query_params.get("file_id", "")
    
<<<<<<< HEAD
    if not file_id:
        return HTMLResponse("Missing file_id parameter", status_code=400)
    
    try:
        # Load the extracted data from the file
        data_path = Path("temp") / f"{file_id}_data.json"
        if not data_path.exists():
            return HTMLResponse("Data file not found", status_code=404)
            
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return templates.TemplateResponse("modelo-211-edit.html", {
            "request": request,
            "file_id": file_id,
            "data": data
        })
    except Exception as e:
        logger.error(f"Error loading data for modelo 211 edit: {str(e)}")
        return HTMLResponse("Error loading data. Please try again.", status_code=500)
=======
    try:
        # Load the extracted data from the file
        data_path = Path("temp") / f"{file_id}_data.json"
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return templates.TemplateResponse("modelo-211-edit.html", {"request": request, "file_id": file_id, "data": data})
    except Exception as e:
        logger.error(f"Error loading data for modelo 211 edit: {str(e)}")
        return HTMLResponse("Error loading data. Please try again.")
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

@app.get("/modelo-211-exito", response_class=HTMLResponse)
async def modelo_211_exito(request: Request):
    """Render the modelo 211 success page"""
    file_id = request.query_params.get("file_id", "")
<<<<<<< HEAD
    return templates.TemplateResponse("modelo-211-exito.html", {
        "request": request,
        "file_id": file_id
    })
=======
    return templates.TemplateResponse("modelo-211-exito.html", {"request": request, "file_id": file_id})
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

@app.get("/modelo-600-resultados", response_class=HTMLResponse)
async def modelo_600_resultados(request: Request):
    """Render the modelo 600 results page"""
    file_id = request.query_params.get("file_id", "")
    
<<<<<<< HEAD
    if not file_id:
        return HTMLResponse("Missing file_id parameter", status_code=400)
    
    try:
        data_path = Path("temp") / f"{file_id}_data.json"
        if not data_path.exists():
            return HTMLResponse("Data file not found", status_code=404)
            
=======
    # Load the extracted data from the file
    try:
        data_path = Path("temp") / f"{file_id}_data.json"
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Format the data for modelo 600 display
        formatted_data = format_data_for_model_600(data)
        
        return templates.TemplateResponse(
<<<<<<< HEAD
            "modelo-600-resultados.html",
=======
            "modelo-600-resultados.html", 
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
            {"request": request, "datos": formatted_data}
        )
    except Exception as e:
        logger.error(f"Error loading data for modelo 600 results: {str(e)}")
<<<<<<< HEAD
        return HTMLResponse("Error loading data. Please try again.", status_code=500)
=======
        return HTMLResponse("Error loading data. Please try again.")
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04

# API endpoints
@app.post("/proceso_completo")
async def proceso_completo(
    pdf_file: UploadFile = File(...),
    ai_provider: str = Form("openai"),
    api_key: str = Form(...)
):
    """Process PDF file for modelo 211 and extract data"""
    try:
<<<<<<< HEAD
        # Validate file type
        if not pdf_file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"error": "Solo se permiten archivos PDF"}
            )
        
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
        # Log request details for debugging
        logger.info(f"Received proceso_completo request with file: {pdf_file.filename}, provider: {ai_provider}")
        
        # Create a temporary file to store the PDF
        file_id = str(uuid.uuid4())
        pdf_path = Path("temp") / f"{file_id}.pdf"
        
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
            
<<<<<<< HEAD
            if text_length < 100:
                return JSONResponse(
                    status_code=400,
                    content={"error": "El PDF parece estar vacío o no contiene texto extraíble"}
                )
            
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
            # Save extracted text for debugging
            with open(Path("temp") / f"{file_id}_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error al extraer texto del PDF: {str(e)}"}
            )
        
        # Extract structured data with AI
        try:
            logger.info(f"Extracting data with {ai_provider}")
            extracted_data = await extract_data_with_ai(text, api_key, ai_provider)
            
            # Save extracted data for debugging
            with open(Path("temp") / f"{file_id}_data.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            if "error" in extracted_data:
                logger.error(f"Error in AI extraction: {extracted_data['error']}")
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Error en la extracción de datos: {extracted_data['error']}"}
                )
                
            logger.info("Data extraction successful")
            
            # Return file ID for edit page
            return {"file_id": file_id, "message": "Datos extraídos correctamente"}
            
        except Exception as e:
            logger.error(f"Error in AI extraction: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error en la extracción de datos con IA: {str(e)}"}
            )
        
    except Exception as e:
<<<<<<< HEAD
        logger.error(f"Unexpected error in proceso_completo: {str(e)}")
=======
        logger.error(f"Unexpected error in process_pdf: {str(e)}")
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
        # Return error response
        return JSONResponse(
            status_code=500,
            content={"error": f"Error inesperado al procesar la solicitud: {str(e)}"}
        )

@app.post("/procesar_600")
async def procesar_600(
    pdf_file: UploadFile = File(...),
    ai_provider: str = Form("openai"),
    api_key: str = Form(...),
    model_type: str = Form("600")
):
    """Process PDF file for modelo 600 extraction"""
    try:
<<<<<<< HEAD
        # Validate file type
        if not pdf_file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"error": "Solo se permiten archivos PDF"}
            )
        
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
        # Log request details for debugging
        logger.info(f"Received procesar_600 request with file: {pdf_file.filename}, provider: {ai_provider}")
        
        # Create a temporary file to store the PDF
        file_id = str(uuid.uuid4())
        pdf_path = Path("temp") / f"{file_id}.pdf"
        
        # Save uploaded file to temporary location
        with open(pdf_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)
        
        logger.info(f"PDF saved to {pdf_path} for Modelo 600 processing")
        
        # Extract text from PDF
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            text = extract_text(pdf_path)
            text_length = len(text)
            logger.info(f"Extracted {text_length} characters from PDF")
            
<<<<<<< HEAD
            if text_length < 100:
                return JSONResponse(
                    status_code=400,
                    content={"error": "El PDF parece estar vacío o no contiene texto extraíble"}
                )
            
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
            # Save extracted text for debugging
            with open(Path("temp") / f"{file_id}_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error al extraer texto del PDF: {str(e)}"}
            )
        
        # Extract structured data with AI
        try:
            logger.info(f"Extracting data for Modelo 600 with {ai_provider}")
            # Use the specialized extractor for Modelo 600
            extracted_data = await extract_data_for_model_600(text, api_key, ai_provider)
            
            # Save extracted data for debugging
            with open(Path("temp") / f"{file_id}_data.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
<<<<<<< HEAD
            # Debug logging
            logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
            if 'compradores' in extracted_data:
                logger.info(f"Compradores data: {extracted_data['compradores']}")
            if 'valores' in extracted_data:
                logger.info(f"Valores data: {extracted_data['valores']}")
            
=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
            if "error" in extracted_data:
                logger.error(f"Error in AI extraction: {extracted_data['error']}")
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Error en la extracción de datos: {extracted_data['error']}"}
                )
                
            logger.info("Data extraction successful for Modelo 600")
            
            # Return file ID for the results page
            return {"file_id": file_id, "message": "Datos extraídos correctamente"}
            
        except Exception as e:
            logger.error(f"Error in AI extraction for Modelo 600: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Error en la extracción de datos con IA: {str(e)}"}
            )
        
    except Exception as e:
        logger.error(f"Unexpected error in procesar_600: {str(e)}")
        # Return error response
        return JSONResponse(
            status_code=500,
            content={"error": f"Error inesperado al procesar la solicitud: {str(e)}"}
        )

@app.post("/generar_211")
async def generar_211(data: Dict[str, Any] = Body(...)):
    """Generate 211 file from form data"""
    try:
        logger.info("Generating 211 file from form data")
        
        file_id = data.get("file_id", str(uuid.uuid4()))
        
        # Generate 211 file content
        file_content = generate_211_file(data)
        
        # Create a temporary file for the 211 content
        file_path = Path("temp") / f"{file_id}.211"
        
        # Write content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
            
        logger.info(f"211 file generated successfully: {file_path}")
        
        # Return file ID for download
        return {"file_id": file_id, "message": "Archivo 211 generado correctamente"}
        
    except Exception as e:
        logger.error(f"Error generating 211 file: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al generar el archivo 211: {str(e)}"}
        )

@app.get("/descargar/{file_id}")
async def descargar_211(file_id: str):
    """Download generated 211 file"""
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

def format_data_for_model_600(extracted_data):
    """Format the extracted data for model 600 presentation"""
    # For Modelo 600, the extractor already returns data in the format we need
    # Just ensure all required fields are present
    
    # Ensure compradores list exists
    if "compradores" not in extracted_data or not extracted_data["compradores"]:
        extracted_data["compradores"] = [{
            "nombre": "NO ENCONTRADO",
            "nif": "NO ENCONTRADO",
            "direccion": "NO ENCONTRADO"
        }]
    
    # Ensure vendedores list exists
    if "vendedores" not in extracted_data or not extracted_data["vendedores"]:
        extracted_data["vendedores"] = [{
            "nombre": "NO ENCONTRADO",
            "nie": "NO ENCONTRADO",
            "direccion": "NO ENCONTRADO"
        }]
    
    # Ensure documento exists
    if "documento" not in extracted_data:
        extracted_data["documento"] = {
            "tipo": "NO ENCONTRADO",
            "fecha": "NO ENCONTRADO",
            "protocolo": "NO ENCONTRADO",
            "notario": "NO ENCONTRADO"
        }
    
    # Ensure propiedades list exists
    if "propiedades" not in extracted_data or not extracted_data["propiedades"]:
        extracted_data["propiedades"] = [{
            "descripcion": "NO ENCONTRADO",
            "superficie": "NO ENCONTRADO",
            "referencia": "NO ENCONTRADO"
        }]
    
    # Ensure valores exists
    if "valores" not in extracted_data:
        extracted_data["valores"] = {
            "importe": "NO ENCONTRADO",
            "valorReferencia": "NO ENCONTRADO",
            "retencion": "NO ENCONTRADO"
        }
    
    # Ensure representacionFiscal exists
    if "representacionFiscal" not in extracted_data:
        extracted_data["representacionFiscal"] = {
            "nombre": "NO ENCONTRADO",
            "dni": "NO ENCONTRADO"
        }
    
    # Ensure presentante exists
    if "presentante" not in extracted_data:
        extracted_data["presentante"] = {
            "empresa": "NO ENCONTRADO",
            "cif": "NO ENCONTRADO"
        }
    
    return extracted_data

<<<<<<< HEAD
# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

# Cleanup function for startup
@app.on_event("startup")
async def startup_event():
    """Clean temp directory on startup"""
    logger.info("Starting up MODEL.IA application")
    logger.info("Cleaning up temporary files on startup")
    try:
        for file in Path("temp").glob("*"):
            if file.suffix in [".pdf", ".211", ".txt", ".json"]:
                file.unlink()
                logger.info(f"Deleted temporary file: {file}")
    except Exception as e:
        logger.error(f"Error cleaning temporary files: {str(e)}")

=======
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
