"""
property_sync.py
Fetches the Apinmo XML feed, parses properties, and stores them in Supabase.
"""

import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from supabase import create_client

SUPABASE_URL = "https://pntipdspiivffvxfyshg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBudGlwZHNwaWl2ZmZ2eGZ5c2hnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3OTg5NzYsImV4cCI6MjA4NzM3NDk3Nn0.2n0YukribUPyIcaWcercFEzpStq-VhQTzFpE69Pnv2M"

_client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    child = el.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _float(el, tag: str) -> float:
    val = _text(el, tag)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _int(el, tag: str) -> int:
    val = _text(el, tag)
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _extract_features(el) -> list[str]:
    features = []
    for field, label in FEATURE_MAP.items():
        if _text(el, field) == "1":
            features.append(label)
    return features


def _extract_photos(el) -> list[str]:
    photos = []
    for i in range(1, 38):
        url = _text(el, f"foto{i}")
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
        "title_fr": _text(el, "titulo4"),
        "title_nl": _text(el, "titulo5"),
        "title_no": _text(el, "titulo6"),
        "title_sv": _text(el, "titulo9"),
        "description_es": _text(el, "descrip1"),
        "description_en": _text(el, "descrip2"),
        "description_de": _text(el, "descrip3"),
        "description_fr": _text(el, "descrip4"),
        "description_nl": _text(el, "descrip5"),
        "description_no": _text(el, "descrip6"),
        "description_sv": _text(el, "descrip9"),
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
        "synced_at": datetime.now().isoformat(),
    }


def sync_from_url(url: str = DEFAULT_XML_URL) -> dict:
    """Fetch XML from URL, parse properties, replace all in Supabase."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return _sync_xml_content(response.content, source=url)


def _sync_xml_content(xml_bytes: bytes, source: str) -> dict:
    """Parse XML and replace all properties in Supabase."""
    root = ET.fromstring(xml_bytes)
    properties = []
    for prop_el in root.findall("propiedad"):
        prop = parse_property(prop_el)
        if prop["active"] and prop["ref"]:
            properties.append(prop)

    # Delete all existing properties
    _client.table("properties").delete().neq("ref", "").execute()

    # Insert all new properties in batches of 50
    for i in range(0, len(properties), 50):
        batch = properties[i:i + 50]
        _client.table("properties").insert(batch).execute()

    return {
        "last_sync": datetime.now().isoformat(),
        "source": source,
        "total_properties": len(properties),
    }


def load_properties() -> list[dict]:
    """Load all active properties from Supabase."""
    result = _client.table("properties").select("*").eq("active", True).execute()
    return result.data


def load_sync_meta() -> dict | None:
    """Get sync status from the most recently synced property."""
    result = (
        _client.table("properties")
        .select("synced_at")
        .order("synced_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        count = _client.table("properties").select("ref", count="exact").execute()
        return {
            "last_sync": result.data[0]["synced_at"],
            "total_properties": count.count,
        }
    return None


def search_properties(
    operation: str = "",
    property_type: str = "",
    location: str = "",
    bedrooms_min: int = 0,
    price_max: float = 0,
    price_min: float = 0,
    features: list[str] | None = None,
) -> list[dict]:
    """Search properties in Supabase with filters."""
    query = _client.table("properties").select("*").eq("active", True)

    if operation:
        query = query.eq("operation", operation.lower())

    if bedrooms_min:
        query = query.gte("bedrooms", bedrooms_min)

    if price_max:
        query = query.lte("price", price_max)

    if price_min:
        query = query.gte("price", price_min)

    result = query.execute()
    properties = result.data

    # Client-side filtering for fuzzy matches (type, location, features)
    filtered = []
    for p in properties:
        if property_type:
            pt = property_type.lower()
            type_lower = (p.get("type") or "").lower()
            title_lower = (p.get("title_es") or "").lower()
            if pt not in type_lower and pt not in title_lower:
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
                    if pt in alias_list and any(a in type_lower for a in alias_list):
                        matched = True
                        break
                if not matched:
                    continue

        if location:
            loc = location.lower()
            if (loc not in (p.get("city") or "").lower()
                    and loc not in (p.get("zone") or "").lower()
                    and loc not in (p.get("province") or "").lower()):
                continue

        if features:
            p_features = [f.lower() for f in (p.get("features") or [])]
            if not all(any(req.lower() in pf for pf in p_features) for req in features):
                continue

        filtered.append(p)

    return filtered
