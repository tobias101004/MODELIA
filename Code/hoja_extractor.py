"""
hoja_extractor.py
Extracts structured data from Cardenas Real Estate visit reports (hojas de visita)
using GPT-4o vision (image-based), for audit verification.

These PDFs are scanned documents (images), so we convert each page to an image
and send it to GPT-4o vision for extraction.

Supports documents in Spanish, English, and German.
"""

import base64
import json
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import fitz  # PyMuPDF
from openai import OpenAI


# ── Schema for GPT-4o function calling ──────────────────────────────────────

EXTRACT_HOJA = {
    "type": "function",
    "function": {
        "name": "extract_hoja_visita",
        "description": (
            "Extract key data from a property visit report (hoja de visita / "
            "Besichtigungsblatt) from Cardenas Real Estate agency. "
            "The document may be in Spanish, English, or German."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Name of the Cardenas agent/consultant who conducted or "
                        "created the visit. Look for: 'Creado por', 'Realizado por' "
                        "(Spanish), 'Created by', 'Made by' (English), 'Erstellt von', "
                        "'Durchgefuhrt von' (German). Also check the agent signature "
                        "at the bottom next to 'Fdo.: (Asesora Cardenas)' or similar."
                    ),
                },
                "property_ref": {
                    "type": "string",
                    "description": (
                        "Property reference code from the property details header, "
                        "e.g. 'REF: 06023-CA' or 'REF.: 06026-CA'. "
                        "Return the full code including suffix like '-CA'."
                    ),
                },
                "visit_date": {
                    "type": "string",
                    "description": (
                        "Date of the visit. Found as 'Fecha:', date colon, or "
                        "'Datum:'. Return in DD/MM/YYYY format."
                    ),
                },
                "client_name": {
                    "type": "string",
                    "description": (
                        "Client/customer name. Found as 'Nombre Cliente', "
                        "'Client\\'s Name', 'Name des Kunden'."
                    ),
                },
                "demand_number": {
                    "type": "string",
                    "description": (
                        "Demand/request number if present. May appear in "
                        "parentheses after client name like '(Demanda 12581)', "
                        "in the property title, as 'Num Demanda', or as "
                        "'N solicitud'. Return just the number without "
                        "surrounding text."
                    ),
                },
                "property_type": {
                    "type": "string",
                    "description": (
                        "Type of property (e.g. 'Apartamento', 'Villa', 'Chalet', "
                        "'Piso', 'Casa', 'Apartment', 'Wohnung'). Found in "
                        "property details section."
                    ),
                },
                "property_address": {
                    "type": "string",
                    "description": (
                        "Full address of the property. Found in property details "
                        "section, may include street, number, city, postal code."
                    ),
                },
                "property_price": {
                    "type": "string",
                    "description": (
                        "Price of the property. Found in property details section. "
                        "Return the numeric value with currency if visible "
                        "(e.g. '350000', '350.000 EUR')."
                    ),
                },
                "client_signature_present": {
                    "type": "boolean",
                    "description": (
                        "Whether the client's signature is visibly present on the "
                        "document. Look in the signatures section at the bottom, "
                        "next to 'Fdo.: (Cliente)' or similar. True if there is a "
                        "visible handwritten signature, false if the signature "
                        "area is blank."
                    ),
                },
            },
        },
    },
}

