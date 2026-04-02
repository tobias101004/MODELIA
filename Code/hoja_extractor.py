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
                        "Client/customer name — this is the person who visited the property "
                        "(the potential buyer or searcher), NOT the property owner or agent. "
                        "Look for 'Nombre Cliente', 'Client\\'s Name', 'Name des Kunden' in "
                        "the client info table near the top of the document. "
                        "IMPORTANT: The document title/header may contain a format like "
                        "'DEMANDA / REF-CODE (PropertyName) / ClientName / DemandNumber' or "
                        "the description may say 'Visita a la Ref: XXXXX-CA (PropertyName) "
                        "por el cliente NNNNN (ClientName)'. In this pattern, the name in "
                        "parentheses AFTER 'por el cliente NNNNN' is the CLIENT name — "
                        "the name in parentheses after the REF code is the PROPERTY name, "
                        "not the client. Always prefer the name from the 'Nombre Cliente' "
                        "field in the client info table if visible. Return ONLY the client's "
                        "first name or full name as written, without ID numbers."
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
10. If a field is not found, return an empty string (or false for signature).

CRITICAL — CLIENT NAME EXTRACTION:
The client name is the person who visited the property (the potential buyer/searcher). \
It is NOT the property name or the agent name. \
Look for the 'Nombre Cliente' / 'Client's Name' / 'Name des Kunden' field in the \
client info table near the top of the document. \
BE CAREFUL: The document title or description may follow a pattern like: \
'Visita a la Ref: 06055-CA (Christopher) por el cliente 13059 (Samara)'. \
In this format, 'Christopher' is the PROPERTY reference name (NOT the client), \
and 'Samara' is the CLIENT name (the name in parentheses after the client ID number). \
Always prioritize the name written in the 'Nombre Cliente' field of the client info table. \
Return only the client's name, without any ID numbers or reference codes."""


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

    Uses weighted scoring to determine if an extraction matches a check.
    Identity fields (property_ref, demand_number) are weighted heavily.
    Secondary fields (agent, client, date, etc.) provide supporting evidence.
    Signature is a quality indicator, not a matching criterion.

    Args:
        extracted: dict from GPT-4o (agent_name, property_ref, visit_date,
                   client_name, demand_number, property_type, property_address,
                   property_price, client_signature_present)
        expected:  dict with CSV data (comercial, ref_propiedad, num_demanda,
                   fecha_visita, id_seguimiento, nombre_cliente,
                   tipo_propiedad, direccion_propiedad, precio_propiedad)

    Returns:
        dict with ``match`` bool, ``score`` int, per-field ``fields`` results,
        and raw ``extracted`` data.
    """
    results = {}
    weighted_score = 0
    max_possible_score = 0

    # ── Identity fields (high weight) ──────────────────────────────────

    # Nº solicitud/demanda — strongest identifier, unique per visit/client (weight: 6)
    ext_demand = re.sub(r"[^\d]", "", extracted.get("demand_number") or "")
    exp_demand = re.sub(r"[^\d]", "", expected.get("num_demanda") or "")
    if exp_demand:
        demand_match = bool(
            ext_demand and exp_demand and (
                ext_demand == exp_demand
                or ext_demand in exp_demand
                or exp_demand in ext_demand
            )
        )
        results["solicitud_demanda"] = {
            "expected": expected.get("num_demanda", ""),
            "found": extracted.get("demand_number", ""),
            "match": demand_match,
        }
        max_possible_score += 6
        if demand_match:
            weighted_score += 6

    # Property REF — supporting identifier, can repeat across visits (weight: 3)
    ext_ref = (extracted.get("property_ref") or "").strip().upper().replace(" ", "")
    exp_ref = (expected.get("ref_propiedad") or "").strip().upper().replace(" ", "")
    ext_ref_digits = re.sub(r"[^\d]", "", ext_ref)
    exp_ref_digits = re.sub(r"[^\d]", "", exp_ref)
    if exp_ref:
        ref_match = (
            ext_ref == exp_ref
            or ext_ref.startswith(exp_ref)
            or exp_ref.startswith(ext_ref)
            or exp_ref in ext_ref
            or ext_ref in exp_ref
            # Loose digit-only match (e.g., "06055" vs "06055-CA")
            or (ext_ref_digits and exp_ref_digits and
                (ext_ref_digits == exp_ref_digits
                 or ext_ref_digits.startswith(exp_ref_digits)
                 or exp_ref_digits.startswith(ext_ref_digits)))
        )
        results["ref_propiedad"] = {
            "expected": expected.get("ref_propiedad", ""),
            "found": extracted.get("property_ref", ""),
            "match": ref_match,
        }
        max_possible_score += 3
        if ref_match:
            weighted_score += 3

    # ── Supporting fields (medium weight) ──────────────────────────────

    # Asesor / agent (weight: 2)
    ext_agent = (extracted.get("agent_name") or "").strip()
    exp_agent = (expected.get("comercial") or "").strip()
    if exp_agent:
        agent_match = _fuzzy_name_match(ext_agent, exp_agent)
        results["asesor"] = {
            "expected": exp_agent,
            "found": ext_agent,
            "match": agent_match,
        }
        max_possible_score += 2
        if agent_match:
            weighted_score += 2

    # Nombre cliente (weight: 2) — uses flexible matching (nicknames, partial, etc.)
    ext_client = (extracted.get("client_name") or "").strip()
    exp_client = (expected.get("nombre_cliente") or "").strip()
    if exp_client:
        client_match = _flexible_client_name_match(ext_client, exp_client)
        results["nombre_cliente"] = {
            "expected": exp_client,
            "found": ext_client,
            "match": client_match,
        }
        max_possible_score += 2
        if client_match:
            weighted_score += 2

    # Visit date ±7 days (weight: 2)
    ext_date_raw = (extracted.get("visit_date") or "").strip()
    exp_date_raw = (expected.get("fecha_visita") or "").strip()
    if exp_date_raw:
        date_match = _dates_within_days(ext_date_raw, exp_date_raw, 7)
        results["fecha_visita"] = {
            "expected": exp_date_raw,
            "found": ext_date_raw,
            "match": date_match,
        }
        max_possible_score += 2
        if date_match:
            weighted_score += 2

    # ── Secondary fields (low weight) ──────────────────────────────────

    # Tipo propiedad (weight: 1)
    ext_type = (extracted.get("property_type") or "").strip()
    exp_type = (expected.get("tipo_propiedad") or "").strip()
    if exp_type:
        type_match = _fuzzy_name_match(ext_type, exp_type)
        results["tipo_propiedad"] = {
            "expected": exp_type,
            "found": ext_type,
            "match": type_match,
        }
        max_possible_score += 1
        if type_match:
            weighted_score += 1

    # Dirección propiedad (weight: 1)
    ext_addr = (extracted.get("property_address") or "").strip()
    exp_addr = (expected.get("direccion_propiedad") or "").strip()
    if exp_addr:
        addr_match = _fuzzy_name_match(ext_addr, exp_addr)
        results["direccion_propiedad"] = {
            "expected": exp_addr,
            "found": ext_addr,
            "match": addr_match,
        }
        max_possible_score += 1
        if addr_match:
            weighted_score += 1

    # Precio propiedad (weight: 1)
    ext_price = _normalize_price(extracted.get("property_price") or "")
    exp_price = _normalize_price(expected.get("precio_propiedad") or "")
    if exp_price:
        price_match = ext_price == exp_price
        results["precio_propiedad"] = {
            "expected": expected.get("precio_propiedad", ""),
            "found": extracted.get("property_price", ""),
            "match": price_match,
        }
        max_possible_score += 1
        if price_match:
            weighted_score += 1

    # ── Firma cliente — quality indicator only, does NOT affect match ──
    sig_present = extracted.get("client_signature_present", False)
    results["firma_cliente"] = {
        "expected": "Presente",
        "found": "Presente" if sig_present else "No encontrada",
        "match": bool(sig_present),
    }

    # ── Determine overall match ────────────────────────────────────────
    # Two-level result:
    #
    # IDENTIFICATION: ref_propiedad + num_demanda both match.
    #   → This confirms it IS the visit we're looking for.
    #
    # VERIFICATION: ALL other fields also match (agent, client, date,
    #   type, address, price, signature).
    #   → "verified" = identified AND everything checks out.
    #   → "incomplete" = identified BUT some fields are missing/wrong.
    #   → "not_found" = could not even identify the visit in the document.
    #
    # The frontend uses `identified` to decide if the visit was found,
    # and `match` (all fields ok) to decide verified vs incomplete.
    ref_matched = results.get("ref_propiedad", {}).get("match", False)
    demand_matched = results.get("solicitud_demanda", {}).get("match", False)

    # Identification: ref + demand (or just one if the other wasn't available)
    if ref_matched and demand_matched:
        identified = True
    elif demand_matched and not exp_ref:
        identified = True
    elif ref_matched and not exp_demand:
        identified = True
    else:
        identified = False

    # Full verification: identified AND every compared field matches
    all_fields_ok = all(f["match"] for f in results.values())
    overall_match = identified and all_fields_ok

    return {
        "match": overall_match,         # True = fully verified (all fields ok)
        "identified": identified,       # True = ref+demand confirmed this is the visit
        "score": weighted_score,
        "max_score": max_possible_score,
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
    """Match extracted page data to expected checks using weighted scoring.

    Uses a two-pass approach:
    1. First pass: find best matches using weighted scores
    2. Second pass: assign remaining extractions to unmatched checks if
       there is any positive evidence

    Args:
        extractions: list of dicts from extraer_datos_hoja_por_pagina
        checks: list of dicts with keys: id, comercial, ref_propiedad,
                num_demanda, fecha_visita, nombre_cliente, etc.

    Returns:
        dict mapping check_id -> {match, score, fields, extracted, page} or None
    """
    import logging
    log = logging.getLogger("hoja_extractor")

    # Build a score matrix: (check_idx, extraction_idx) -> verification result
    score_matrix = []
    for ci, check in enumerate(checks):
        for ei, ext in enumerate(extractions):
            ver = verificar_hoja(ext, check)
            score_matrix.append({
                "check_idx": ci,
                "ext_idx": ei,
                "score": ver["score"],
                "match": ver["match"],
                "result": ver,
            })

    # Sort by: identified first, then match (all fields), then score
    score_matrix.sort(
        key=lambda x: (x["result"]["identified"], x["match"], x["score"]),
        reverse=True,
    )

    results = {}
    used_checks = set()
    used_extractions = set()

    # Assign best matches greedily by highest score
    for entry in score_matrix:
        ci = entry["check_idx"]
        ei = entry["ext_idx"]
        if ci in used_checks or ei in used_extractions:
            continue
        if entry["score"] <= 0:
            continue

        check = checks[ci]
        check_id = check.get("id", str(ci))

        used_checks.add(ci)
        used_extractions.add(ei)
        entry["result"]["page"] = extractions[ei].get("_page", 0)
        results[check_id] = entry["result"]

        log.info(
            f"[MATCH] Check {check_id} (ref={check.get('ref_propiedad','?')}) "
            f"<-> page {entry['result']['page']} "
            f"(extracted ref={extractions[ei].get('property_ref','?')}) "
            f"score={entry['score']} match={entry['match']}"
        )

    # Fill in unmatched checks as None
    for ci, check in enumerate(checks):
        check_id = check.get("id", str(ci))
        if check_id not in results:
            results[check_id] = None
            log.info(
                f"[NO MATCH] Check {check_id} "
                f"(ref={check.get('ref_propiedad','?')}) — no extraction matched"
            )

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


def _flexible_client_name_match(extracted_name: str, expected_name: str) -> bool:
    """Very flexible client name matching for audit verification.

    The extracted name comes from AI reading a scanned visit sheet, and the
    expected name comes from the CRM CSV. These can differ significantly:
    - Different order: "Garcia Lopez Maria" vs "Maria Garcia"
    - With/without surname: "Samara" vs "Samara Rodriguez"
    - Nicknames or abbreviations: "Paco" vs "Francisco"
    - Partial names: "M. Garcia" vs "Maria Garcia Lopez"
    - Extra words: "Sr. Martinez" vs "Martinez"
    - Typos from OCR: "Martínez" vs "Martinez"

    Returns True if there is reasonable evidence both names refer to the
    same person. Errs on the side of matching (permissive).
    """
    a = _strip_accents(extracted_name.strip().lower())
    b = _strip_accents(expected_name.strip().lower())
    if not a or not b:
        return False

    # Remove common prefixes/suffixes that aren't part of the name
    for prefix in ("sr.", "sra.", "sr ", "sra ", "don ", "doña ", "dona ",
                   "mr.", "mrs.", "ms.", "mr ", "mrs ", "ms ",
                   "herr ", "frau "):
        a = a.replace(prefix, "")
        b = b.replace(prefix, "")
    a = a.strip()
    b = b.strip()

    if not a or not b:
        return False

    # Exact match after normalization
    if a == b:
        return True

    # Direct substring — one name contained in the other
    if a in b or b in a:
        return True

    # Word-based matching: ANY shared word is enough
    # (e.g., "Samara" matches "Samara Rodriguez Torres")
    words_a = set(w for w in a.split() if len(w) > 1)
    words_b = set(w for w in b.split() if len(w) > 1)

    if not words_a or not words_b:
        return False

    overlap = words_a & words_b
    if overlap:
        return True

    # Check if any word from one set is a substring of any word in the other
    # Catches: "Fran" in "Francisco", "Alex" in "Alexander", etc.
    for wa in words_a:
        for wb in words_b:
            if len(wa) >= 3 and len(wb) >= 3:
                if wa in wb or wb in wa:
                    return True

    # Levenshtein-like: if the shorter name is very close to part of the longer
    # (catches OCR typos: "Martimez" vs "Martinez")
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 3:
        # Check if any word in the longer name is close to any word in shorter
        for ws in shorter.split():
            if len(ws) < 3:
                continue
            for wl in longer.split():
                if len(wl) < 3:
                    continue
                if _simple_similarity(ws, wl) >= 0.75:
                    return True

    return False


def _simple_similarity(a: str, b: str) -> float:
    """Simple character-overlap similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    # Bigram similarity (Dice coefficient)
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))
    ba = bigrams(a)
    bb = bigrams(b)
    if not ba or not bb:
        return 1.0 if a == b else 0.0
    return 2.0 * len(ba & bb) / (len(ba) + len(bb))


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
