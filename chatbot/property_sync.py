"""
property_sync.py
Fetches the Apinmo XML feed, parses properties, and caches them as JSON.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent / "data"
PROPERTIES_FILE = DATA_DIR / "properties.json"
SYNC_META_FILE = DATA_DIR / "sync_meta.json"

DEFAULT_XML_URL = "https://procesos.apinmo.com/xml/v2/L5iw2DpX/2934-web.xml"

# Boolean feature fields → human-readable labels
FEATURE_MAP = {
    "aire_con": "Aire acondicionado",
    "ascensor": "Ascensor",
    "balcon": "Balcón",
    "jardin": "Jardín",
    "barbacoa": "Barbacoa",
    "calefaccion": "Calefacción",
    "chimenea": "Chimenea",
    "gimnasio": "Gimnasio",
    "piscina_com": "Piscina comunitaria",
    "piscina_prop": "Piscina privada",
    "terraza": "Terraza",
    "trastero": "Trastero",
    "parking": "Parking",
    "plaza_gara": "Garaje",
    "vistasalmar": "Vistas al mar",
    "muebles": "Amueblado",
    "solarium": "Solarium",
    "jacuzzi": "Jacuzzi",
    "sauna": "Sauna",
    "primera_line": "Primera línea",
}

OPERATION_MAP = {
    "vender": "venta",
    "alquilar": "alquiler",
    "alquiler": "alquiler",
    "venta": "venta",
}


def _text(el, tag: str) -> str:
    """Get text content of a child element, or empty string."""
    child = el.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _float(el, tag: str) -> float:
    """Get float value of a child element, or 0."""
    val = _text(el, tag)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _int(el, tag: str) -> int:
    """Get int value of a child element, or 0."""
    val = _text(el, tag)
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _extract_features(el) -> list[str]:
    """Extract human-readable feature list from boolean fields."""
    features = []
    for field, label in FEATURE_MAP.items():
        if _text(el, field) == "1":
            features.append(label)
    return features


def _extract_photos(el) -> list[str]:
    """Extract photo URLs from foto1-foto37 fields."""
    photos = []
    for i in range(1, 38):
        tag = f"foto{i}"
        url = _text(el, tag)
        if url and url.startswith("http"):
            photos.append(url)
    return photos


def parse_property(el) -> dict:
    """Parse a single <propiedad> XML element into a clean dict."""
    operation_raw = _text(el, "accion").lower()
    operation = OPERATION_MAP.get(operation_raw, operation_raw)

    price = _float(el, "precioinmo") if operation == "venta" else _float(el, "precioalq")
    if price == 0:
        price = _float(el, "precioinmo") or _float(el, "precioalq")

    photos = _extract_photos(el)

    return {
        "ref": _text(el, "ref"),
        "title_es": _text(el, "titulo1"),
        "title_en": _text(el, "titulo2"),
        "title_de": _text(el, "titulo3"),
        "description_es": _text(el, "descrip1"),
        "description_en": _text(el, "descrip2"),
        "description_de": _text(el, "descrip3"),
        "type": _text(el, "tipo_ofer"),
        "operation": operation,
        "price": price,
        "currency": "EUR",
        "city": _text(el, "ciudad"),
        "zone": _text(el, "zona"),
        "province": _text(el, "provincia"),
        "postal_code": _text(el, "cp"),
        "bedrooms": _int(el, "habitaciones"),
        "bathrooms": _int(el, "banyos"),
        "surface_built": _float(el, "m_cons"),
        "surface_usable": _float(el, "m_uties"),
        "surface_terrace": _float(el, "m_terraza"),
        "surface_plot": _float(el, "m_parcela"),
        "floor": _int(el, "planta"),
        "orientation": _text(el, "orientacion"),
        "condition": _text(el, "conservacion"),
        "year_built": _text(el, "antiguedad"),
        "energy_rating": _text(el, "energialetra"),
        "features": _extract_features(el),
        "photos": photos,
        "photo_main": photos[0] if photos else "",
        "video": _text(el, "videos/video1") if el.find("videos/video1") is not None else "",
        "tour": _text(el, "tour"),
        "latitude": _float(el, "latitud"),
        "longitude": _float(el, "altitud"),
        "agent_name": _text(el, "agente"),
        "agent_email": _text(el, "email_agente"),
        "agent_phone": _text(el, "tlf_agente"),
        "exclusive": _text(el, "exclu") == "1",
        "active": _text(el, "estadoficha") == "1",
        "distance_to_sea": _int(el, "distmar"),
    }


def sync_from_url(url: str = DEFAULT_XML_URL) -> dict:
    """Fetch XML from URL, parse all properties, save to JSON."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return _sync_xml_content(response.content, source=url)


