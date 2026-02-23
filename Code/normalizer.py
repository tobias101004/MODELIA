"""
normalizer.py
Normaliza el dict raw del LLM al formato exacto que consume modelo211_generator.

Conversiones:
- Fechas en cualquier formato → DDMMYYYY (8 dígitos)
- Importes con símbolos/separadores → float
- Nombres de países / códigos → ISO 3166-1 alpha-2
- coef_part_porcentaje (0-100) → coef_part_centesimas (entero ×100)
- Cálculo automático de retención si no se indica
- Sanitización ASCII: todos los strings se limpian de caracteres no-ASCII
  (ej: º→"", é→e, ñ→n) para que el fichero final sea siempre 6600 bytes exactos
- Sincronización pagina_020/030 desde pagina_010 si están vacías
"""

import re
import unicodedata


# ── Sanitización ASCII ────────────────────────────────────────────────────────

def _ascii(s) -> str:
    """
    Convierte cualquier string a ASCII puro.
    - Descompone caracteres acentuados: é→e, ü→u, ñ→n, etc.
    - Elimina caracteres sin equivalente ASCII: º, ª, etc.
    Garantiza que el fichero final ocupe exactamente 6600 bytes.
    """
    if not isinstance(s, str) or not s:
        return s if s is not None else ""
    nfkd = unicodedata.normalize("NFKD", s)
    return nfkd.encode("ascii", "ignore").decode("ascii")


def _ascii_dict(obj):
    """Aplica _ascii recursivamente a todos los strings de un dict/list."""
    if isinstance(obj, dict):
        return {k: _ascii_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_ascii_dict(v) for v in obj]
    if isinstance(obj, str):
        return _ascii(obj)
    return obj


# ── Mapeo de países (nombre → ISO alpha-2) ────────────────────────────────────

