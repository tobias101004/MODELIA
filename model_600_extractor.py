"""
<<<<<<< HEAD
model_600_extractor.py - Fixed version using the same approach as Modelo 211
=======
model_600_extractor.py - Module for extracting data specifically for Modelo 600
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
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
    
<<<<<<< HEAD
    Eres un asistente experto en extraer datos estructurados de escrituras de compraventa inmobiliaria en España.
    Tu tarea es extraer con precisión todos los datos solicitados para completar un formulario del Modelo 600.
    
    IMPORTANTE: Usa EXACTAMENTE los nombres de campos que te indico a continuación:
    
    1. COMPRADORES (usar nombre de sección: "compradores" - debe ser una lista):
       Para cada comprador extraer:
       - nombre: Nombre completo incluyendo apellidos
       - nif: Número del documento de identidad (DNI/NIE/Pasaporte)
       - direccion: Dirección completa
    
    2. VENDEDORES (usar nombre de sección: "vendedores" - debe ser una lista):
       Para cada vendedor extraer:
       - nombre: Nombre completo incluyendo apellidos
       - nie: Número del documento de identidad (DNI/NIE/Pasaporte)
       - direccion: Dirección completa
    
    3. DOCUMENTO (usar nombre de sección: "documento"):
=======
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
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
       - tipo: Tipo de documento (generalmente "Escritura de Compraventa")
       - fecha: Fecha del documento (formato DD/MM/AAAA)
       - protocolo: Número de protocolo
       - notario: Nombre del notario
    
<<<<<<< HEAD
    4. PROPIEDADES (usar nombre de sección: "propiedades" - debe ser una lista):
       Para cada propiedad extraer:
=======
    4. PROPIEDAD/es:
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
       - descripcion: Descripción del inmueble
       - superficie: Superficie útil en metros cuadrados
       - referencia: Referencia catastral completa
    
<<<<<<< HEAD
    5. VALORES (usar nombre de sección: "valores"):
       - importe: Importe de compraventa
       - valorReferencia: Valor de referencia catastral (si se menciona)
       - retencion: Retención 3% MOD211 (si aplica)
    
    6. REPRESENTACIÓN FISCAL (usar nombre de sección: "representacionFiscal"):
       - nombre: Nombre completo del representante
       - dni: DNI/NIE del representante
    
    7. PRESENTANTE DEL TÍTULO (usar nombre de sección: "presentante"):
       - empresa: Nombre de la empresa o persona
       - cif: CIF o NIF del presentante
    
    INSTRUCCIONES IMPORTANTES:
    - Busca minuciosamente en todo el texto
    - Identifica correctamente el país de residencia (es crítico para la retención del 3%)
    - Si el vendedor es extranjero y no residente, debe aplicarse retención del 3%
    - Verifica especialmente los tipos de documento (F/E/X/J)
    - Extrae la referencia catastral completa
    - Formatear fechas como DD/MM/AAAA
    - Formatear importes monetarios sin separadores de miles ni símbolo € (ej: 240000)
    - Mostrar cada persona (comprador o vendedor) por separado en listas
    - Si no encuentras algún dato, usa "NO ENCONTRADO"
    
    Devuelve los datos en formato JSON estructurado, utilizando EXACTAMENTE los nombres de secciones indicados.
    Los campos "compradores", "vendedores" y "propiedades" deben ser arrays/listas.
    """
    return instructions

class BaseExtractor:
    """Base class for AI-powered extractors"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _prepare_system_prompt(self) -> str:
        """Generate the system prompt for the AI model"""
        return get_model_600_instructions()
    
    def _clean_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate the extracted data for Modelo 600"""
        if not data:
            return {}
        
        # Ensure all required sections exist with default values
        cleaned_data = {
            "compradores": data.get("compradores", []),
            "vendedores": data.get("vendedores", []),
            "documento": data.get("documento", {}),
            "propiedades": data.get("propiedades", []),
            "valores": data.get("valores", {}),
            "representacionFiscal": data.get("representacionFiscal", {}),
            "presentante": data.get("presentante", {})
        }
        
        # Ensure compradores is a list with at least one entry
        if not cleaned_data["compradores"] or not isinstance(cleaned_data["compradores"], list):
            cleaned_data["compradores"] = [{
                "nombre": "NO ENCONTRADO",
                "nif": "NO ENCONTRADO",
                "direccion": "NO ENCONTRADO"
            }]
        
        # Ensure vendedores is a list with at least one entry
        if not cleaned_data["vendedores"] or not isinstance(cleaned_data["vendedores"], list):
            cleaned_data["vendedores"] = [{
                "nombre": "NO ENCONTRADO",
                "nie": "NO ENCONTRADO",
                "direccion": "NO ENCONTRADO"
            }]
        
        # Ensure propiedades is a list with at least one entry
        if not cleaned_data["propiedades"] or not isinstance(cleaned_data["propiedades"], list):
            cleaned_data["propiedades"] = [{
                "descripcion": "NO ENCONTRADO",
                "superficie": "NO ENCONTRADO",
                "referencia": "NO ENCONTRADO"
            }]
        
        # Set defaults for empty objects
        if not cleaned_data["documento"]:
            cleaned_data["documento"] = {
                "tipo": "NO ENCONTRADO",
                "fecha": "NO ENCONTRADO",
                "protocolo": "NO ENCONTRADO",
                "notario": "NO ENCONTRADO"
            }
        
        if not cleaned_data["valores"]:
            cleaned_data["valores"] = {
                "importe": "NO ENCONTRADO",
                "valorReferencia": "NO ENCONTRADO",
                "retencion": "NO ENCONTRADO"
            }
        
        if not cleaned_data["representacionFiscal"]:
            cleaned_data["representacionFiscal"] = {
                "nombre": "NO ENCONTRADO",
                "dni": "NO ENCONTRADO"
            }
        
        if not cleaned_data["presentante"]:
            cleaned_data["presentante"] = {
                "empresa": "NO ENCONTRADO",
                "cif": "NO ENCONTRADO"
            }
        
        logger.info(f"Cleaned data structure for Modelo 600: {list(cleaned_data.keys())}")
        return cleaned_data