def sync_from_file(xml_path: str) -> dict:
    """Parse XML from a local file, save properties to JSON."""
    content = Path(xml_path).read_bytes()
    return _sync_xml_content(content, source=str(xml_path))


def _sync_xml_content(xml_bytes: bytes, source: str) -> dict:
    """Parse XML content and save properties."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    root = ET.fromstring(xml_bytes)
    properties = []
    for prop_el in root.findall("propiedad"):
        prop = parse_property(prop_el)
        if prop["active"] and prop["ref"]:
            properties.append(prop)

    with open(PROPERTIES_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)

    meta = {
        "last_sync": datetime.now().isoformat(),
        "source": source,
        "total_properties": len(properties),
    }
    with open(SYNC_META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta


def load_properties() -> list[dict]:
    """Load cached properties from JSON. Returns empty list if not synced yet."""
    if not PROPERTIES_FILE.exists():
        return []
    with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sync_meta() -> dict | None:
    """Load sync metadata (last sync time, count, etc)."""
    if not SYNC_META_FILE.exists():
        return None
    with open(SYNC_META_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def search_properties(
    operation: str = "",
    property_type: str = "",
    location: str = "",
    bedrooms_min: int = 0,
    price_max: float = 0,
    price_min: float = 0,
    features: list[str] | None = None,
) -> list[dict]:
    """Search cached properties with structured filters."""
    properties = load_properties()
    results = []

    for p in properties:
        if operation and operation.lower() not in p["operation"].lower():
            continue

        if property_type:
            pt = property_type.lower()
            if (pt not in p["type"].lower()
                    and pt not in p["title_es"].lower()
                    and pt not in p["title_en"].lower()):
                # Common aliases
                aliases = {
                    "apartamento": ["apartamento", "piso", "estudio", "apartment", "flat"],
                    "apartment": ["apartamento", "piso", "estudio", "apartment", "flat"],
                    "piso": ["apartamento", "piso", "apartment", "flat"],
                    "casa": ["casa", "chalet", "villa", "house", "duplex", "dúplex", "adosado"],
                    "house": ["casa", "chalet", "villa", "house", "duplex", "dúplex", "adosado"],
                    "villa": ["villa", "chalet"],
                    "duplex": ["dúplex", "duplex"],
                    "studio": ["estudio", "studio"],
                    "estudio": ["estudio", "studio"],
                }
                matched = False
                for alias_list in aliases.values():
                    if pt in alias_list:
                        if any(a in p["type"].lower() for a in alias_list):
                            matched = True
                            break
                if not matched:
                    continue

        if location:
            loc = location.lower()
            if (loc not in p["city"].lower()
                    and loc not in p["zone"].lower()
                    and loc not in p["province"].lower()):
                continue

        if bedrooms_min and p["bedrooms"] < bedrooms_min:
            continue

        if price_max and p["price"] > price_max:
            continue

        if price_min and p["price"] < price_min:
            continue

        if features:
            p_features_lower = [f.lower() for f in p["features"]]
            if not all(
                any(req.lower() in pf for pf in p_features_lower)
                for req in features
            ):
                continue

        results.append(p)

    return results
