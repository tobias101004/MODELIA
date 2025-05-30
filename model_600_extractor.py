"""
model_600_extractor.py - Module for extracting data specifically for Modelo 600
"""

import httpx
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_model_600_instructions() -> str:
    """Get AI extraction instructions for Modelo 600 data"""
    instructions = """
    INSTRUCCIONES DE EXTRACCIÓN DE DATOS PARA MODELO 600:
    
    Eres un AI legal especializado en interpretar contratos de compraventa de inmuebles (escrituras) en España. 
    Tu tarea es leer el texto proporcionado y generar una respuesta estructurada con información clave, 
    formateada exactamente como se especifica.
    
    Lee atentamente el texto de la escritura y extrae la siguiente información clave:
    
    1. COMPRADORES:
       - nombre: Nombre completo incluyendo apellidos
       - nif: Número de identificación (DNI, NIE o Pasaporte)
       - direccion: Dirección completa
    
    2. VENDEDORES:
       - nombre: Nombre completo incluyendo apellidos
       - nie: Número de identificación (DNI, NIE o Pasaporte)
       - direccion: Dirección completa
    
    3. DOCUMENTO:
       - tipo: Tipo de documento (generalmente "Escritura de Compraventa")
       - fecha: Fecha del documento (formato DD/MM/AAAA)
       - protocolo: Número de protocolo
       - notario: Nombre del notario
    
    4. PROPIEDAD/es:
       - descripcion: Descripción del inmueble
       - superficie: Superficie útil en metros cuadrados
       - referencia: Referencia catastral completa
    
    5. VALORES:
       - importe: Importe de compraventa
       - valorReferencia: Valor de referencia catastral
       - retencion: Retención 3% MOD211 (si aplica)
    
    6. REPRESENTACIÓN FISCAL:
       - nombre: Nombre completo del representante
       - dni: DNI/NIE del representante
    
    7. PRESENTANTE DEL TÍTULO:
       - empresa: Nombre de la empresa o persona
       - cif: CIF o NIF del presentante
    
    Reglas de formateo:
    - Formatear fechas como DD/MM/AAAA
    - Formatear importes monetarios sin separadores de miles ni símbolo € (ej: 240000,00)
    - Mostrar cada persona (comprador o vendedor) por separado
    - Reemplazar datos no encontrados con "NO ENCONTRADO"
    
    Devuelve los datos en formato JSON estructurado usando EXACTAMENTE los nombres de sección indicados.
    """
    return instructions

async def extract_data_for_model_600(text: str, api_key: str, provider: str = "openai") -> Dict[str, Any]:
    """
    Extract structured data specifically for Modelo 600 using AI
    
    Args:
        text: The text from the deed document
        api_key: API key for the AI provider
        provider: AI provider to use (openai or deepseek)
        
    Returns:
        Dictionary with structured data for Modelo 600
    """
    try:
        logger.info(f"Starting Modelo 600 extraction with {provider}")
        
        # Get specialized instructions for Modelo 600
        system_prompt = get_model_600_instructions()
        
        if provider.lower() == "openai":
            return await extract_with_openai(text, api_key, system_prompt)
        elif provider.lower() == "deepseek":
            return await extract_with_deepseek(text, api_key, system_prompt)
        else:
            return {"error": f"Proveedor no soportado: {provider}"}
            
    except Exception as e:
        logger.error(f"Error in extract_data_for_model_600: {str(e)}")
        return {"error": f"Error en extracción para Modelo 600: {str(e)}"}

async def extract_with_openai(text: str, api_key: str, system_prompt: str) -> Dict[str, Any]:
    """Extract data using OpenAI API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("Sending request to OpenAI API for Modelo 600")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
        
        if response.status_code == 200:
            logger.info("OpenAI API request successful for Modelo 600")
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                data = json.loads(content)
                logger.info("Successfully parsed JSON response from OpenAI for Modelo 600")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from OpenAI: {e}")
                return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return {"error": f"Error API OpenAI: {response.status_code} - {response.text}"}
            
    except Exception as e:
        logger.error(f"Exception in OpenAI extraction for Modelo 600: {str(e)}")
        return {"error": f"Error en extracción con OpenAI: {str(e)}"}

async def extract_with_deepseek(text: str, api_key: str, system_prompt: str) -> Dict[str, Any]:
    """Extract data using DeepSeek API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("Sending request to DeepSeek API for Modelo 600")
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
        
        if response.status_code == 200:
            logger.info("DeepSeek API request successful for Modelo 600")
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                data = json.loads(content)
                logger.info("Successfully parsed JSON response from DeepSeek for Modelo 600")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from DeepSeek: {e}")
                return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
        else:
            logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return {"error": f"Error API DeepSeek: {response.status_code} - {response.text}"}
            
    except Exception as e:
        logger.error(f"Exception in DeepSeek extraction for Modelo 600: {str(e)}")
        return {"error": f"Error en extracción con DeepSeek: {str(e)}"}