COUNTRY_MAP: dict[str, str] = {
    # Códigos ISO directos (passthrough)
    "ES": "ES", "GB": "GB", "DE": "DE", "FR": "FR", "IT": "IT",
    "NO": "NO", "SE": "SE", "DK": "DK", "FI": "FI", "NL": "NL",
    "BE": "BE", "AT": "AT", "CH": "CH", "PT": "PT", "IE": "IE",
    "US": "US", "CA": "CA", "AU": "AU", "NZ": "NZ", "JP": "JP",
    "CN": "CN", "RU": "RU", "BR": "BR", "MX": "MX", "AR": "AR",
    "CO": "CO", "CL": "CL", "VE": "VE", "PE": "PE", "UY": "UY",
    "PL": "PL", "CZ": "CZ", "SK": "SK", "HU": "HU", "RO": "RO",
    "BG": "BG", "HR": "HR", "SI": "SI", "EE": "EE", "LV": "LV",
    "LT": "LT", "LU": "LU", "MT": "MT", "CY": "CY", "GR": "GR",
    "TR": "TR", "MA": "MA", "DZ": "DZ", "EG": "EG", "ZA": "ZA",
    "IN": "IN", "PK": "PK", "IL": "IL", "AE": "AE", "SA": "SA",
    "NG": "NG", "KE": "KE", "SG": "SG", "HK": "HK", "TH": "TH",
    "KR": "KR", "TW": "TW", "MY": "MY", "PH": "PH", "ID": "ID",
    "UA": "UA", "RS": "RS", "BA": "BA", "MK": "MK", "AL": "AL",
    "IS": "IS", "LI": "LI", "MC": "MC", "SM": "SM", "AD": "AD",
    # Nombres en español (mayúsculas sin tildes)
    "ESPANA": "ES", "ESPAÑA": "ES",
    "ALEMANIA": "DE",
    "REINO UNIDO": "GB", "GRAN BRETANA": "GB", "GRAN BRETAÑA": "GB",
    "INGLATERRA": "GB", "ESCOCIA": "GB", "GALES": "GB",
    "FRANCIA": "FR",
    "ITALIA": "IT",
    "NORUEGA": "NO",
    "SUECIA": "SE",
    "DINAMARCA": "DK",
    "FINLANDIA": "FI",
    "HOLANDA": "NL", "PAISES BAJOS": "NL", "PAÍSES BAJOS": "NL",
    "BELGICA": "BE", "BÉLGICA": "BE",
    "AUSTRIA": "AT",
    "SUIZA": "CH",
    "PORTUGAL": "PT",
    "IRLANDA": "IE",
    "ESTADOS UNIDOS": "US", "EEUU": "US", "EE.UU.": "US", "EE UU": "US",
    "CANADA": "CA", "CANADÁ": "CA",
    "AUSTRALIA": "AU",
    "NUEVA ZELANDA": "NZ",
    "JAPON": "JP", "JAPÓN": "JP",
    "CHINA": "CN",
    "RUSIA": "RU",
    "BRASIL": "BR",
    "MEXICO": "MX", "MÉXICO": "MX",
    "ARGENTINA": "AR",
    "COLOMBIA": "CO",
    "CHILE": "CL",
    "VENEZUELA": "VE",
    "PERU": "PE", "PERÚ": "PE",
    "URUGUAY": "UY",
    "POLONIA": "PL",
    "REPUBLICA CHECA": "CZ", "REPÚBLICA CHECA": "CZ", "CHEQUIA": "CZ",
    "ESLOVAQUIA": "SK",
    "HUNGRIA": "HU", "HUNGRÍA": "HU",
    "RUMANIA": "RO", "RUMANÍA": "RO",
    "BULGARIA": "BG",
    "CROACIA": "HR",
    "ESLOVENIA": "SI",
    "ESTONIA": "EE",
    "LETONIA": "LV",
    "LITUANIA": "LT",
    "LUXEMBURGO": "LU",
    "MALTA": "MT",
    "CHIPRE": "CY",
    "GRECIA": "GR",
    "TURQUIA": "TR", "TURQUÍA": "TR",
    "MARRUECOS": "MA",
    "ARGELIA": "DZ",
    "EGIPTO": "EG",
    "SUDAFRICA": "ZA", "SUDÁFRICA": "ZA",
    "INDIA": "IN",
    "PAKISTAN": "PK", "PAKISTÁN": "PK",
    "ISRAEL": "IL",
    "EMIRATOS ARABES UNIDOS": "AE", "EMIRATOS ARABES": "AE", "EAU": "AE",
    "ARABIA SAUDI": "SA", "ARABIA SAUDÍ": "SA",
    "ISLANDIA": "IS",
    "SINGAPUR": "SG",
    "UCRANIA": "UA",
    # Nombres en inglés
    "GERMANY": "DE",
    "UNITED KINGDOM": "GB", "ENGLAND": "GB", "SCOTLAND": "GB", "WALES": "GB",
    "FRANCE": "FR",
    "ITALY": "IT",
    "NORWAY": "NO",
    "SWEDEN": "SE",
    "DENMARK": "DK",
    "FINLAND": "FI",
    "NETHERLANDS": "NL", "HOLLAND": "NL",
    "BELGIUM": "BE",
    "SWITZERLAND": "CH",
    "IRELAND": "IE",
    "UNITED STATES": "US", "USA": "US", "UNITED STATES OF AMERICA": "US",
    "CANADA": "CA",
    "NEW ZEALAND": "NZ",
    "JAPAN": "JP",
    "RUSSIA": "RU",
    "BRAZIL": "BR",
    "POLAND": "PL",
    "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ",
    "SLOVAKIA": "SK",
    "HUNGARY": "HU",
    "ROMANIA": "RO",
    "CROATIA": "HR",
    "SLOVENIA": "SI",
    "ESTONIA": "EE",
    "LATVIA": "LV",
    "LITHUANIA": "LT",
    "LUXEMBOURG": "LU",
    "CYPRUS": "CY",
    "GREECE": "GR",
    "TURKEY": "TR",
    "MOROCCO": "MA",
    "SOUTH AFRICA": "ZA",
    "UKRAINE": "UA",
    "ICELAND": "IS",
    "SINGAPORE": "SG",
    "UAE": "AE", "SAUDI ARABIA": "SA",
}

MESES_ES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

# ── Números en palabras (español) ─────────────────────────────────────────────
# Usados para parsear fechas escritas en letras en escrituras notariales:
# "a veintinueve de abril del dos mil veinticinco" → 29042025

_NUM_SIMPLES: dict[str, int] = {
    "un": 1, "uno": 1, "una": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20,
    "veintiun": 21, "veintiuno": 21, "veintiuna": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
    "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29,
    "treinta": 30,
}
_NUM_DECENAS: dict[str, int] = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}
_NUM_CENTENAS: dict[str, int] = {
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}