class OpenAIExtractor(BaseExtractor):
    """Extractor using OpenAI API"""
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data using OpenAI API"""
        try:
            system_prompt = self._prepare_system_prompt()
            
            # Add retry logic for SSL issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        logger.info(f"Sending request to OpenAI API for Modelo 600 (attempt {attempt + 1})")
                        response = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}"
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
                    break  # Success, exit retry loop
                    
                except httpx.ConnectError as e:
                    if "SSL" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"SSL error on attempt {attempt + 1}, retrying...")
                        continue
                    else:
                        raise e
            
            if response.status_code == 200:
                logger.info("OpenAI API request successful for Modelo 600")
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                try:
                    data = json.loads(content)
                    logger.info("Successfully parsed JSON response from OpenAI for Modelo 600")
                    logger.info(f"Raw data structure: {list(data.keys())}")
                    return self._clean_output(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from OpenAI: {e}")
                    return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {"error": f"Error API OpenAI: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Exception in OpenAI extraction for Modelo 600: {str(e)}")
            return {"error": f"Error en extracción con OpenAI: {str(e)}"}

class DeepSeekExtractor(BaseExtractor):
    """Extractor using DeepSeek API"""
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data using DeepSeek API"""
        try:
            system_prompt = self._prepare_system_prompt()
            
            # Add retry logic for SSL issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        logger.info(f"Sending request to DeepSeek API for Modelo 600 (attempt {attempt + 1})")
                        response = await client.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}"
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
                    break  # Success, exit retry loop
                    
                except httpx.ConnectError as e:
                    if "SSL" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"SSL error on attempt {attempt + 1}, retrying...")
                        continue
                    else:
                        raise e
            
            if response.status_code == 200:
                logger.info("DeepSeek API request successful for Modelo 600")
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                try:
                    data = json.loads(content)
                    logger.info("Successfully parsed JSON response from DeepSeek for Modelo 600")
                    logger.info(f"Raw data structure: {list(data.keys())}")
                    return self._clean_output(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from DeepSeek: {e}")
                    return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return {"error": f"Error API DeepSeek: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Exception in DeepSeek extraction for Modelo 600: {str(e)}")
            return {"error": f"Error en extracción con DeepSeek: {str(e)}"}

# Factory to get the appropriate extractor
def get_extractor(provider: str, api_key: str) -> BaseExtractor:
    """Return the appropriate extractor based on provider"""
    if provider.lower() == "openai":
        return OpenAIExtractor(api_key)
    elif provider.lower() == "deepseek":
        return DeepSeekExtractor(api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# Main function to extract data
async def extract_data_for_model_600(text: str, api_key: str, provider: str = "openai") -> Dict[str, Any]:
    """Extract structured data from deed text using AI for Modelo 600"""
    try:
        logger.info(f"Starting Modelo 600 extraction with {provider}")
        extractor = get_extractor(provider, api_key)
        extracted_data = await extractor.extract(text)
        
        # Post-process data to ensure required fields
        if 'error' not in extracted_data:
            logger.info(f"Final extracted data structure: {list(extracted_data.keys())}")
            logger.info(f"Compradores count: {len(extracted_data.get('compradores', []))}")
            logger.info(f"Vendedores count: {len(extracted_data.get('vendedores', []))}")
        else:
            logger.error(f"Extraction error: {extracted_data['error']}")
        
        return extracted_data
    except Exception as e:
        logger.error(f"Error in extract_data_for_model_600: {str(e)}")
        return {"error": f"Error en extracción con IA: {str(e)}"}
=======
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
>>>>>>> e042e24fc2311fbacc4a45efd92355288a8cea04
