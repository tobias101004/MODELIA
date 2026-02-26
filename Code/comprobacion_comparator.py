"""
comprobacion_comparator.py
Comparación determinista de datos extraídos de escritura, Modelo 211 y Modelo 600.
Sin llamadas a LLM — 100% Python puro.
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


def _norm_date(val) -> str:
    """Normaliza fecha a DDMMYYYY para comparación."""
    if not val:
        return ""
    s = str(val).strip()
    # Ya DDMMYYYY
    if re.fullmatch(r"\d{8}", s):
        return s
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", s)
    if m:
        return f"{m.group(1).zfill(2)}{m.group(2).zfill(2)}{m.group(3)}"
    # YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", s)
    if m:
        return f"{m.group(3).zfill(2)}{m.group(2).zfill(2)}{m.group(1)}"
    return _ascii(s).upper().strip()


def _norm_address(val) -> str:
    """Normaliza dirección: ASCII, mayúsculas, sin puntuación extra."""
    if not val:
        return ""
    s = _ascii(str(val)).upper().strip()
    s = re.sub(r"[,.\-;:]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_generic(val) -> str:
    """Normalización genérica: ASCII, mayúsculas, trim."""
    if not val:
        return ""
    return _ascii(str(val)).upper().strip()


# ── Tipos de campo y su normalizador ────────────────────────────────────────

_NIF_FIELDS = {"comprador_nif", "vendedor_nif", "sujeto_pasivo_nif"}
_NAME_FIELDS = {"comprador_nombre", "vendedor_nombre", "sujeto_pasivo_nombre", "notario_nombre"}
_AMOUNT_FIELDS = {"importe_transmision", "porcentaje_retencion", "importe_retencion",
                  "resultado_ingresar", "base_imponible", "tipo_gravamen", "cuota_tributaria"}
_DATE_FIELDS = {"fecha_operacion", "vendedor_fecha_nacimiento"}
_ADDRESS_FIELDS = {"comprador_domicilio", "vendedor_domicilio", "inmueble_direccion"}


def _compare_field(campo: str, val_a, val_b) -> bool:
    """Compara dos valores de un campo usando la normalización adecuada."""
    if campo in _NIF_FIELDS:
        return _norm_nif(val_a) == _norm_nif(val_b)
    if campo in _NAME_FIELDS:
        return _norm_name(val_a) == _norm_name(val_b)
    if campo in _AMOUNT_FIELDS:
        return abs(_norm_amount(val_a) - _norm_amount(val_b)) < 0.02
    if campo in _DATE_FIELDS:
        return _norm_date(val_a) == _norm_date(val_b)
    if campo in _ADDRESS_FIELDS:
        return _norm_address(val_a) == _norm_address(val_b)
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
            # Only flag if the model has a value but escritura doesn't, or vice versa
            if val_a is not None and val_a != "" and (val_b is None or val_b == ""):
                continue  # Source has value, model doesn't — might just not be in model
            if val_b is not None and val_b != "" and (val_a is None or val_a == ""):
                continue
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
