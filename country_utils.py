"""
country_utils.py - Utilities for country code handling and mapping
"""

import re
from typing import Dict, Optional
import logging
from unidecode import unidecode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Extended country code mappings with common variations and misspellings
COUNTRY_CODES_EXTENDED = {
    # Original mappings from codpaises.pdf
    "ESPAÑA": "ES",
    "ALEMANIA": "DE",
    "FRANCIA": "FR",
    "ITALIA": "IT",
    "REINO UNIDO": "GB",
    "PORTUGAL": "PT",
    "PAÍSES BAJOS": "NL",
    "BÉLGICA": "BE",
    "ESTADOS UNIDOS": "US",
    "SUIZA": "CH",
    "REPÚBLICA CHECA": "CZ",
    
    # Common variations and alternate names
    "ESPANA": "ES",
    "SPAIN": "ES",
    "GERMANY": "DE",
    "DEUTSCHLAND": "DE",
    "FRANCE": "FR",
    "ITALY": "IT",
    "ITALIA": "IT",
    "UK": "GB",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "ENGLAND": "GB",
    "SCOTLAND": "GB",
    "WALES": "GB",
    "NORTHERN IRELAND": "GB",
    "HOLLAND": "NL",
    "NETHERLANDS": "NL",
    "HOLANDA": "NL",
    "PAISES BAJOS": "NL",
    "BELGIUM": "BE",
    "BELGICA": "BE",
    "BELGIQUE": "BE",
    "USA": "US",
    "UNITED STATES": "US",
    "ESTADOS UNIDOS DE AMERICA": "US",
    "SWITZERLAND": "CH",
    "SUISSE": "CH",
    "CZECH REPUBLIC": "CZ",
    "CZECHIA": "CZ",
    "REPUBLICA CHECA": "CZ",
    "CHECA": "CZ",
    
    # Add other country variations here...
    "AUSTRIA": "AT",
    "OSTERREICH": "AT",
    "POLAND": "PL",
    "POLONIA": "PL",
    "SWEDEN": "SE",
    "SUECIA": "SE",
    "NORWAY": "NO",
    "NORUEGA": "NO",
    "DENMARK": "DK",
    "DINAMARCA": "DK",
    "FINLAND": "FI",
    "FINLANDIA": "FI",
    "IRELAND": "IE",
    "IRLANDA": "IE",
    "RUSSIA": "RU",
    "RUSIA": "RU",
    "CANADA": "CA",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
    "JAPAN": "JP",
    "JAPON": "JP",
    "CHINA": "CN",
    "MOROCCO": "MA",
    "MARRUECOS": "MA",
    "MEXICO": "MX",
    "MÉXICO": "MX",
}

def normalize_country_name(country_name: str) -> str:
    """Normalize country name by removing accents, converting to uppercase, etc."""
    if not country_name:
        return ""
    
    # Convert to uppercase and normalize accents
    normalized = unidecode(country_name.upper().strip())
    
    # Remove special characters except spaces
    normalized = re.sub(r'[^A-Z0-9 ]', '', normalized)
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized

def get_country_code(country_name: str) -> str:
    """Get ISO country code from country name using an extended mapping system"""
    if not country_name:
        return 'ES'  # Default to Spain if no country is provided
    
    # Normalize country name
    normalized_name = normalize_country_name(country_name)
    
    # Direct lookup in extended dictionary
    if normalized_name in COUNTRY_CODES_EXTENDED:
        return COUNTRY_CODES_EXTENDED[normalized_name]
    
    # Try to find partial matches (if the country name contains the key or vice versa)
    for key, value in COUNTRY_CODES_EXTENDED.items():
        if key in normalized_name or normalized_name in key:
            logger.info(f"Partial country match: '{normalized_name}' matched with '{key}' -> {value}")
            return value
    
    # If we still don't have a match, try word by word matching
    words = normalized_name.split()
    if len(words) > 1:
        for word in words:
            if len(word) > 3:  # Only consider words with more than 3 characters
                for key, value in COUNTRY_CODES_EXTENDED.items():
                    if word in key.split():
                        logger.info(f"Word match: '{word}' in '{normalized_name}' matched with '{key}' -> {value}")
                        return value
    
    # Log when we can't find a match
    logger.warning(f"Could not find country code for: '{country_name}', defaulting to ES")
    
    # Default to Spain if not found
    return 'ES'

def validate_country_mapping():
    """Validate that all country codes in the mapping are correct"""
    valid_codes = set()
    with open("codpaises.pdf.txt", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2 and len(parts[0]) == 2 and parts[0].isalpha():
                valid_codes.add(parts[0])
    
    for country, code in COUNTRY_CODES_EXTENDED.items():
        if code not in valid_codes:
            logger.warning(f"Invalid country code: {code} for country {country}")

if __name__ == "__main__":
    # Test the country code mapping with some examples
    test_countries = [
        "España",
        "ALEMANIA",
        "República Checa",
        "UK",
        "Estados Unidos de América",
        "Holanda",
        "Unknown Country"
    ]
    
    for country in test_countries:
        code = get_country_code(country)
        print(f"{country} -> {code}")