SYSTEM_HOJA = """You are an expert at reading property visit reports (hojas de visita) \
from Cardenas Real Estate agency.

These documents come in multiple languages (Spanish, English, German) but always \
follow the same template structure:
1. Header with title (PARTE VISITA: DEMANDA / REPORT AFTER VIEWING: DEMAND / \
BESICHTIGUNGSBLATT: NACHFRAGE)
2. Client info table (name, phone, appointment place / N solicitud)
3. Date and agent info (Created by / Made by)
4. Property details section with REF number, type, address, and price
5. Visit report / Control de Visitas / Besichtigungskontrolle section with signatures

Instructions:
1. Extract ONLY data clearly visible in the document image.
2. For the agent name: this is the Cardenas consultant, NOT the client. \
Look for 'Creado por', 'Created by', 'Erstellt von', 'Realizado por', \
'Made by', 'Durchgefuhrt von'.
3. For property REF: found in property details title, format like '06023-CA'.
4. For date: convert to DD/MM/YYYY format.
5. For demand number: may appear in parentheses in the client name field \
like '(Demanda 12581)', in the property title, or as 'N solicitud'. \
Just return the number.
6. For property type: extract the type (Apartamento, Villa, Chalet, Piso, etc.).
7. For property address: extract the full address from the property details.
8. For property price: extract the price value.
9. For client signature: check if there is a visible handwritten signature \
in the client signature area at the bottom of the document.
10. If a field is not found, return an empty string (or false for signature)."""


# ── PDF to images ───────────────────────────────────────────────────────────

def pdf_to_base64_images(pdf_path: Path, dpi: int = 200) -> list[str]:
    """Convert each page of a PDF to a base64-encoded PNG string."""
    pdf_path = Path(pdf_path)
    images = []
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            # Render page to pixmap at given DPI
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            b64 = base64.b64encode(png_bytes).decode("utf-8")
            images.append(b64)
    finally:
        doc.close()
    return images


# ── Extraction via GPT-4o vision ────────────────────────────────────────────

def extraer_datos_hoja(pdf_path: Path, api_key: str) -> dict:
    """Extract structured data from a hoja de visita PDF using GPT-4o vision."""
    images_b64 = pdf_to_base64_images(pdf_path)

    if not images_b64:
        raise RuntimeError("No se pudieron extraer paginas del PDF.")

    client = OpenAI(api_key=api_key)

    # Build the user message with images
    content = [
        {"type": "text", "text": "Extract the data from this property visit report (hoja de visita):"},
    ]
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high",
            },
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": SYSTEM_HOJA},
            {"role": "user", "content": content},
        ],
        tools=[EXTRACT_HOJA],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_hoja_visita"},
        },
    )

    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "extract_hoja_visita":
                return json.loads(tool_call.function.arguments)

    raise RuntimeError("GPT-4o did not return a function call for hoja extraction.")


# ── Verification ────────────────────────────────────────────────────────────

