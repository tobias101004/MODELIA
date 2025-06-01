"""
template_formatter.py - Updated with country list and field changes
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any
from unidecode import unidecode
from country_utils import get_country_code

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Complete list of countries with ISO codes for dropdown
COUNTRY_CODES = [
    {"name": "AFGANISTÁN - AF", "code": "AF"},
    {"name": "ALBANIA - AL", "code": "AL"},
    {"name": "ALEMANIA - DE", "code": "DE"},
    {"name": "ANDORRA - AD", "code": "AD"},
    {"name": "ANGOLA - AO", "code": "AO"},
    {"name": "ANGUILA - AI", "code": "AI"},
    {"name": "ANTÁRTIDA - AQ", "code": "AQ"},
    {"name": "ANTIGUA Y BARBUDA - AG", "code": "AG"},
    {"name": "ARABIA SAUDÍ - SA", "code": "SA"},
    {"name": "ARGELIA - DZ", "code": "DZ"},
    {"name": "ARGENTINA - AR", "code": "AR"},
    {"name": "ARMENIA - AM", "code": "AM"},
    {"name": "ARUBA - AW", "code": "AW"},
    {"name": "AUSTRALIA - AU", "code": "AU"},
    {"name": "AUSTRIA - AT", "code": "AT"},
    {"name": "AZERBAIYÁN - AZ", "code": "AZ"},
    {"name": "BAHAMAS - BS", "code": "BS"},
    {"name": "BAHRÉIN - BH", "code": "BH"},
    {"name": "BANGLADESH - BD", "code": "BD"},
    {"name": "BARBADOS - BB", "code": "BB"},
    {"name": "BÉLGICA - BE", "code": "BE"},
    {"name": "BELICE - BZ", "code": "BZ"},
    {"name": "BENÍN - BJ", "code": "BJ"},
    {"name": "BERMUDAS - BM", "code": "BM"},
    {"name": "BIELORRUSIA - BY", "code": "BY"},
    {"name": "BOLIVIA - BO", "code": "BO"},
    {"name": "BOSNIA-HERZEGOVINA - BA", "code": "BA"},
    {"name": "BOTSUANA - BW", "code": "BW"},
    {"name": "BRASIL - BR", "code": "BR"},
    {"name": "BRUNÉI - BN", "code": "BN"},
    {"name": "BULGARIA - BG", "code": "BG"},
    {"name": "BURKINA FASO - BF", "code": "BF"},
    {"name": "BURUNDI - BI", "code": "BI"},
    {"name": "BUTÁN - BT", "code": "BT"},
    {"name": "CABO VERDE - CV", "code": "CV"},
    {"name": "CAIMÁN, ISLAS - KY", "code": "KY"},
    {"name": "CAMBOYA - KH", "code": "KH"},
    {"name": "CAMERÚN - CM", "code": "CM"},
    {"name": "CANADÁ - CA", "code": "CA"},
    {"name": "CHAD - TD", "code": "TD"},
    {"name": "CHECA, REPÚBLICA - CZ", "code": "CZ"},
    {"name": "CHILE - CL", "code": "CL"},
    {"name": "CHINA - CN", "code": "CN"},
    {"name": "CHIPRE - CY", "code": "CY"},
    {"name": "COLOMBIA - CO", "code": "CO"},
    {"name": "COMORAS - KM", "code": "KM"},
    {"name": "CONGO - CG", "code": "CG"},
    {"name": "CONGO, REP. DEMOCRÁTICA - CD", "code": "CD"},
    {"name": "COREA DEL NORTE - KP", "code": "KP"},
    {"name": "COREA DEL SUR - KR", "code": "KR"},
    {"name": "COSTA DE MARFIL - CI", "code": "CI"},
    {"name": "COSTA RICA - CR", "code": "CR"},
    {"name": "CROACIA - HR", "code": "HR"},
    {"name": "CUBA - CU", "code": "CU"},
    {"name": "DINAMARCA - DK", "code": "DK"},
    {"name": "DOMINICA - DM", "code": "DM"},
    {"name": "DOMINICANA, REPÚBLICA - DO", "code": "DO"},
    {"name": "ECUADOR - EC", "code": "EC"},
    {"name": "EGIPTO - EG", "code": "EG"},
    {"name": "EMIRATOS ÁRABES UNIDOS - AE", "code": "AE"},
    {"name": "ERITREA - ER", "code": "ER"},
    {"name": "ESLOVAQUIA - SK", "code": "SK"},
    {"name": "ESLOVENIA - SI", "code": "SI"},
    {"name": "ESPAÑA - ES", "code": "ES"},
    {"name": "ESTADOS UNIDOS - US", "code": "US"},
    {"name": "ESTONIA - EE", "code": "EE"},
    {"name": "ETIOPÍA - ET", "code": "ET"},
    {"name": "FEROE, ISLAS - FO", "code": "FO"},
    {"name": "FILIPINAS - PH", "code": "PH"},
    {"name": "FINLANDIA - FI", "code": "FI"},
    {"name": "FIYI - FJ", "code": "FJ"},
    {"name": "FRANCIA - FR", "code": "FR"},
    {"name": "GABÓN - GA", "code": "GA"},
    {"name": "GAMBIA - GM", "code": "GM"},
    {"name": "GEORGIA - GE", "code": "GE"},
    {"name": "GHANA - GH", "code": "GH"},
    {"name": "GIBRALTAR - GI", "code": "GI"},
    {"name": "GRANADA - GD", "code": "GD"},
    {"name": "GRECIA - GR", "code": "GR"},
    {"name": "GROENLANDIA - GL", "code": "GL"},
    {"name": "GUATEMALA - GT", "code": "GT"},
    {"name": "GUINEA - GN", "code": "GN"},
    {"name": "GUINEA ECUATORIAL - GQ", "code": "GQ"},
    {"name": "GUINEA-BISSAU - GW", "code": "GW"},
    {"name": "GUYANA - GY", "code": "GY"},
    {"name": "HAITÍ - HT", "code": "HT"},
    {"name": "HONDURAS - HN", "code": "HN"},
    {"name": "HONG-KONG - HK", "code": "HK"},
    {"name": "HUNGRÍA - HU", "code": "HU"},
    {"name": "INDIA - IN", "code": "IN"},
    {"name": "INDONESIA - ID", "code": "ID"},
    {"name": "IRÁN - IR", "code": "IR"},
    {"name": "IRAQ - IQ", "code": "IQ"},
    {"name": "IRLANDA - IE", "code": "IE"},
    {"name": "ISLANDIA - IS", "code": "IS"},
    {"name": "ISRAEL - IL", "code": "IL"},
    {"name": "ITALIA - IT", "code": "IT"},
    {"name": "JAMAICA - JM", "code": "JM"},
    {"name": "JAPÓN - JP", "code": "JP"},
    {"name": "JORDANIA - JO", "code": "JO"},
    {"name": "KAZAJSTÁN - KZ", "code": "KZ"},
    {"name": "KENIA - KE", "code": "KE"},
    {"name": "KIRGUISTÁN - KG", "code": "KG"},
    {"name": "KIRIBATI - KI", "code": "KI"},
    {"name": "KUWAIT - KW", "code": "KW"},
    {"name": "LAOS - LA", "code": "LA"},
    {"name": "LESOTHO - LS", "code": "LS"},
    {"name": "LETONIA - LV", "code": "LV"},
    {"name": "LÍBANO - LB", "code": "LB"},
    {"name": "LIBERIA - LR", "code": "LR"},
    {"name": "LIBIA - LY", "code": "LY"},
    {"name": "LIECHTENSTEIN - LI", "code": "LI"},
    {"name": "LITUANIA - LT", "code": "LT"},
    {"name": "LUXEMBURGO - LU", "code": "LU"},
    {"name": "MACAO - MO", "code": "MO"},
    {"name": "MACEDONIA - MK", "code": "MK"},
    {"name": "MADAGASCAR - MG", "code": "MG"},
    {"name": "MALASIA - MY", "code": "MY"},
    {"name": "MALAWI - MW", "code": "MW"},
    {"name": "MALDIVAS - MV", "code": "MV"},
    {"name": "MALI - ML", "code": "ML"},
    {"name": "MALTA - MT", "code": "MT"},
    {"name": "MARRUECOS - MA", "code": "MA"},
    {"name": "MAURICIO - MU", "code": "MU"},
    {"name": "MAURITANIA - MR", "code": "MR"},
    {"name": "MÉXICO - MX", "code": "MX"},
    {"name": "MOLDAVIA - MD", "code": "MD"},
    {"name": "MÓNACO - MC", "code": "MC"},
    {"name": "MONGOLIA - MN", "code": "MN"},
    {"name": "MONTENEGRO - ME", "code": "ME"},
    {"name": "MOZAMBIQUE - MZ", "code": "MZ"},
    {"name": "MYANMAR - MM", "code": "MM"},
    {"name": "NAMIBIA - NA", "code": "NA"},
    {"name": "NAURU - NR", "code": "NR"},
    {"name": "NEPAL - NP", "code": "NP"},
    {"name": "NICARAGUA - NI", "code": "NI"},
    {"name": "NÍGER - NE", "code": "NE"},
    {"name": "NIGERIA - NG", "code": "NG"},
    {"name": "NORUEGA - NO", "code": "NO"},
    {"name": "NUEVA ZELANDA - NZ", "code": "NZ"},
    {"name": "OMÁN - OM", "code": "OM"},
    {"name": "PAÍSES BAJOS - NL", "code": "NL"},
    {"name": "PAKISTÁN - PK", "code": "PK"},
    {"name": "PANAMÁ - PA", "code": "PA"},
    {"name": "PAPÚA NUEVA GUINEA - PG", "code": "PG"},
    {"name": "PARAGUAY - PY", "code": "PY"},
    {"name": "PERÚ - PE", "code": "PE"},
    {"name": "POLONIA - PL", "code": "PL"},
    {"name": "PORTUGAL - PT", "code": "PT"},
    {"name": "PUERTO RICO - PR", "code": "PR"},
    {"name": "QATAR - QA", "code": "QA"},
    {"name": "REINO UNIDO - GB", "code": "GB"},
    {"name": "RUANDA - RW", "code": "RW"},
    {"name": "RUMANÍA - RO", "code": "RO"},
    {"name": "RUSIA - RU", "code": "RU"},
    {"name": "SALOMÓN, ISLAS - SB", "code": "SB"},
    {"name": "SALVADOR, EL - SV", "code": "SV"},
    {"name": "SAMOA - WS", "code": "WS"},
    {"name": "SAN MARINO - SM", "code": "SM"},
    {"name": "SANTA LUCÍA - LC", "code": "LC"},
    {"name": "SANTO TOMÉ Y PRÍNCIPE - ST", "code": "ST"},
    {"name": "SENEGAL - SN", "code": "SN"},
    {"name": "SERBIA - RS", "code": "RS"},
    {"name": "SEYCHELLES - SC", "code": "SC"},
    {"name": "SIERRA LEONA - SL", "code": "SL"},
    {"name": "SINGAPUR - SG", "code": "SG"},
    {"name": "SIRIA - SY", "code": "SY"},
    {"name": "SOMALIA - SO", "code": "SO"},
    {"name": "SRI LANKA - LK", "code": "LK"},
    {"name": "SUDÁFRICA - ZA", "code": "ZA"},
    {"name": "SUDÁN - SD", "code": "SD"},
    {"name": "SUDÁN DEL SUR - SS", "code": "SS"},
    {"name": "SUECIA - SE", "code": "SE"},
    {"name": "SUIZA - CH", "code": "CH"},
    {"name": "SURINAM - SR", "code": "SR"},
    {"name": "TAILANDIA - TH", "code": "TH"},
    {"name": "TAIWÁN - TW", "code": "TW"},
    {"name": "TANZANIA - TZ", "code": "TZ"},
    {"name": "TAYIKISTÁN - TJ", "code": "TJ"},
    {"name": "TIMOR LESTE - TL", "code": "TL"},
    {"name": "TOGO - TG", "code": "TG"},
    {"name": "TONGA - TO", "code": "TO"},
    {"name": "TRINIDAD Y TOBAGO - TT", "code": "TT"},
    {"name": "TÚNEZ - TN", "code": "TN"},
    {"name": "TURKMENISTÁN - TM", "code": "TM"},
    {"name": "TURQUÍA - TR", "code": "TR"},
    {"name": "TUVALU - TV", "code": "TV"},
    {"name": "UCRANIA - UA", "code": "UA"},
    {"name": "UGANDA - UG", "code": "UG"},
    {"name": "URUGUAY - UY", "code": "UY"},
    {"name": "UZBEKISTÁN - UZ", "code": "UZ"},
    {"name": "VANUATU - VU", "code": "VU"},
    {"name": "VATICANO - VA", "code": "VA"},
    {"name": "VENEZUELA - VE", "code": "VE"},
    {"name": "VIETNAM - VN", "code": "VN"},
    {"name": "YEMEN - YE", "code": "YE"},
    {"name": "YIBUTI - DJ", "code": "DJ"},
    {"name": "ZAMBIA - ZM", "code": "ZM"},
    {"name": "ZIMBABWE - ZW", "code": "ZW"}
]

# Updated field definitions with changed requirements and labels
REQUIRED_FIELDS = {
    "comprador": [
        {"name": "nombre_completo", "label": "Nombre completo", "required": True},
        {"name": "tipo_documento", "label": "Tipo documento (F, E, X)", "required": True, "type": "select", "options": [
            {"value": "F", "label": "F - Persona física española"},
            {"value": "E", "label": "E - Extranjero con NIE"},
            {"value": "X", "label": "X - Extranjero sin NIE (pasaporte)"}
        ]},
        {"name": "nif_nie", "label": "NIF/NIE/Pasaporte", "required": True},
        {"name": "direccion", "label": "Dirección", "required": True},
        {"name": "direccion_complemento", "label": "Complemento dirección", "required": False},
        {"name": "codigo_postal", "label": "Código postal", "required": True},
        {"name": "municipio", "label": "Municipio/Ciudad", "required": False},
        {"name": "provincia", "label": "Provincia", "required": False},
        {"name": "pais", "label": "País", "required": True, "type": "select", "options": COUNTRY_CODES}
    ],
    "vendedor": [
        {"name": "nombre_completo", "label": "Nombre completo", "required": True},
        {"name": "tipo_documento", "label": "Tipo documento (F, J, E, X)", "required": True, "type": "select", "options": [
            {"value": "F", "label": "F - Persona física española"},
            {"value": "J", "label": "J - Persona jurídica/empresa"},
            {"value": "E", "label": "E - Extranjero con NIE"},
            {"value": "X", "label": "X - Extranjero sin NIE (pasaporte)"}
        ]},
        {"name": "nif_nie", "label": "NIF/NIE/Pasaporte", "required": True},
        {"name": "direccion", "label": "Dirección", "required": True},
        {"name": "direccion_complemento", "label": "Complemento dirección", "required": False},
        {"name": "codigo_postal", "label": "Código postal", "required": True},
        {"name": "municipio", "label": "Municipio/Ciudad", "required": False},
        {"name": "provincia", "label": "Provincia", "required": False},
        {"name": "pais", "label": "País", "required": True, "type": "select", "options": COUNTRY_CODES}
    ],
    "inmueble": [
        {"name": "direccion", "label": "Dirección", "required": True},
        {"name": "referencia_catastral", "label": "Referencia catastral", "required": True},
        {"name": "codigo_postal", "label": "Código postal", "required": False},
        {"name": "municipio", "label": "Municipio/Ciudad", "required": False},
        {"name": "provincia", "label": "Provincia", "required": False},
    ],
    "operacion": [
        {"name": "fecha_documento", "label": "Fecha (DD/MM/AAAA)", "required": True},
        {"name": "importe", "label": "Importe (euros)", "required": True},
        {"name": "retencion", "label": "Retención (euros)", "required": False},
        {"name": "porcentaje_adquirido", "label": "Porcentaje adquirido", "required": False},
        {"name": "tipo_iva", "label": "Tipo de IVA (%)", "required": False},
        {"name": "tipo_itp", "label": "Tipo de ITP (%)", "required": False},
        {"name": "codigo_notario", "label": "Código notario", "required": False},
        {"name": "numero_protocolo", "label": "Número protocolo", "required": True},
    ],
    "presentante": [
        {"name": "nombre_completo", "label": "Nombre completo", "required": False},
        {"name": "tipo_documento", "label": "Tipo documento", "required": False},
        {"name": "nif_nie", "label": "NIF/NIE", "required": False},
    ],
    "representante_fiscal": [
        {"name": "nombre_completo", "label": "Nombre completo", "required": False},
        {"name": "tipo_documento", "label": "Tipo documento", "required": False},
        {"name": "nif_nie", "label": "NIF/NIE", "required": False},
        {"name": "direccion", "label": "Dirección", "required": False},
        {"name": "codigo_postal", "label": "Código postal", "required": False},
        {"name": "municipio", "label": "Municipio/Ciudad", "required": False},
        {"name": "pais", "label": "País", "required": False, "type": "select", "options": COUNTRY_CODES},
    ]
}

# Helper functions for formatting text and values
def format_text(text: str, length: int, alignment: str = 'left') -> str:
    """Format text to specific length with specified alignment"""
    if text is None:
        text = ""
    
    # Convert to string and remove accents
    text = unidecode(str(text).strip())
    
    # Handle alignment
    if alignment == 'left':
        return text.ljust(length)[:length]
    elif alignment == 'right':
        return text.rjust(length)[:length]
    elif alignment == 'center':
        return text.center(length)[:length]
    else:
        return text.ljust(length)[:length]

def format_number(number: Any, length: int, decimals: int = 0) -> str:
    """Format number to specific length with specified decimals"""
    if number is None or number == "":
        number = 0
    
    try:
        # Convert to float
        value = float(str(number).replace(',', '.'))
        
        # Format with specified decimals
        if decimals > 0:
            formatted = f"{value:.{decimals}f}"
        else:
            formatted = f"{int(value)}"
        
        # Remove decimal point if no decimals
        if decimals == 0:
            formatted = formatted.split('.')[0]
        
        # Ensure correct length by padding with zeros
        return formatted.zfill(length)[:length]
    except (ValueError, TypeError):
        # In case of error, return zeros
        if decimals > 0:
            return "0" * (length - decimals - 1) + "." + "0" * decimals
        else:
            return "0" * length

def format_date(date_str: str) -> str:
    """Format date string to DDMMYYYY format"""
    if not date_str:
        # Default to current date if none provided
        now = datetime.now()
        return now.strftime("%d%m%Y")
    
    # Remove any non-alphanumeric characters
    date_str = re.sub(r'[^\w\s]', '/', date_str)
    
    # Try different date formats
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%d%m%Y")
        except ValueError:
            continue
    
    # If no format matches, return current date
    now = datetime.now()
    logger.warning(f"Could not parse date: {date_str}, using current date instead")
    return now.strftime("%d%m%Y")

def clean_nif(nif: str) -> str:
    """Clean and format NIF/NIE number"""
    if not nif:
        return ""
    
    # Remove spaces and special characters
    cleaned = re.sub(r'[^A-Z0-9]', '', nif.upper())
    
    # Ensure it has at least 9 characters
    if len(cleaned) < 9:
        cleaned = cleaned.rjust(9, '0')
    
    return cleaned[:9]

def generate_211_file(data: Dict[str, Any]) -> str:
    """Generate 211 file content from structured data"""
    logger.info("Starting 211 file generation")
    
    # Ensure all required sections exist
    for section in ["comprador", "vendedor", "inmueble", "operacion", "presentante", "representante_fiscal"]:
        if section not in data:
            data[section] = {}
            logger.warning(f"Missing section {section} in data, using empty defaults")
    
    # Extract sections for easier access
    comprador = data.get("comprador", {})
    vendedor = data.get("vendedor", {})
    inmueble = data.get("inmueble", {})
    operacion = data.get("operacion", {})
    presentante = data.get("presentante", {})
    representante_fiscal = data.get("representante_fiscal", {})
    
    # Apply defaults for required values
    if 'porcentaje_adquirido' not in operacion or not operacion['porcentaje_adquirido']:
        operacion['porcentaje_adquirido'] = 100
        
    if 'tipo_iva' not in operacion or not operacion['tipo_iva']:
        operacion['tipo_iva'] = 0
        
    if 'tipo_itp' not in operacion or not operacion['tipo_itp']:
        operacion['tipo_itp'] = 7
    
    # Handle retention calculation if needed
    if ('retencion' not in operacion or not operacion['retencion']) and 'importe' in operacion and operacion['importe']:
        # Check if seller is non-resident in Spain
        is_seller_non_resident = False
        
        if 'pais' in vendedor and vendedor['pais'] and vendedor['pais'] != 'ESPAÑA' and vendedor['pais'] != 'ES':
            is_seller_non_resident = True
            
        if is_seller_non_resident:
            # Calculate 3% retention for non-resident sellers
            try:
                importe = float(str(operacion['importe']).replace(',', '.'))
                operacion['retencion'] = round(importe * 0.03, 2)
                logger.info(f"Calculated retention for non-resident seller: {operacion['retencion']}")
            except (ValueError, TypeError):
                logger.warning("Could not calculate retention due to invalid importe value")
    
    # Format date
    fecha_formatted = format_date(operacion.get('fecha_documento', ''))
    
    # Get country codes
    comprador_pais_code = "ES"  # Default to Spain
    vendedor_pais_code = "ES"  # Default to Spain
    
    if 'pais' in comprador and comprador['pais']:
        comprador_pais_code = get_country_code(comprador['pais'])
        
    if 'pais' in vendedor and vendedor['pais']:
        vendedor_pais_code = get_country_code(vendedor['pais'])
    
    # Start building 211 file content
    content = []
    
    # Header record - type 1
    header = "1"  # Record type
    header += format_text("211", 3)  # Form code
    header += format_text("05", 2)  # Delegation code (default)
    header += format_text("B", 1)  # Administration code (default)
    header += format_date(operacion.get('fecha_documento', ''))  # Date DDMMYYYY
    header += format_text("", 13)  # Reserved space
    header += format_text("", 40)  # Reserved space
    header += format_text("", 88)  # Reserved space
    
    content.append(header)
    
    # Property details - type 2
    property_record = "2"  # Record type
    property_record += format_text(inmueble.get('referencia_catastral', ''), 20)  # Cadastral reference
    property_record += format_text(inmueble.get('direccion', ''), 40)  # Address
    property_record += format_text(inmueble.get('codigo_postal', ''), 5)  # Postal code
    property_record += format_text(inmueble.get('municipio', ''), 25)  # Municipality
    property_record += format_text(inmueble.get('provincia', ''), 25)  # Province
    property_record += format_text("", 31)  # Reserved space
    
    content.append(property_record)
    
    # Buyer details - type 3
    buyer_record = "3"  # Record type
    buyer_record += format_text(comprador.get('tipo_documento', 'F'), 1)  # Document type (F, E, X)
    buyer_record += format_text(clean_nif(comprador.get('nif_nie', '')), 9)  # NIF/NIE
    buyer_record += format_text(comprador.get('nombre_completo', ''), 40)  # Full name
    buyer_record += format_text(comprador.get('direccion', ''), 40)  # Address
    buyer_record += format_text(comprador.get('codigo_postal', ''), 5)  # Postal code
    buyer_record += format_text(comprador.get('municipio', ''), 25)  # Municipality
    buyer_record += format_text(comprador.get('provincia', ''), 25)  # Province
    buyer_record += format_text(comprador_pais_code, 2)  # Country code
    
    content.append(buyer_record)
    
    # Seller details - type 4
    seller_record = "4"  # Record type
    seller_record += format_text(vendedor.get('tipo_documento', 'F'), 1)  # Document type (F, J, E, X)
    seller_record += format_text(clean_nif(vendedor.get('nif_nie', '')), 9)  # NIF/NIE
    seller_record += format_text(vendedor.get('nombre_completo', ''), 40)  # Full name
    seller_record += format_text(vendedor.get('direccion', ''), 40)  # Address
    seller_record += format_text(vendedor.get('codigo_postal', ''), 5)  # Postal code
    seller_record += format_text(vendedor.get('municipio', ''), 25)  # Municipality
    seller_record += format_text(vendedor.get('provincia', ''), 25)  # Province
    seller_record += format_text(vendedor_pais_code, 2)  # Country code
    
    content.append(seller_record)
    
    # Transaction details - type 5
    transaction_record = "5"  # Record type
    
    # Format numbers for transaction
    importe = format_number(operacion.get('importe', 0), 11, 0)
    retencion = format_number(operacion.get('retencion', 0), 11, 0)
    porcentaje = format_number(operacion.get('porcentaje_adquirido', 100), 3, 0)
    
    transaction_record += format_text(operacion.get('numero_protocolo', ''), 10)  # Protocol number
    transaction_record += format_text(operacion.get('codigo_notario', ''), 5)  # Notary code
    transaction_record += importe  # Amount in euros (integer)
    transaction_record += retencion  # Retention amount (integer)
    transaction_record += porcentaje  # Percentage acquired (integer, default 100)
    transaction_record += format_number(operacion.get('tipo_iva', 0), 2, 0)  # VAT rate (integer)
    transaction_record += format_number(operacion.get('tipo_itp', 7), 2, 0)  # ITP rate (integer)
    transaction_record += format_text("", 96)  # Reserved space
    
    content.append(transaction_record)
    
    # Fiscal representative (if exists) - type 6
    if representante_fiscal and representante_fiscal.get('nombre_completo'):
        rep_pais_code = "ES"  # Default to Spain
        if 'pais' in representante_fiscal and representante_fiscal['pais']:
            rep_pais_code = get_country_code(representante_fiscal['pais'])
            
        rep_record = "6"  # Record type
        rep_record += format_text(representante_fiscal.get('tipo_documento', 'F'), 1)  # Document type
        rep_record += format_text(clean_nif(representante_fiscal.get('nif_nie', '')), 9)  # NIF/NIE
        rep_record += format_text(representante_fiscal.get('nombre_completo', ''), 40)  # Full name
        rep_record += format_text(representante_fiscal.get('direccion', ''), 40)  # Address
        rep_record += format_text(representante_fiscal.get('codigo_postal', ''), 5)  # Postal code
        rep_record += format_text(representante_fiscal.get('municipio', ''), 25)  # Municipality
        rep_record += format_text("", 25)  # Province (not always required)
        rep_record += format_text(rep_pais_code, 2)  # Country code
        
        content.append(rep_record)
    
    # Presenter details (if exists) - type 7
    if presentante and presentante.get('nombre_completo'):
        presenter_record = "7"  # Record type
        presenter_record += format_text(presentante.get('tipo_documento', 'F'), 1)  # Document type
        presenter_record += format_text(clean_nif(presentante.get('nif_nie', '')), 9)  # NIF/NIE
        presenter_record += format_text(presentante.get('nombre_completo', ''), 40)  # Full name
        presenter_record += format_text("", 97)  # Reserved space
        
        content.append(presenter_record)
    
    # Join all records with newlines
    file_content = "\n".join(content)
    
    logger.info(f"Generated 211 file with {len(content)} records")
    
    return file_content

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
