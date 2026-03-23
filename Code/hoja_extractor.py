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
                        "in the property title, or as 'Num Demanda'. "
                        "Return just the number without surrounding text."
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
2. Client info table (name, phone, appointment place)
3. Date and agent info (Created by / Made by)
4. Property details section with REF number
5. Visit report / Control de Visitas / Besichtigungskontrolle section with signatures

Instructions:
1. Extract ONLY data clearly visible in the document image.
2. For the agent name: this is the Cardenas consultant, NOT the client. \
Look for 'Creado por', 'Created by', 'Erstellt von', 'Realizado por', \
'Made by', 'Durchgefuhrt von'.
3. For property REF: found in property details title, format like '06023-CA'.
4. For date: convert to DD/MM/YYYY format.
5. For demand number: may appear in parentheses in the client name field \
like '(Demanda 12581)' or in the property title. Just return the number.
6. If a field is not found, return an empty string."""


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
                   client_name, demand_number)
        expected:  dict with CSV data (comercial, ref_propiedad, num_demanda,
                   fecha_visita, id_seguimiento)

    Returns:
        dict with ``match`` bool, per-field ``fields`` results, and raw
        ``extracted`` data.
    """
    results = {}
    overall_match = True

    # ── Agent / Comercial ───────────────────────────────────────────────
    ext_agent = (extracted.get("agent_name") or "").strip()
    exp_agent = (expected.get("comercial") or "").strip()
    if exp_agent:
        agent_match = _fuzzy_name_match(ext_agent, exp_agent)
        results["comercial"] = {
            "expected": exp_agent,
            "found": ext_agent,
            "match": agent_match,
        }
        if not agent_match:
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

    # ── Demand number ───────────────────────────────────────────────────
    ext_demand = (extracted.get("demand_number") or "").strip()
    exp_demand = (expected.get("num_demanda") or "").strip()
    if exp_demand:
        demand_match = (
            ext_demand == exp_demand
            or ext_demand in exp_demand
            or exp_demand in ext_demand
        )
        results["num_demanda"] = {
            "expected": exp_demand,
            "found": ext_demand,
            "match": demand_match,
        }
        if not demand_match:
            overall_match = False

    # ── Visit date ──────────────────────────────────────────────────────
    ext_date = _normalize_date(extracted.get("visit_date") or "")
    exp_date = _normalize_date(expected.get("fecha_visita") or "")
    if exp_date:
        date_match = ext_date == exp_date
        results["fecha_visita"] = {
            "expected": expected.get("fecha_visita", ""),
            "found": extracted.get("visit_date", ""),
            "match": date_match,
        }
        if not date_match:
            overall_match = False

    return {
        "match": overall_match,
        "fields": results,
        "extracted": extracted,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fuzzy_name_match(a: str, b: str) -> bool:
    """Check if two names likely refer to the same person."""
    la = a.lower()
    lb = b.lower()
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