def verificar_hoja(extracted: dict, expected: dict) -> dict:
    """
    Compare extracted hoja data against expected visit data from CSV.

    Args:
        extracted: dict from GPT-4o (agent_name, property_ref, visit_date,
                   client_name, demand_number, property_type, property_address,
                   property_price, client_signature_present)
        expected:  dict with CSV data (comercial, ref_propiedad, num_demanda,
                   fecha_visita, id_seguimiento, nombre_cliente,
                   tipo_propiedad, direccion_propiedad, precio_propiedad)

    Returns:
        dict with ``match`` bool, per-field ``fields`` results, and raw
        ``extracted`` data.
    """
    results = {}
    overall_match = True

    # ── Asesor (agent) ──────────────────────────────────────────────────
    ext_agent = (extracted.get("agent_name") or "").strip()
    exp_agent = (expected.get("comercial") or "").strip()
    if exp_agent:
        agent_match = _fuzzy_name_match(ext_agent, exp_agent)
        results["asesor"] = {
            "expected": exp_agent,
            "found": ext_agent,
            "match": agent_match,
        }
        if not agent_match:
            overall_match = False

    # ── Nombre cliente ──────────────────────────────────────────────────
    ext_client = (extracted.get("client_name") or "").strip()
    exp_client = (expected.get("nombre_cliente") or "").strip()
    if exp_client:
        client_match = _fuzzy_name_match(ext_client, exp_client)
        results["nombre_cliente"] = {
            "expected": exp_client,
            "found": ext_client,
            "match": client_match,
        }
        if not client_match:
            overall_match = False

    # ── Property REF ────────────────────────────────────────────────────
    ext_ref = (extracted.get("property_ref") or "").strip().upper().replace(" ", "")
    exp_ref = (expected.get("ref_propiedad") or "").strip().upper().replace(" ", "")
    if exp_ref:
        ref_match = (
            ext_ref == exp_ref
            or ext_ref.startswith(exp_ref)
            or exp_ref.startswith(ext_ref)
            or exp_ref in ext_ref
            or ext_ref in exp_ref
        )
        results["ref_propiedad"] = {
            "expected": expected.get("ref_propiedad", ""),
            "found": extracted.get("property_ref", ""),
            "match": ref_match,
        }
        if not ref_match:
            overall_match = False

    # ── Nº solicitud/demanda ────────────────────────────────────────────
    ext_demand = (extracted.get("demand_number") or "").strip()
    exp_demand = (expected.get("num_demanda") or "").strip()
    if exp_demand:
        demand_match = (
            ext_demand == exp_demand
            or ext_demand in exp_demand
            or exp_demand in ext_demand
        )
        results["solicitud_demanda"] = {
            "expected": exp_demand,
            "found": ext_demand,
            "match": demand_match,
        }
        if not demand_match:
            overall_match = False

    # ── Visit date (±7 days tolerance) ──────────────────────────────────
    ext_date_raw = (extracted.get("visit_date") or "").strip()
    exp_date_raw = (expected.get("fecha_visita") or "").strip()
    if exp_date_raw:
        date_match = _dates_within_days(ext_date_raw, exp_date_raw, 7)
        results["fecha_visita"] = {
            "expected": exp_date_raw,
            "found": ext_date_raw,
            "match": date_match,
        }
        if not date_match:
            overall_match = False

    # ── Tipo propiedad ──────────────────────────────────────────────────
    ext_type = (extracted.get("property_type") or "").strip()
    exp_type = (expected.get("tipo_propiedad") or "").strip()
    if exp_type:
        type_match = _fuzzy_name_match(ext_type, exp_type)
        results["tipo_propiedad"] = {
            "expected": exp_type,
            "found": ext_type,
            "match": type_match,
        }
        if not type_match:
            overall_match = False

    # ── Dirección propiedad ─────────────────────────────────────────────
    ext_addr = (extracted.get("property_address") or "").strip()
    exp_addr = (expected.get("direccion_propiedad") or "").strip()
    if exp_addr:
        addr_match = _fuzzy_name_match(ext_addr, exp_addr)
        results["direccion_propiedad"] = {
            "expected": exp_addr,
            "found": ext_addr,
            "match": addr_match,
        }
        if not addr_match:
            overall_match = False

    # ── Precio propiedad ────────────────────────────────────────────────
    ext_price = _normalize_price(extracted.get("property_price") or "")
    exp_price = _normalize_price(expected.get("precio_propiedad") or "")
    if exp_price:
        price_match = ext_price == exp_price
        results["precio_propiedad"] = {
            "expected": expected.get("precio_propiedad", ""),
            "found": extracted.get("property_price", ""),
            "match": price_match,
        }
        if not price_match:
            overall_match = False

    # ── Firma cliente ───────────────────────────────────────────────────
    sig_present = extracted.get("client_signature_present", False)
    results["firma_cliente"] = {
        "expected": "Presente",
        "found": "Presente" if sig_present else "No encontrada",
        "match": bool(sig_present),
    }
    if not sig_present:
        overall_match = False

    return {
        "match": overall_match,
        "fields": results,
        "extracted": extracted,
    }