def _palabras_a_entero(texto: str) -> int:
    """
    Convierte número escrito en palabras (español) a entero.
    Cubre días (1-31) y años (1900-2099) típicos de escrituras notariales.
    Ejemplos:
      "veintinueve"           → 29
      "dos mil veinticinco"   → 2025
      "mil novecientos ochenta y dos" → 1982
      "treinta y uno"         → 31
    """
    # Normalizar: quitar tildes/acentos, minúsculas, separadores
    s = _ascii(texto).lower().strip()
    s = re.sub(r'\b(del?|y|e)\b', ' ', s)   # quitar artículos/conectores
    s = re.sub(r'\s+', ' ', s).strip()

    tokens = s.split()
    total = 0
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "mil":
            # "dos mil" → 2000  |  solo "mil" → 1000
            total = (total if total else 1) * 1000
        elif t in _NUM_CENTENAS:
            total += _NUM_CENTENAS[t]
        elif t in _NUM_DECENAS:
            total += _NUM_DECENAS[t]
        elif t in _NUM_SIMPLES:
            total += _NUM_SIMPLES[t]
        i += 1
    return total


def _fecha_palabras(texto: str) -> str:
    """
    Parsea fechas escritas en letras en escrituras notariales españolas.
    Ejemplos:
      "a veintinueve de abril del dos mil veinticinco"  → "29042025"
      "a uno de enero de dos mil veinticuatro"          → "01012024"
      "treinta y uno de diciembre de mil novecientos noventa" → "31121990"
    Devuelve "" si no puede parsear.
    """
    s = _ascii(texto).lower().strip()
    # Buscar el nombre del mes como ancla
    for mes_nombre, mes_num in MESES_ES.items():
        if not re.search(rf'\b{mes_nombre}\b', s):
            continue
        # Dividir por "de {mes}"
        partes = re.split(rf'\bde\s+{mes_nombre}\b', s, maxsplit=1)
        if len(partes) < 2:
            continue
        day_raw  = partes[0].strip()
        year_raw = partes[1].strip()
        # Limpiar prefijos irrelevantes del día: artículos y preposiciones sueltos
        day_raw  = re.sub(r'^\b(a|el|la|en|los|las|al)\b\s*', '', day_raw).strip()
        # Limpiar "del/de" inicial del año y puntuación final
        year_raw = re.sub(r'^de[l]?\s+', '', year_raw).strip()
        year_raw = re.sub(r'[.,\s]+$', '', year_raw).strip()

        dia  = _palabras_a_entero(day_raw)
        anyo = _palabras_a_entero(year_raw)
        if 1 <= dia <= 31 and 1900 <= anyo <= 2099:
            return f"{dia:02d}{mes_num}{anyo}"
    return ""


# ── Funciones de normalización ────────────────────────────────────────────────

def normalizar_fecha(valor) -> str:
    """Convierte cualquier representación de fecha a DDMMYYYY (8 dígitos)."""
    if not valor:
        return ""
    s = str(valor).strip()

    # Ya en formato DDMMYYYY
    if re.fullmatch(r"\d{8}", s):
        return s

    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", s)
    if m:
        return f"{m.group(1).zfill(2)}{m.group(2).zfill(2)}{m.group(3)}"

    # YYYY-MM-DD o YYYY/MM/DD (formato ISO)
    m = re.fullmatch(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", s)
    if m:
        return f"{m.group(3).zfill(2)}{m.group(2).zfill(2)}{m.group(1)}"

    # DD de mes de YYYY (español)
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", s.lower())
    if m:
        mes = MESES_ES.get(m.group(2).lower(), "")
        if mes:
            return f"{m.group(1).zfill(2)}{mes}{m.group(3)}"

    # DD mes YYYY
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s.lower())
    if m:
        mes = MESES_ES.get(m.group(2).lower(), "")
        if mes:
            return f"{m.group(1).zfill(2)}{mes}{m.group(3)}"

    # Fecha completamente en palabras: "a veintinueve de abril del dos mil veinticinco"
    resultado = _fecha_palabras(s)
    if resultado:
        return resultado

    return ""


