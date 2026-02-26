"""
comprobacion_comparator.py
Comparación determinista de datos extraídos de escritura, Modelo 211 y Modelo 600.
Sin llamadas a LLM — 100% Python puro.

IMPORTANTE: Las comparaciones son tolerantes con diferencias de formato.
- Fechas: "29 de diciembre de 2025" == "29/12/2025" == "29122025"
- Direcciones: "AVENIDA CASTELLON NUMERO 07" == "AV CASTELLON NR 07"
- Nombres: sin tildes, mayúsculas, espacios colapsados
- NIFs: sin espacios, guiones ni puntos
- Importes: tolerancia de 0.02 EUR
"""

import re
import unicodedata


# ── Etiquetas legibles para los campos ───────────────────────────────────────

FIELD_LABELS = {
    "comprador_nif":            "NIF del comprador",
    "comprador_nombre":         "Nombre del comprador",
    "comprador_domicilio":      "Domicilio del comprador",
    "comprador_cp":             "Código postal del comprador",
    "comprador_municipio":      "Municipio del comprador",
    "comprador_provincia":      "Provincia del comprador",
    "vendedor_nif":             "NIF del vendedor",
    "vendedor_nombre":          "Nombre del vendedor",
    "vendedor_pais_residencia": "País de residencia del vendedor",
    "vendedor_fecha_nacimiento":"Fecha de nacimiento del vendedor",
    "vendedor_domicilio":       "Domicilio del vendedor",
    "inmueble_direccion":       "Dirección del inmueble",
    "inmueble_cp":              "Código postal del inmueble",
    "inmueble_municipio":       "Municipio del inmueble",
    "inmueble_provincia":       "Provincia del inmueble",
    "inmueble_ref_catastral":   "Referencia catastral",
    "importe_transmision":      "Importe de la transmisión",
    "fecha_operacion":          "Fecha de la operación",
    "notario_nombre":           "Nombre del notario",
    "num_protocolo":            "Número de protocolo",
    "porcentaje_retencion":     "Porcentaje de retención",
    "importe_retencion":        "Importe de la retención",
    "resultado_ingresar":       "Resultado a ingresar",
    "forma_pago":               "Forma de pago",
    "iban":                     "IBAN",
    "base_imponible":           "Base imponible",
    "tipo_impuesto":            "Tipo de impuesto (TPO/AJD)",
    "tipo_gravamen":            "Tipo de gravamen",
    "cuota_tributaria":         "Cuota tributaria",
    "sujeto_pasivo_nif":        "NIF del sujeto pasivo",
    "sujeto_pasivo_nombre":     "Nombre del sujeto pasivo",
}


# ── Helpers de normalización para comparación ────────────────────────────────