def extraer_datos_hoja_por_pagina(pdf_path: Path, api_key: str) -> list[dict]:
    """Extract visit data from each page of a multi-page PDF independently.

    Returns a list of extraction dicts, one per page that contains visit data.
    Pages that don't appear to contain visit data are skipped.
    """
    images_b64 = pdf_to_base64_images(pdf_path)
    if not images_b64:
        raise RuntimeError("No se pudieron extraer paginas del PDF.")

    client = OpenAI(api_key=api_key)
    extractions = []

    for i, img_b64 in enumerate(images_b64):
        content = [
            {"type": "text", "text": "Extract the data from this property visit report page:"},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "high",
                },
            },
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_HOJA},
                {"role": "user", "content": content},
            ],
            tools=[EXTRACT_HOJA],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_hoja_visita"},
            },
        )

        message = response.choices[0].message
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "extract_hoja_visita":
                    data = json.loads(tool_call.function.arguments)
                    # Only keep pages that have meaningful data
                    has_data = any(
                        data.get(k)
                        for k in ("agent_name", "property_ref", "client_name")
                    )
                    if has_data:
                        data["_page"] = i + 1
                        extractions.append(data)

    return extractions


def emparejar_hojas(extractions: list[dict], checks: list[dict]) -> dict:
    """Match extracted page data to expected checks.

    Args:
        extractions: list of dicts from extraer_datos_hoja_por_pagina
        checks: list of dicts with keys: id, comercial, ref_propiedad,
                num_demanda, fecha_visita, nombre_cliente, etc.

    Returns:
        dict mapping check_id -> {match, fields, extracted, page} or None
    """
    results = {}
    used_extractions = set()

    for check in checks:
        best_score = -1
        best_idx = -1
        best_result = None

        for idx, ext in enumerate(extractions):
            if idx in used_extractions:
                continue

            ver = verificar_hoja(ext, check)
            score = sum(1 for f in ver["fields"].values() if f["match"])

            if score > best_score:
                best_score = score
                best_idx = idx
                best_result = ver

        check_id = check.get("id", str(checks.index(check)))

        if best_idx >= 0 and best_score > 0:
            used_extractions.add(best_idx)
            best_result["page"] = extractions[best_idx].get("_page", 0)
            results[check_id] = best_result
        else:
            results[check_id] = None

    return results


# ── Helpers ─────────────────────────────────────────────────────────────────

def _strip_accents(s: str) -> str:
    """Remove accents/diacritics from a string for fuzzy comparison."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _fuzzy_name_match(a: str, b: str) -> bool:
    """Check if two names likely refer to the same person.

    Strips accents before comparing so CSV encoding issues don't cause
    false negatives.
    """
    la = _strip_accents(a.lower())
    lb = _strip_accents(b.lower())
    if not la or not lb:
        return False
    # Direct substring
    if la in lb or lb in la:
        return True
    # Word-overlap heuristic
    words_a = set(la.split())
    words_b = set(lb.split())
    overlap = words_a & words_b
    return len(overlap) >= min(len(words_a), len(words_b)) * 0.5


def _parse_date(date_str: str):
    """Parse a date string into a datetime.date, or None."""
    date_str = date_str.strip()
    if not date_str:
        return None

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.split()[0], fmt).date()
        except ValueError:
            continue
    return None


def _dates_within_days(date1_str: str, date2_str: str, days: int = 7) -> bool:
    """Return True if two date strings are within ±days of each other."""
    d1 = _parse_date(date1_str)
    d2 = _parse_date(date2_str)
    if d1 and d2:
        return abs((d1 - d2).days) <= days
    # If either date can't be parsed, fall back to normalized string comparison
    n1 = _normalize_date(date1_str)
    n2 = _normalize_date(date2_str)
    return n1 == n2 if (n1 and n2) else False


def _normalize_date(date_str: str) -> str:
    """Normalize a date string to DD/MM/YYYY for comparison."""
    date_str = date_str.strip()
    if not date_str:
        return ""

    # DD/MM/YYYY (possibly with time)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"

    # DD-MM-YYYY
    m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", date_str)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"

    # DD.MM.YYYY
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_str)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"

    # YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if m:
        return f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}"

    return date_str


def _normalize_price(price_str: str) -> str:
    """Normalize a price string to digits only for comparison."""
    if not price_str:
        return ""
    # Remove everything except digits
    return re.sub(r"[^\d]", "", price_str)