def normalizar_importe(valor) -> float:
    """Convierte cualquier representación de importe a float."""
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)

    s = str(valor).strip()
    # Quitar símbolo de moneda y espacios
    s = re.sub(r"[€$£\s]", "", s)

    # Formato europeo: 102.000,00 → punto=miles, coma=decimal
    if re.search(r"\d\.\d{3},\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    # Formato americano: 102,000.00 → coma=miles, punto=decimal
    elif re.search(r"\d,\d{3}\.\d{2}$", s):
        s = s.replace(",", "")
    # Solo coma y sin punto: coma como decimal
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    # Solo punto: comprobar si es separador de miles (>3 dígitos tras punto)
    elif "." in s and "," not in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit():
            s = s.replace(".", "")  # separador de miles, no decimal

    try:
        return float(s)
    except ValueError:
        return 0.0


def normalizar_pais(valor) -> str:
    """Convierte nombre de país o código a ISO 3166-1 alpha-2."""
    if not valor:
        return ""
    v = str(valor).strip().upper()
    # Buscar en mapa (normalizado sin tildes)
    resultado = COUNTRY_MAP.get(v)
    if resultado:
        return resultado
    # Si es un código de 2 letras que no está en el mapa, devolverlo tal cual
    if len(v) == 2 and v.isalpha():
        return v
    return ""


def _norm_dir_ext(raw: dict) -> dict:
    """Normaliza una dirección extranjera."""
    if not raw:
        return {}
    result = {}
    for k in ("domicilio", "datos_complementarios", "ciudad", "email",
              "codigo_postal_zip", "provincia_region", "telefono_fijo",
              "telefono_movil", "fax"):
        if k in raw and raw[k] is not None:
            result[k] = raw[k]
    if "codigo_pais" in raw:
        result["codigo_pais"] = normalizar_pais(raw["codigo_pais"])
    return result


def _norm_dir_esp(raw: dict) -> dict:
    """Devuelve la dirección española tal cual (valores ya numéricos/string)."""
    if not raw:
        return {}
    return {k: v for k, v in raw.items() if v is not None}


# ── Normalizador principal ────────────────────────────────────────────────────

def normalizar_datos(raw: dict) -> dict:
    """
    Normaliza el dict raw del LLM al formato limpio para modelo211_generator.

    Args:
        raw: Dict con estructura pagina_010/020/030 devuelto por el LLM.

    Returns:
        Dict normalizado listo para generar_modelo211().
    """
    p010 = raw.get("pagina_010") or {}
    p020 = raw.get("pagina_020") or {}
    p030 = raw.get("pagina_030") or {}

    # ── Datos base de página 010 ──────────────────────────────────────────────

    header_raw   = p010.get("header") or {}
    adq_raw      = p010.get("adquirente") or {}
    trans_raw    = p010.get("transmitente") or {}
    rep_raw      = p010.get("representante_adquirente") or {}
    inm_raw      = p010.get("inmueble") or {}
    liq_raw      = p010.get("liquidacion") or {}
    comp_raw     = p010.get("complementaria") or {}
    pago_raw     = p010.get("pago") or {}

    fecha_norm = normalizar_fecha(header_raw.get("fecha_devengo", ""))

    importe   = normalizar_importe(liq_raw.get("importe_transmision"))
    pct_ret   = normalizar_importe(liq_raw.get("porcentaje_retencion")) or 3.0
    retencion = normalizar_importe(liq_raw.get("retencion_ingreso_cuenta"))
    if retencion == 0.0 and importe > 0:
        retencion = round(importe * pct_ret / 100, 2)
    result_ant = normalizar_importe(liq_raw.get("resultados_anteriores"))
    resultado  = normalizar_importe(liq_raw.get("resultado_ingresar"))
    if resultado == 0.0:
        resultado = round(retencion - result_ant, 2)

    # Construir adquirente de página 010
    adquirente_010: dict = {
        "nif":               adq_raw.get("nif", ""),
        "apellidos_nombre":  adq_raw.get("apellidos_nombre", ""),
        "fj":                adq_raw.get("fj", "F"),
        "num_adquirentes":   int(adq_raw.get("num_adquirentes", 1)),
        "nif_pais_residencia": adq_raw.get("nif_pais_residencia", ""),
    }
    if adq_raw.get("domicilio_espana"):
        adquirente_010["domicilio_espana"] = _norm_dir_esp(adq_raw["domicilio_espana"])
    if adq_raw.get("direccion_extranjero"):
        adquirente_010["direccion_extranjero"] = _norm_dir_ext(adq_raw["direccion_extranjero"])

    # Construir transmitente de página 010
    transmitente_010: dict = {
        "nif":                           trans_raw.get("nif", ""),
        "fj":                            trans_raw.get("fj", "F"),
        "apellidos_nombre":              trans_raw.get("apellidos_nombre", ""),
        "num_transmitentes":             int(trans_raw.get("num_transmitentes", 1)),
        "nif_pais_residencia":           trans_raw.get("nif_pais_residencia", ""),
        "fecha_nacimiento":              normalizar_fecha(trans_raw.get("fecha_nacimiento", "")),
        "lugar_nacimiento_ciudad":       trans_raw.get("lugar_nacimiento_ciudad", ""),
        "lugar_nacimiento_codigo_pais":  normalizar_pais(trans_raw.get("lugar_nacimiento_codigo_pais", "")),
        "residencia_fiscal_codigo_pais": normalizar_pais(trans_raw.get("residencia_fiscal_codigo_pais", "")),
    }
    if trans_raw.get("direccion_extranjero"):
        transmitente_010["direccion_extranjero"] = _norm_dir_ext(trans_raw["direccion_extranjero"])

    pagina_010 = {
        "header": {
            "tipo_declaracion":  header_raw.get("tipo_declaracion", "I"),
            "fecha_devengo":     fecha_norm,
            "es_complementaria": bool(comp_raw.get("es_complementaria", False)),
        },
        "adquirente":              adquirente_010,
        "representante_adquirente": {
            "nif":              rep_raw.get("nif", ""),
            "fj":               rep_raw.get("fj", ""),
            "apellidos_nombre": rep_raw.get("apellidos_nombre", ""),
            "domicilio":        _norm_dir_esp(rep_raw.get("domicilio") or {}),
        },
        "transmitente": transmitente_010,
        "inmueble": {
            "tipo_via":             inm_raw.get("tipo_via", ""),
            "nombre_via":           inm_raw.get("nombre_via", ""),
            "tipo_numeracion":      inm_raw.get("tipo_numeracion", ""),
            "num_casa":             int(inm_raw.get("num_casa") or 0),
            "calificador":          inm_raw.get("calificador", ""),
            "bloque":               inm_raw.get("bloque", ""),
            "portal":               inm_raw.get("portal", ""),
            "escalera":             inm_raw.get("escalera", ""),
            "planta":               inm_raw.get("planta", ""),
            "puerta":               inm_raw.get("puerta", ""),
            "datos_complementarios":inm_raw.get("datos_complementarios", ""),
            "localidad":            inm_raw.get("localidad", ""),
            "codigo_postal":        int(inm_raw.get("codigo_postal") or 0),
            "municipio":            inm_raw.get("municipio", ""),
            "codigo_ine":           int(inm_raw.get("codigo_ine") or 0),
            "provincia":            int(inm_raw.get("provincia") or 0),
            "referencia_catastral": inm_raw.get("referencia_catastral", ""),
            "tipo_documento":       inm_raw.get("tipo_documento", "P"),
            "notario":              inm_raw.get("notario", ""),
            "num_protocolo":        int(inm_raw.get("num_protocolo") or 0),
        },
        "liquidacion": {
            "importe_transmision":      importe,
            "porcentaje_retencion":     pct_ret,
            "retencion_ingreso_cuenta": retencion,
            "resultados_anteriores":    result_ant,
            "resultado_ingresar":       resultado,
        },
        "complementaria": {
            "es_complementaria":         bool(comp_raw.get("es_complementaria", False)),
            "num_justificante_anterior": int(comp_raw.get("num_justificante_anterior") or 0),
        },
        "pago": {
            "forma_pago": str(pago_raw.get("forma_pago", "1")),
            "iban":       pago_raw.get("iban", ""),
        },
        "contacto_nombre":         p010.get("contacto_nombre", ""),
        "contacto_telefono_fijo":  p010.get("contacto_telefono_fijo", ""),
        "contacto_telefono_movil": p010.get("contacto_telefono_movil", ""),
        "contacto_email":          p010.get("contacto_email", ""),
    }

    # ── Página 020: adquirentes ───────────────────────────────────────────────

    adqs_raw = p020.get("adquirentes") or []

    # Si el LLM no rellenó pagina_020, copiar desde pagina_010.adquirente
    if not adqs_raw and adq_raw:
        adqs_raw = [{
            "nif":                  adq_raw.get("nif", ""),
            "fj":                   adq_raw.get("fj", "F"),
            "apellidos_nombre":     adq_raw.get("apellidos_nombre", ""),
            "nif_pais_residencia":  adq_raw.get("nif_pais_residencia", ""),
            "tipo_cuota":           "C",
            "coef_part_porcentaje": 100.0,
            "domicilio_espana":     adq_raw.get("domicilio_espana"),
            "direccion_extranjero": adq_raw.get("direccion_extranjero"),
        }]

    num_adqs = len(adqs_raw)
    adquirentes_norm = []
    for adq in adqs_raw:
        pct = float(adq.get("coef_part_porcentaje") or (100.0 / num_adqs))
        entry: dict = {
            "nif":                  adq.get("nif", ""),
            "fj":                   adq.get("fj", "F"),
            "apellidos_nombre":     adq.get("apellidos_nombre", ""),
            "nif_pais_residencia":  adq.get("nif_pais_residencia", ""),
            "tipo_cuota":           adq.get("tipo_cuota", "C"),
            "coef_part_centesimas": int(round(pct * 100)),
        }
        if adq.get("domicilio_espana"):
            entry["domicilio_espana"] = _norm_dir_esp(adq["domicilio_espana"])
        if adq.get("direccion_extranjero"):
            entry["direccion_extranjero"] = _norm_dir_ext(adq["direccion_extranjero"])
        adquirentes_norm.append(entry)

    pagina_020 = {"adquirentes": adquirentes_norm}

    # ── Página 030: transmitentes ─────────────────────────────────────────────

    trans_list_raw = p030.get("transmitentes") or []

    # Si el LLM no rellenó pagina_030, copiar desde pagina_010.transmitente
    if not trans_list_raw and trans_raw:
        trans_list_raw = [{
            "nif":                           trans_raw.get("nif", ""),
            "fj":                            trans_raw.get("fj", "F"),
            "apellidos_nombre":              trans_raw.get("apellidos_nombre", ""),
            "tipo_cuota":                    "C",
            "coef_part_porcentaje":          100.0,
            "nif_pais_residencia":           trans_raw.get("nif_pais_residencia", ""),
            "fecha_nacimiento":              trans_raw.get("fecha_nacimiento", ""),
            "lugar_nacimiento_ciudad":       trans_raw.get("lugar_nacimiento_ciudad", ""),
            "lugar_nacimiento_codigo_pais":  trans_raw.get("lugar_nacimiento_codigo_pais", ""),
            "residencia_fiscal_codigo_pais": trans_raw.get("residencia_fiscal_codigo_pais", ""),
            "direccion_extranjero":          trans_raw.get("direccion_extranjero"),
        }]

    num_trans = len(trans_list_raw)
    transmitentes_norm = []
    for t in trans_list_raw:
        pct = float(t.get("coef_part_porcentaje") or (100.0 / num_trans))
        entry = {
            "nif":                           t.get("nif", ""),
            "fj":                            t.get("fj", "F"),
            "apellidos_nombre":              t.get("apellidos_nombre", ""),
            "tipo_cuota":                    t.get("tipo_cuota", "C"),
            "coef_part_centesimas":          int(round(pct * 100)),
            "nif_pais_residencia":           t.get("nif_pais_residencia", ""),
            "fecha_nacimiento":              normalizar_fecha(t.get("fecha_nacimiento", "")),
            "lugar_nacimiento_ciudad":       t.get("lugar_nacimiento_ciudad", ""),
            "lugar_nacimiento_codigo_pais":  normalizar_pais(t.get("lugar_nacimiento_codigo_pais", "")),
            "residencia_fiscal_codigo_pais": normalizar_pais(t.get("residencia_fiscal_codigo_pais", "")),
        }
        if t.get("direccion_extranjero"):
            entry["direccion_extranjero"] = _norm_dir_ext(t["direccion_extranjero"])
        transmitentes_norm.append(entry)

    pagina_030 = {"transmitentes": transmitentes_norm}

    resultado = {
        "pagina_010": pagina_010,
        "pagina_020": pagina_020,
        "pagina_030": pagina_030,
    }
    # Sanitizar TODOS los strings a ASCII puro para garantizar exactamente 6600 bytes
    return _ascii_dict(resultado)
