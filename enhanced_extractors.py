"""
enhanced_extractors.py - Module for extracting structured data from deed text using AI
"""

# Add this to the top of enhanced_extractors.py to avoid the import error

def get_extraction_instructions() -> str:
    """Get AI extraction instructions for deed data"""
    instructions = """
    INSTRUCCIONES DE EXTRACCIÓN DE DATOS:
    
    Extrae los siguientes datos de la escritura de compraventa con precisión. Si no encuentras algún dato, déjalo en blanco.
    
    IMPORTANTE: Usa EXACTAMENTE los nombres de campos y secciones que se indican a continuación:
    
    1. DATOS DEL COMPRADOR (usar nombre de sección: "comprador"):
       - nombre_completo: Nombre completo incluyendo apellidos
       - tipo_documento: F (español con DNI), E (extranjero con NIE), X (extranjero con pasaporte)
       - nif_nie: Número del documento de identidad
       - direccion: Dirección completa
       - direccion_complemento: Información adicional de dirección
       - codigo_postal: Código postal
       - municipio: Ciudad o municipio
       - provincia: Provincia
       - pais: País de residencia en MAYÚSCULAS
    
    2. DATOS DEL VENDEDOR (usar nombre de sección: "vendedor"):
       - nombre_completo: Nombre completo incluyendo apellidos
       - tipo_documento: F (español con DNI), J (persona jurídica/empresa), E (extranjero con NIE), X (extranjero con pasaporte)
       - nif_nie: Número del documento de identidad
       - direccion: Dirección completa
       - direccion_complemento: Información adicional de dirección
       - codigo_postal: Código postal
       - municipio: Ciudad o municipio
       - provincia: Provincia
       - pais: País de residencia en MAYÚSCULAS
    
    3. DATOS DEL INMUEBLE (usar nombre de sección: "inmueble"):
       - direccion: Dirección completa del inmueble
       - referencia_catastral: Referencia catastral completa
       - codigo_postal: Código postal
       - municipio: Municipio
       - provincia: Provincia
    
    4. DATOS DE LA OPERACIÓN (usar nombre de sección: "operacion"):
       - fecha_documento: Fecha de la escritura (formato DD/MM/AAAA)
       - importe: Importe total de la compraventa en euros (sólo números)
       - retencion: Retención aplicada (generalmente 3% para extranjeros no residentes)
       - porcentaje_adquirido: Porcentaje adquirido (normalmente 100)
       - tipo_iva: Tipo de IVA aplicado (0 si no aplica)
       - tipo_itp: Tipo impositivo ITP (normalmente entre 4-10%)
       - codigo_notario: Código del notario
       - numero_protocolo: Número de protocolo de la escritura
    
    5. DATOS DEL PRESENTANTE (usar nombre de sección: "presentante"):
       - nombre_completo: Nombre completo
       - tipo_documento: Tipo de documento
       - nif_nie: Número de identificación
    
    6. DATOS DEL REPRESENTANTE FISCAL (usar nombre de sección: "representante_fiscal"):
       - nombre_completo: Nombre completo
       - tipo_documento: Tipo de documento
       - nif_nie: Número de identificación
       - direccion: Dirección completa
       - codigo_postal: Código postal
       - municipio: Municipio
       - pais: País en MAYÚSCULAS
    
    INSTRUCCIONES IMPORTANTES:
    - Busca minuciosamente en todo el texto
    - Identifica correctamente el país de residencia (es crítico para la retención del 3%)
    - Si el vendedor es extranjero y no residente, debe aplicarse retención del 3%
    - Verifica especialmente los tipos de documento (F/E/X/J)
    - Extrae la referencia catastral completa
    - NO USES nombres de secciones diferentes a los indicados (como "datos_comprador", etc.)
    
    Devuelve los datos en formato JSON estructurado, utilizando EXACTAMENTE los nombres de secciones indicados.
    """
    return instructions