def _ascii(s: str) -> str:
    """Convierte string a ASCII puro (sin tildes)."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
    return nfkd.encode("ascii", "ignore").decode("ascii")


def _norm_nif(val) -> str:
    """Normaliza NIF: mayúsculas, sin espacios ni guiones."""
    if not val:
        return ""
    return re.sub(r"[\s\-\.]", "", str(val).strip().upper())


def _norm_name(val) -> str:
    """Normaliza nombre: ASCII, mayúsculas, espacios colapsados."""
    if not val:
        return ""
    return re.sub(r"\s+", " ", _ascii(str(val)).upper().strip())


def _name_tokens(val) -> set:
    """
    Extrae el conjunto de palabras de un nombre, ignorando orden y puntuación.
    "POULSEN, RICHARDT" → {"POULSEN", "RICHARDT"}
    "RICHARDT POULSEN"  → {"POULSEN", "RICHARDT"}
    "MARK-THOMAS PERKINS" → {"MARK", "THOMAS", "PERKINS"}
    "PERKINS, MARK THOMAS" → {"PERKINS", "MARK", "THOMAS"}
    """
    if not val:
        return set()
    s = _ascii(str(val)).upper().strip()
    # Remove commas, hyphens, dots — split into individual words
    s = re.sub(r"[,.\-;:]+", " ", s)
    tokens = set(re.sub(r"\s+", " ", s).strip().split())
    # Remove trivial words that don't identify the person
    tokens.discard("DE")
    tokens.discard("DEL")
    tokens.discard("LA")
    tokens.discard("LOS")
    tokens.discard("LAS")
    return tokens


def _compare_names(val_a, val_b) -> bool:
    """
    Compara nombres de forma flexible:
    - Ignora orden (surname first vs name first)
    - Ignora comas, guiones
    - "RICHARDT POULSEN" == "POULSEN, RICHARDT" → True
    - "MARK-THOMAS PERKINS" == "PERKINS, MARK THOMAS" → True
    - "VALENTIN CONCEJO ARRANZ" == "CONCEJO ARRANZ VALENTIN" → True
    """
    # First try exact match after basic normalization
    if _norm_name(val_a) == _norm_name(val_b):
        return True
    # Then compare as sets of name tokens (order-independent)
    return _name_tokens(val_a) == _name_tokens(val_b)


def _norm_amount(val) -> float:
    """Normaliza importe a float."""
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = re.sub(r"[€$£\s]", "", str(val).strip())
    # Formato europeo: 102.000,00
    if re.search(r"\d\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r"\d,\d{3}\.\d{2}$", s):
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


# ── Date normalization (robust: handles text dates, numeric, mixed) ──────────

_MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    # Abbreviations
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "jun": "06", "jul": "07", "ago": "08", "sep": "09", "sept": "09",
    "oct": "10", "nov": "11", "dic": "12",
    "jan": "01", "aug": "08", "dec": "12",
}

_NUM_SIMPLES = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiun": 21, "veintiuno": 21, "veintiuna": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30,
}
_NUM_DECENAS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}
_NUM_CENTENAS = {
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800, "novecientos": 900, "novecientas": 900,
}

def _palabras_a_entero(texto: str) -> int:
    """Convierte número en palabras españolas a entero (días 1-31, años 1900-2099)."""
    s = _ascii(texto).lower().strip()
    s = re.sub(r'\b(del?|y|e)\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    tokens = s.split()
    total = 0
    for t in tokens:
        if t == "mil":
            total = (total if total else 1) * 1000
        elif t in _NUM_CENTENAS:
            total += _NUM_CENTENAS[t]
        elif t in _NUM_DECENAS:
            total += _NUM_DECENAS[t]
        elif t in _NUM_SIMPLES:
            total += _NUM_SIMPLES[t]
    return total


def _norm_date(val) -> str:
    """
    Normaliza fecha a DDMMYYYY para comparación.
    Handles:
      - "29/12/2025", "29-12-2025", "29.12.2025"
      - "2025-12-29" (ISO)
      - "29122025" (already DDMMYYYY)
      - "29 de diciembre de 2025"
      - "a veintinueve de diciembre del dos mil veinticinco"
      - "29 diciembre 2025"
      - "December 29, 2025"
    """
    if not val:
        return ""
    s = str(val).strip()

    # Already DDMMYYYY
    if re.fullmatch(r"\d{8}", s):
        return s

    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", s)
    if m:
        return f"{m.group(1).zfill(2)}{m.group(2).zfill(2)}{m.group(3)}"

    # YYYY-MM-DD or YYYY/MM/DD (ISO)
    m = re.fullmatch(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", s)
    if m:
        return f"{m.group(3).zfill(2)}{m.group(2).zfill(2)}{m.group(1)}"

    # Text-based: normalize to lowercase ASCII for pattern matching
    sl = _ascii(s).lower().strip()

    # "DD de MES de YYYY" or "DD MES YYYY" (Spanish/English month names)
    for mes_nombre, mes_num in _MESES.items():
        if mes_nombre not in sl:
            continue
        # Try "DD de MES de YYYY"
        m = re.search(r"(\d{1,2})\s+(?:de\s+)?" + re.escape(mes_nombre) + r"\s+(?:de[l]?\s+)?(\d{4})", sl)
        if m:
            return f"{m.group(1).zfill(2)}{mes_num}{m.group(2)}"
        # Try "MES DD, YYYY" (English style)
        m = re.search(re.escape(mes_nombre) + r"\s+(\d{1,2}),?\s+(\d{4})", sl)
        if m:
            return f"{m.group(1).zfill(2)}{mes_num}{m.group(2)}"

    # Fully written in words: "a veintinueve de diciembre del dos mil veinticinco"
    for mes_nombre, mes_num in _MESES.items():
        if not re.search(rf'\b{re.escape(mes_nombre)}\b', sl):
            continue
        partes = re.split(rf'\bde\s+{re.escape(mes_nombre)}\b', sl, maxsplit=1)
        if len(partes) < 2:
            partes = re.split(rf'\b{re.escape(mes_nombre)}\b', sl, maxsplit=1)
        if len(partes) < 2:
            continue
        day_raw = partes[0].strip()
        year_raw = partes[1].strip()
        # Clean prefixes
        day_raw = re.sub(r'^\b(a|el|la|en|los|las|al)\b\s*', '', day_raw).strip()
        year_raw = re.sub(r'^de[l]?\s+', '', year_raw).strip()
        year_raw = re.sub(r'[.,\s]+$', '', year_raw).strip()

        # Day might be a number or words
        dia = int(day_raw) if day_raw.isdigit() else _palabras_a_entero(day_raw)
        # Year might be a number or words
        anyo = int(year_raw) if year_raw.isdigit() else _palabras_a_entero(year_raw)
        if 1 <= dia <= 31 and 1900 <= anyo <= 2099:
            return f"{dia:02d}{mes_num}{anyo}"

    return _ascii(s).upper().strip()


# ── Address normalization (robust: handles abbreviations vs full names) ──────

# Map of common Spanish address abbreviations ↔ full forms
# We normalize everything to the abbreviated form for comparison
_ADDRESS_ABBREVS = {
    # Via types
    "AVENIDA": "AV", "AVDA": "AV", "AVD": "AV", "AVDA.": "AV", "AV.": "AV",
    "CALLE": "CL", "C/": "CL", "C.": "CL", "C": "CL",
    "PLAZA": "PZ", "PZA": "PZ", "PLZA": "PZ", "PL": "PZ",
    "PASEO": "PS", "PSO": "PS", "PO": "PS",
    "CAMINO": "CM", "CMO": "CM",
    "CARRETERA": "CR", "CRTA": "CR", "CTRA": "CR",
    "URBANIZACION": "URB", "URBANIZAC": "URB",
    "TRAVESIA": "TR", "TRAV": "TR",
    "RONDA": "RD",
    "PASAJE": "PJ", "PSJE": "PJ",
    "GLORIETA": "GL",
    "PROLONGACION": "PROL",
    "PARTIDA": "PTDA",
    "LUGAR": "LG",
    "BARRIO": "BO",
    "SECTOR": "SC",
    "PARCELA": "PC",
    # Number indicators
    "NUMERO": "N", "NUM": "N", "NR": "N", "NO": "N",
    "NUM.": "N", "NR.": "N", "NO.": "N", "N.": "N",
    # Floor/door
    "PLANTA": "PL", "PISO": "PL",
    "PUERTA": "PT", "PTA": "PT",
    "ESCALERA": "ESC", "ESCAL": "ESC",
    "BLOQUE": "BL", "BLQ": "BL",
    "PORTAL": "PRT", "PORT": "PRT",
    "BAJO": "BJ",
    "ENTRESUELO": "ENT", "ENTRLO": "ENT",
    "PRINCIPAL": "PRAL",
    "DERECHA": "DCHA", "DRCHA": "DCHA",
    "IZQUIERDA": "IZDA", "IZQDA": "IZDA", "IZQD": "IZDA",
    # Without/no number
    "SIN NUMERO": "SN", "S/N": "SN",
}


def _norm_address(val) -> str:
    """
    Normaliza dirección: ASCII, mayúsculas, sin puntuación,
    y reemplaza abreviaturas/formas completas por una forma canónica.
    """
    if not val:
        return ""
    s = _ascii(str(val)).upper().strip()
    s = re.sub(r"[,.\-;:/]+", " ", s)
    s = re.sub(r"\b(\d+)\s*(O|A|ER|ERO|ERA)\b", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bSIN\s+NUMERO\b", "SN", s)

    tokens = s.split()
    normalized = []
    for token in tokens:
        clean = token.rstrip(".")
        if clean in _ADDRESS_ABBREVS:
            normalized.append(_ADDRESS_ABBREVS[clean])
        else:
            normalized.append(token)

    result = " ".join(normalized)
    result = re.sub(r"\b0+(\d+)\b", r"\1", result)
    return result


def _address_tokens(val) -> set:
    """Extract meaningful tokens from an address for flexible comparison."""
    if not val:
        return set()
    s = _norm_address(val)
    tokens = set(s.split())
    # Remove filler words
    for w in ("DE", "DEL", "LA", "LOS", "LAS", "EL", "EN", "A"):
        tokens.discard(w)
    return tokens


def _compare_addresses(val_a, val_b) -> bool:
    """
    Compara direcciones de forma flexible.
    - Normaliza abreviaturas
    - Si una dirección es un subconjunto de la otra → OK (one is more complete)
    - Only flags if there's a clear difference in the core components
      (street name, number differ)

    Examples that should NOT be flagged:
    - "AV LA CORNISA N 7" vs "AV CORNISA NUM 7 C 04 25 PUERTO PLATA 425-C"
      → Same street & number, one just has more detail
    - "THE CHERRY ORCHARD" vs "THE CHERRY ORCHARD, KILLINCARRIG, DELGANY"
      → Subset
    """
    # Exact match after normalization
    norm_a = _norm_address(val_a)
    norm_b = _norm_address(val_b)
    if norm_a == norm_b:
        return True

    # Check if one is contained in the other (one is more detailed)
    if norm_a in norm_b or norm_b in norm_a:
        return True

    # Token-based: if the shorter set is a subset of the longer, it's just
    # a matter of one being more complete
    tokens_a = _address_tokens(val_a)
    tokens_b = _address_tokens(val_b)

    if not tokens_a or not tokens_b:
        return True  # one is empty, skip

    # If the smaller set is a subset of the larger → OK
    if tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a):
        return True

    # Check overlap: if >70% of the smaller set overlaps with the larger,
    # it's likely the same address with format differences
    smaller = tokens_a if len(tokens_a) <= len(tokens_b) else tokens_b
    larger = tokens_b if len(tokens_a) <= len(tokens_b) else tokens_a
    overlap = smaller & larger
    if len(overlap) >= len(smaller) * 0.7:
        return True

    return False


def _norm_generic(val) -> str:
    """Normalización genérica: ASCII, mayúsculas, trim, strip leading zeros from numbers."""
    if not val:
        return ""
    s = _ascii(str(val)).upper().strip()
    # If value is purely numeric (possibly with leading zeros), normalize
    # e.g. "02914" → "2914"
    if re.fullmatch(r"0*\d+", s):
        s = s.lstrip("0") or "0"
    return s


# ── Tipos de campo y su normalizador ────────────────────────────────────────

_NIF_FIELDS = {"comprador_nif", "vendedor_nif", "sujeto_pasivo_nif"}
_NAME_FIELDS = {"comprador_nombre", "vendedor_nombre", "sujeto_pasivo_nombre", "notario_nombre"}
_AMOUNT_FIELDS = {"importe_transmision", "porcentaje_retencion", "importe_retencion",
                  "resultado_ingresar", "base_imponible", "tipo_gravamen", "cuota_tributaria"}
_DATE_FIELDS = {"fecha_operacion", "vendedor_fecha_nacimiento"}
_ADDRESS_FIELDS = {"comprador_domicilio", "vendedor_domicilio", "inmueble_direccion",
                   "comprador_municipio", "inmueble_municipio", "comprador_provincia",
                   "inmueble_provincia"}


def _compare_field(campo: str, val_a, val_b) -> bool:
    """Compara dos valores de un campo usando la normalización adecuada."""
    if campo in _NIF_FIELDS:
        return _norm_nif(val_a) == _norm_nif(val_b)
    if campo in _NAME_FIELDS:
        return _compare_names(val_a, val_b)
    if campo in _AMOUNT_FIELDS:
        return abs(_norm_amount(val_a) - _norm_amount(val_b)) < 0.02
    if campo in _DATE_FIELDS:
        return _norm_date(val_a) == _norm_date(val_b)
    if campo in _ADDRESS_FIELDS:
        return _compare_addresses(val_a, val_b)
    return _norm_generic(val_a) == _norm_generic(val_b)


def _format_value(campo: str, val) -> str:
    """Formatea un valor para mostrarlo al usuario."""
    if val is None or val == "":
        return "(vacío)"
    if campo in _AMOUNT_FIELDS:
        try:
            return f"{_norm_amount(val):,.2f}"
        except Exception:
            return str(val)
    return str(val)


# ── Campos por fase de comparación ──────────────────────────────────────────

_COMMON_FIELDS = [
    "comprador_nif", "comprador_nombre", "comprador_domicilio",
    "comprador_cp", "comprador_municipio", "comprador_provincia",
    "vendedor_nif", "vendedor_nombre", "vendedor_pais_residencia",
    "vendedor_fecha_nacimiento", "vendedor_domicilio",
    "inmueble_direccion", "inmueble_cp", "inmueble_municipio",
    "inmueble_provincia", "inmueble_ref_catastral",
    "importe_transmision", "fecha_operacion",
    "notario_nombre", "num_protocolo",
]

_FIELDS_211_VS_600 = [
    "comprador_nif", "comprador_nombre",
    "vendedor_nif", "vendedor_nombre",
    "inmueble_direccion", "inmueble_cp", "inmueble_municipio",
    "inmueble_provincia", "inmueble_ref_catastral",
    "importe_transmision", "fecha_operacion",
]


# ── Comparador principal ────────────────────────────────────────────────────

def _compare_pair(doc_a: dict, doc_b: dict, fields: list,
                  label_a: str, label_b: str) -> list:
    """Compara dos documentos campo a campo y devuelve lista de discrepancias."""
    discrepancias = []
    for campo in fields:
        val_a = doc_a.get(campo)
        val_b = doc_b.get(campo)
        # Skip if both are empty/missing
        if (val_a is None or val_a == "") and (val_b is None or val_b == ""):
            continue
        # Skip if one is missing (only compare when both present)
        if (val_a is None or val_a == "") or (val_b is None or val_b == ""):
            continue
        if not _compare_field(campo, val_a, val_b):
            campo_legible = FIELD_LABELS.get(campo, campo)
            discrepancias.append({
                "comparacion": f"{label_a} vs {label_b}",
                "campo": campo,
                "campo_legible": campo_legible,
                f"valor_{label_a.lower().replace(' ', '_')}": _format_value(campo, val_a),
                f"valor_{label_b.lower().replace(' ', '_')}": _format_value(campo, val_b),
                "valor_esperado": _format_value(campo, val_a),
                "valor_encontrado": _format_value(campo, val_b),
                "correccion": f"Corregir {campo_legible.lower()} en el {label_b}: "
                              f"cambiar {_format_value(campo, val_b)} por {_format_value(campo, val_a)}"
            })
    return discrepancias


def comparar_documentos(escritura: dict, modelo211: dict, modelo600: dict) -> dict:
    """
    Compara los tres documentos y devuelve el resultado de la verificación.

    Args:
        escritura: Datos extraídos de la escritura (fuente de verdad).
        modelo211: Datos extraídos del Modelo 211 cumplimentado.
        modelo600: Datos extraídos del Modelo 600 cumplimentado.

    Returns:
        Dict con ok, total_campos_verificados y lista de discrepancias.
    """
    discrepancias = []
    campos_verificados = 0

    # Fase 1: Escritura vs Modelo 211
    disc_211 = _compare_pair(escritura, modelo211, _COMMON_FIELDS,
                             "Escritura", "Modelo 211")
    discrepancias.extend(disc_211)
    campos_verificados += sum(
        1 for c in _COMMON_FIELDS
        if escritura.get(c) and modelo211.get(c)
    )

    # Verificación derivada: retención = importe × porcentaje / 100
    importe = _norm_amount(modelo211.get("importe_transmision"))
    pct = _norm_amount(modelo211.get("porcentaje_retencion"))
    retencion = _norm_amount(modelo211.get("importe_retencion"))
    if importe > 0 and pct > 0 and retencion > 0:
        esperada = round(importe * pct / 100, 2)
        if abs(retencion - esperada) > 0.02:
            discrepancias.append({
                "comparacion": "Modelo 211 (cálculo interno)",
                "campo": "importe_retencion",
                "campo_legible": "Importe de la retención (cálculo)",
                "valor_esperado": f"{esperada:,.2f}",
                "valor_encontrado": f"{retencion:,.2f}",
                "correccion": f"La retención debería ser {esperada:,.2f} EUR "
                              f"({importe:,.2f} × {pct}% = {esperada:,.2f}), "
                              f"pero el Modelo 211 indica {retencion:,.2f} EUR"
            })
        campos_verificados += 1

    # Fase 2: Escritura vs Modelo 600
    disc_600 = _compare_pair(escritura, modelo600, _COMMON_FIELDS,
                             "Escritura", "Modelo 600")
    discrepancias.extend(disc_600)
    campos_verificados += sum(
        1 for c in _COMMON_FIELDS
        if escritura.get(c) and modelo600.get(c)
    )

    # Verificación: base_imponible == importe_transmision
    base = _norm_amount(modelo600.get("base_imponible"))
    importe_esc = _norm_amount(escritura.get("importe_transmision"))
    if base > 0 and importe_esc > 0 and abs(base - importe_esc) > 0.02:
        discrepancias.append({
            "comparacion": "Escritura vs Modelo 600",
            "campo": "base_imponible",
            "campo_legible": "Base imponible",
            "valor_esperado": f"{importe_esc:,.2f}",
            "valor_encontrado": f"{base:,.2f}",
            "correccion": f"La base imponible del Modelo 600 ({base:,.2f} EUR) "
                          f"no coincide con el importe de transmisión de la escritura ({importe_esc:,.2f} EUR)"
        })
        campos_verificados += 1

    # Fase 3: Modelo 211 vs Modelo 600
    disc_cross = _compare_pair(modelo211, modelo600, _FIELDS_211_VS_600,
                               "Modelo 211", "Modelo 600")
    discrepancias.extend(disc_cross)
    campos_verificados += sum(
        1 for c in _FIELDS_211_VS_600
        if modelo211.get(c) and modelo600.get(c)
    )

    return {
        "ok": len(discrepancias) == 0,
        "total_campos_verificados": campos_verificados,
        "discrepancias": discrepancias,
    }