import httpx
import json
import re
from typing import Dict, Any, Optional, List
import logging
# Comment out or remove the import line
# from template_formatter import get_extraction_instructions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseExtractor:
    """Base class for AI-powered extractors"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _prepare_system_prompt(self) -> str:
        """Generate the system prompt for the AI model with enhanced instructions"""
        return """
        Eres un asistente experto en extraer datos estructurados de escrituras de compraventa inmobiliaria en España.
        Tu tarea es extraer con precisión todos los datos solicitados para generar un archivo 211 para la Agencia Tributaria.
        
        IMPORTANTE: Debes usar EXACTAMENTE los nombres de campos que te indico a continuación, sin prefijos 'datos_' u otros.
        Los campos principales deben ser exactamente: comprador, vendedor, inmueble, operacion, presentante, representante_fiscal.
        
        """ + get_extraction_instructions()
    
    def _clean_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate the extracted data"""
        if not data:
            return {}
        
        # Standardize field names - ensure we have the correct structure
        cleaned_data = {}
        field_mapping = {
            'datos_comprador': 'comprador',
            'comprador': 'comprador',
            'datos_vendedor': 'vendedor',
            'vendedor': 'vendedor',
            'datos_inmueble': 'inmueble',
            'inmueble': 'inmueble',
            'datos_operacion': 'operacion',
            'operacion': 'operacion',
            'datos_presentante': 'presentante',
            'presentante': 'presentante',
            'datos_representante_fiscal': 'representante_fiscal',
            'representante_fiscal': 'representante_fiscal'
        }
        
        # Transfer data with correct field names
        for old_key, new_key in field_mapping.items():
            if old_key in data:
                if new_key not in cleaned_data:
                    cleaned_data[new_key] = data[old_key]
        
        # Ensure we have all required sections
        for section in ['comprador', 'vendedor', 'inmueble', 'operacion', 'presentante', 'representante_fiscal']:
            if section not in cleaned_data:
                cleaned_data[section] = {}
        
        # Clean numeric values
        for section in ['operacion']:
            if section in cleaned_data:
                for field in ['importe', 'retencion', 'porcentaje_adquirido', 'tipo_iva', 'tipo_itp']:
                    if field in cleaned_data[section] and cleaned_data[section][field]:
                        try:
                            # Handle various formats and clean them
                            value_str = str(cleaned_data[section][field])
                            # Remove currency symbols, spaces and other non-numeric characters except decimal point
                            value_str = re.sub(r'[^\d.,]', '', value_str)
                            # Replace comma with dot for decimal
                            value_str = value_str.replace(',', '.')
                            cleaned_data[section][field] = float(value_str)
                        except (ValueError, TypeError):
                            # Default values if conversion fails
                            if field == 'porcentaje_adquirido':
                                cleaned_data[section][field] = 100
                            elif field == 'tipo_iva':
                                cleaned_data[section][field] = 0
                            elif field == 'tipo_itp':
                                cleaned_data[section][field] = 7
                            else:
                                cleaned_data[section][field] = 0
        
        # Ensure country names are uppercase
        for section in ['comprador', 'vendedor', 'representante_fiscal']:
            if section in cleaned_data and cleaned_data[section] and 'pais' in cleaned_data[section]:
                if cleaned_data[section]['pais']:
                    cleaned_data[section]['pais'] = cleaned_data[section]['pais'].upper()
        
        # Add default values for required fields
        if 'porcentaje_adquirido' not in cleaned_data['operacion'] or not cleaned_data['operacion']['porcentaje_adquirido']:
            cleaned_data['operacion']['porcentaje_adquirido'] = 100
            
        if 'tipo_iva' not in cleaned_data['operacion'] or not cleaned_data['operacion']['tipo_iva']:
            cleaned_data['operacion']['tipo_iva'] = 0
            
        if 'tipo_itp' not in cleaned_data['operacion'] or not cleaned_data['operacion']['tipo_itp']:
            cleaned_data['operacion']['tipo_itp'] = 7  # Default ITP rate
            
        # Calculate retention if not present but should be
        if ('retencion' not in cleaned_data['operacion'] or not cleaned_data['operacion']['retencion']) and 'importe' in cleaned_data['operacion']:
            # Check if buyer or seller is non-resident in Spain
            is_seller_non_resident = False
            
            if 'vendedor' in cleaned_data and 'pais' in cleaned_data['vendedor'] and cleaned_data['vendedor']['pais'] != 'ESPAÑA':
                is_seller_non_resident = True
                
            if is_seller_non_resident and 'importe' in cleaned_data['operacion'] and cleaned_data['operacion']['importe']:
                # Calculate 3% retention
                cleaned_data['operacion']['retencion'] = round(cleaned_data['operacion']['importe'] * 0.03, 2)
        
        logger.info(f"Cleaned data structure: {list(cleaned_data.keys())}")
        return cleaned_data


class OpenAIExtractor(BaseExtractor):
    """Extractor using OpenAI API"""
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data using OpenAI API"""
        try:
            system_prompt = self._prepare_system_prompt()
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info("Sending request to OpenAI API")
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
            
            if response.status_code == 200:
                logger.info("OpenAI API request successful")
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                try:
                    data = json.loads(content)
                    logger.info("Successfully parsed JSON response from OpenAI")
                    logger.info(f"Raw data structure: {list(data.keys())}")
                    return self._clean_output(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from OpenAI: {e}")
                    return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {"error": f"Error API OpenAI: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Exception in OpenAI extraction: {str(e)}")
            return {"error": f"Error en extracción con OpenAI: {str(e)}"}


class DeepSeekExtractor(BaseExtractor):
    """Extractor using DeepSeek API"""
    
    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured data using DeepSeek API"""
        try:
            system_prompt = self._prepare_system_prompt()
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info("Sending request to DeepSeek API")
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
            
            if response.status_code == 200:
                logger.info("DeepSeek API request successful")
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                try:
                    data = json.loads(content)
                    logger.info("Successfully parsed JSON response from DeepSeek")
                    logger.info(f"Raw data structure: {list(data.keys())}")
                    return self._clean_output(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from DeepSeek: {e}")
                    return {"error": f"Error al decodificar la respuesta JSON: {str(e)}"}
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return {"error": f"Error API DeepSeek: {response.status_code} - {response.text}"}
                
        except Exception as e:
            logger.error(f"Exception in DeepSeek extraction: {str(e)}")
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
async def extract_data_with_ai(text: str, api_key: str, provider: str = "openai") -> Dict[str, Any]:
    """Extract structured data from deed text using AI"""
    try:
        logger.info(f"Starting extraction with {provider}")
        extractor = get_extractor(provider, api_key)
        extracted_data = await extractor.extract(text)
        
        # Post-process data to ensure required fields
        if 'error' not in extracted_data:
            # Make sure we log the final structure
            logger.info(f"Final extracted data structure: {list(extracted_data.keys())}")
            logger.info(f"Comprador data: {extracted_data.get('comprador', {})}")
        else:
            logger.error(f"Extraction error: {extracted_data['error']}")
        
        return extracted_data
    except Exception as e:
        logger.error(f"Error in extract_data_with_ai: {str(e)}")
        return {"error": f"Error en extracción con IA: {str(e)}"}
