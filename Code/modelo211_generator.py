"""
modelo211_generator.py
Generador de ficheros de texto del Modelo 211 (AEAT).
IRNR - Retención en la adquisición de bienes inmuebles a no residentes.

Genera SIEMPRE los 3 registros (010 + 020 + 030 = 6600 chars).
"""

import csv
import json
import re
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#  RUTAS Y CONSTANTES
# ─────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent        # MODELIA/Code/
MODELIA_DIR = BASE_DIR.parent              # MODELIA/

CSV_FILES = {
    "010": MODELIA_DIR / "KB" / "21101-Table 1.csv",
    "020": MODELIA_DIR / "KB" / "21102-Table 1.csv",
    "030": MODELIA_DIR / "KB" / "21103-Table 1.csv",
}

TOTAL_LONGITUDES = {
    "010": 2400,
    "020": 2200,
    "030": 2000,
}

# Campos coef_part % que vienen en el JSON ya como enteros en centésimas
# (ej: 100% → 10000) y NO deben multiplicarse por 100.
# El CSV los marca como "3 ent. Y 2 dec." (es_decimal=True), pero se
# sobreescribe su formato a entero puro.
RAW_INT_FIELDS = {
    "020": {11, 46, 81},           # Coef Part % slots 1, 2, 3
    "030": {10, 26, 42, 58, 74},   # Coef Part % slots 1, 2, 3, 4, 5
}


# ─────────────────────────────────────────────────────────────
#  PASO 1: PARSER DE CSVs → field_definitions
# ─────────────────────────────────────────────────────────────

def _extraer_valor_constante(contenido: str):
    """Extrae el literal de 'Constante "VALUE"' en el Contenido del CSV."""
    match = re.search(r'Constante\s+"([^"]*)"', contenido)
    return match.group(1) if match else None


def _detectar_decimales(contenido: str) -> bool:
    """True si el campo tiene decimales implícitos ('ent.' en Contenido)."""
    return "ent." in contenido.lower()


def parse_csv_page(pagina: str) -> list:
    """
    Lee el CSV de la página y devuelve lista de field dicts.
    Salta las 4 filas de cabecera y filtra filas sin Nº numérico.
    """
    csv_path = CSV_FILES[pagina]
    fields = []

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    for row in rows[4:]:
        while len(row) < 7:
            row.append("")
        num_str = row[0].strip()
        if not num_str.isdigit():
            continue

        num         = int(num_str)
        posicion    = int(row[1].strip())
        longitud    = int(row[2].strip())
        tipo        = row[3].strip()
        descripcion = row[4].strip()
        validacion  = row[5].strip()
        contenido   = row[6].strip() if len(row) > 6 else ""

        es_constante    = "Constante" in contenido
        valor_constante = _extraer_valor_constante(contenido) if es_constante else None
        es_decimal      = _detectar_decimales(contenido)
        es_reservado    = "Reservado" in descripcion
        es_fin_registro = "fin de registro" in descripcion.lower()

        fields.append({
            "num":             num,
            "posicion":        posicion,
            "longitud":        longitud,
            "tipo":            tipo,
            "descripcion":     descripcion,
            "validacion":      validacion,
            "contenido":       contenido,
            "es_constante":    es_constante,
            "valor_constante": valor_constante,
            "es_decimal":      es_decimal,
            "num_decimales":   2,
            "es_reservado":    es_reservado,
            "es_fin_registro": es_fin_registro,
        })

    return fields


# ─────────────────────────────────────────────────────────────
#  PASO 2: FORMATEADOR DE CAMPOS
# ─────────────────────────────────────────────────────────────

def formatear_campo(definicion: dict, valor) -> str:
    """
    Formatea un valor a exactamente definicion['longitud'] caracteres.

    Reglas:
      · Constante        → valor literal del CSV
      · Reservado        → espacios
      · An / A           → ljust con espacios
      · Num con decimales → int(round(v * 100)).zfill(n)
      · Num sin decimales → int(v).zfill(n)

    Lanza ValueError si el resultado no tiene la longitud exacta.
    """
    longitud = definicion["longitud"]
    tipo     = definicion["tipo"]

    # ── Constantes ────────────────────────────────────────────
    if definicion["es_constante"]:
        val = definicion["valor_constante"] or ""
        if len(val) == longitud:
            result = val
        elif len(val) < longitud:
            result = val.ljust(longitud)
        else:
            result = val[:longitud]
        if len(result) != longitud:
            raise ValueError(
                f"Campo {definicion['num']}: constante '{val}' → '{result}' "
                f"len={len(result)} != {longitud}"
            )
        return result

    # ── Reservados → espacios ─────────────────────────────────
    if definicion["es_reservado"]:
        return " " * longitud

    # ── Alfanumérico (An, A) ──────────────────────────────────
    if tipo in ("An", "A"):
        s = str(valor) if valor is not None else ""
        result = s[:longitud].ljust(longitud)
        if len(result) != longitud:
            raise ValueError(
                f"Campo {definicion['num']}: An → '{result}' "
                f"len={len(result)} != {longitud}"
            )
        return result

    # ── Numérico con decimales implícitos (×100) ──────────────
    if tipo == "Num" and definicion["es_decimal"]:
        try:
            v = float(valor) if (valor is not None and valor != "") else 0.0
        except (ValueError, TypeError):
            v = 0.0
        int_val = int(round(v * 100))
        result  = str(int_val).zfill(longitud)[-longitud:]
        if len(result) != longitud:
            raise ValueError(
                f"Campo {definicion['num']}: Num/dec → '{result}' "
                f"len={len(result)} != {longitud}"
            )
        return result

    # ── Numérico sin decimales ─────────────────────────────────
    if tipo == "Num":
        try:
            int_val = int(str(valor).strip()) if (valor is not None and str(valor).strip() != "") else 0
        except (ValueError, TypeError):
            int_val = 0
        result = str(int_val).zfill(longitud)[-longitud:]
        if len(result) != longitud:
            raise ValueError(
                f"Campo {definicion['num']}: Num → '{result}' "
                f"len={len(result)} != {longitud}"
            )
        return result

    # ── Fallback ──────────────────────────────────────────────
    s = str(valor) if valor is not None else ""
    return s[:longitud].ljust(longitud)


# ─────────────────────────────────────────────────────────────
#  PASO 3: BUILDERS DE VALORES (pre-build {field_num: value})
# ─────────────────────────────────────────────────────────────

# ─── Mapping página 010 ───────────────────────────────────────
# field_num → tuple de claves para navegar el dict datos_010

MAPPING_010 = {
    6:   ("header", "tipo_declaracion"),
    8:   ("header", "fecha_devengo"),
    9:   ("adquirente", "nif"),
    10:  ("adquirente", "apellidos_nombre"),
    11:  ("adquirente", "fj"),
    12:  ("adquirente", "num_adquirentes"),
    13:  ("adquirente", "nif_pais_residencia"),
    14:  ("adquirente", "domicilio_espana", "tipo_via"),
    15:  ("adquirente", "domicilio_espana", "nombre_via"),
    16:  ("adquirente", "domicilio_espana", "tipo_numeracion"),
    17:  ("adquirente", "domicilio_espana", "num_casa"),
    18:  ("adquirente", "domicilio_espana", "calificador"),
    19:  ("adquirente", "domicilio_espana", "bloque"),
    20:  ("adquirente", "domicilio_espana", "portal"),
    21:  ("adquirente", "domicilio_espana", "escalera"),
    22:  ("adquirente", "domicilio_espana", "planta"),
    23:  ("adquirente", "domicilio_espana", "puerta"),
    24:  ("adquirente", "domicilio_espana", "datos_complementarios"),
    25:  ("adquirente", "domicilio_espana", "localidad"),
    26:  ("adquirente", "domicilio_espana", "codigo_postal"),
    27:  ("adquirente", "domicilio_espana", "municipio"),
    28:  ("adquirente", "domicilio_espana", "codigo_ine"),
    29:  ("adquirente", "domicilio_espana", "provincia"),
    30:  ("adquirente", "domicilio_espana", "telefono_fijo"),
    31:  ("adquirente", "domicilio_espana", "telefono_movil"),
    32:  ("adquirente", "domicilio_espana", "fax"),
    33:  ("adquirente", "direccion_extranjero", "domicilio"),
    34:  ("adquirente", "direccion_extranjero", "datos_complementarios"),
    35:  ("adquirente", "direccion_extranjero", "ciudad"),
    36:  ("adquirente", "direccion_extranjero", "email"),
    37:  ("adquirente", "direccion_extranjero", "codigo_postal_zip"),
    38:  ("adquirente", "direccion_extranjero", "provincia_region"),
    39:  ("adquirente", "direccion_extranjero", "codigo_pais"),
    40:  ("adquirente", "direccion_extranjero", "telefono_fijo"),
    41:  ("adquirente", "direccion_extranjero", "telefono_movil"),
    42:  ("adquirente", "direccion_extranjero", "fax"),
    43:  ("representante_adquirente", "nif"),
    44:  ("representante_adquirente", "fj"),
    45:  ("representante_adquirente", "apellidos_nombre"),
    46:  ("representante_adquirente", "domicilio", "tipo_via"),
    47:  ("representante_adquirente", "domicilio", "nombre_via"),
    48:  ("representante_adquirente", "domicilio", "tipo_numeracion"),
    49:  ("representante_adquirente", "domicilio", "num_casa"),
    50:  ("representante_adquirente", "domicilio", "calificador"),
    51:  ("representante_adquirente", "domicilio", "bloque"),
    52:  ("representante_adquirente", "domicilio", "portal"),
    53:  ("representante_adquirente", "domicilio", "escalera"),
    54:  ("representante_adquirente", "domicilio", "planta"),
    55:  ("representante_adquirente", "domicilio", "puerta"),
    56:  ("representante_adquirente", "domicilio", "datos_complementarios"),
    57:  ("representante_adquirente", "domicilio", "localidad"),
    58:  ("representante_adquirente", "domicilio", "codigo_postal"),
    59:  ("representante_adquirente", "domicilio", "municipio"),
    60:  ("representante_adquirente", "domicilio", "codigo_ine"),
    61:  ("representante_adquirente", "domicilio", "provincia"),
    62:  ("representante_adquirente", "domicilio", "telefono_fijo"),
    63:  ("representante_adquirente", "domicilio", "telefono_movil"),
    64:  ("representante_adquirente", "domicilio", "fax"),
    65:  ("transmitente", "nif"),
    66:  ("transmitente", "fj"),
    67:  ("transmitente", "apellidos_nombre"),
    68:  ("transmitente", "num_transmitentes"),
    69:  ("transmitente", "nif_pais_residencia"),
    70:  ("transmitente", "fecha_nacimiento"),
    71:  ("transmitente", "lugar_nacimiento_ciudad"),
    72:  ("transmitente", "lugar_nacimiento_codigo_pais"),
    73:  ("transmitente", "residencia_fiscal_codigo_pais"),
    74:  ("transmitente", "direccion_extranjero", "domicilio"),
    75:  ("transmitente", "direccion_extranjero", "datos_complementarios"),
    76:  ("transmitente", "direccion_extranjero", "ciudad"),
    77:  ("transmitente", "direccion_extranjero", "codigo_postal_zip"),
    78:  ("transmitente", "direccion_extranjero", "provincia_region"),
    79:  ("transmitente", "direccion_extranjero", "codigo_pais"),
    80:  ("inmueble", "tipo_via"),
    81:  ("inmueble", "nombre_via"),
    82:  ("inmueble", "tipo_numeracion"),
    83:  ("inmueble", "num_casa"),
    84:  ("inmueble", "calificador"),
    85:  ("inmueble", "bloque"),
    86:  ("inmueble", "portal"),
    87:  ("inmueble", "escalera"),
    88:  ("inmueble", "planta"),
    89:  ("inmueble", "puerta"),
    90:  ("inmueble", "datos_complementarios"),
    91:  ("inmueble", "localidad"),
    92:  ("inmueble", "codigo_postal"),
    93:  ("inmueble", "municipio"),
    94:  ("inmueble", "codigo_ine"),
    95:  ("inmueble", "provincia"),
    96:  ("inmueble", "referencia_catastral"),
    97:  ("inmueble", "tipo_documento"),
    98:  ("inmueble", "notario"),
    99:  ("inmueble", "num_protocolo"),
    100: ("liquidacion", "importe_transmision"),
    101: ("liquidacion", "porcentaje_retencion"),
    102: ("liquidacion", "retencion_ingreso_cuenta"),
    103: ("liquidacion", "resultados_anteriores"),
    104: ("liquidacion", "resultado_ingresar"),
    # 105 → campo especial: indicador complementaria (se calcula abajo)
    106: ("complementaria", "num_justificante_anterior"),
    107: ("pago", "forma_pago"),
    108: ("pago", "iban"),
    110: ("contacto_nombre",),
    111: ("contacto_telefono_fijo",),
    112: ("contacto_telefono_movil",),
    113: ("contacto_email",),
}


def _get_valor_raw(ruta: tuple, datos: dict):
    """Navega el dict de datos siguiendo la tupla de claves."""
    obj = datos
    for key in ruta:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def _build_valores_010(datos: dict) -> dict:
    """Construye {field_num: value} para la página 010."""
    valores = {}
    for num, ruta in MAPPING_010.items():
        valores[num] = _get_valor_raw(ruta, datos)
    # Campo 105: indicador complementaria
    complementaria = datos.get("complementaria") or {}
    es_comp = complementaria.get("es_complementaria", False)
    valores[105] = "X" if es_comp else " "
    return valores


# ─── Builders para páginas 020 y 030 ──────────────────────────

def _slot_adquirente(adq: dict) -> dict:
    """
    Devuelve {offset: value} para un slot de adquirente (35 campos).
    Offsets 0-34 corresponden a los campos 6-40 del slot 1,
    41-75 del slot 2, 76-110 del slot 3.
    """
    adq     = adq or {}
    dom_esp = adq.get("domicilio_espana") or {}
    dir_ext = adq.get("direccion_extranjero") or {}
    return {
        0:  adq.get("nif", ""),
        1:  adq.get("fj", ""),
        2:  adq.get("apellidos_nombre", ""),
        3:  adq.get("nif_pais_residencia", ""),
        4:  adq.get("tipo_cuota", ""),               # C/O
        5:  adq.get("coef_part_centesimas", 0),       # RAW INT (ya en centésimas)
        6:  dom_esp.get("tipo_via", ""),
        7:  dom_esp.get("nombre_via", ""),
        8:  dom_esp.get("tipo_numeracion", ""),
        9:  dom_esp.get("num_casa", 0),
        10: dom_esp.get("calificador", ""),
        11: dom_esp.get("bloque", ""),
        12: dom_esp.get("portal", ""),
        13: dom_esp.get("escalera", ""),
        14: dom_esp.get("planta", ""),
        15: dom_esp.get("puerta", ""),
        16: dom_esp.get("datos_complementarios", ""),
        17: dom_esp.get("localidad", ""),
        18: dom_esp.get("codigo_postal", 0),
        19: dom_esp.get("municipio", ""),
        20: dom_esp.get("codigo_ine", 0),
        21: dom_esp.get("provincia", 0),
        22: dom_esp.get("telefono_fijo", 0),
        23: dom_esp.get("telefono_movil", 0),
        24: dom_esp.get("fax", 0),
        25: dir_ext.get("domicilio", ""),
        26: dir_ext.get("datos_complementarios", ""),
        27: dir_ext.get("ciudad", ""),
        28: dir_ext.get("email", ""),
        29: dir_ext.get("codigo_postal_zip", ""),
        30: dir_ext.get("provincia_region", ""),
        31: dir_ext.get("codigo_pais", ""),
        32: dir_ext.get("telefono_fijo", ""),
        33: dir_ext.get("telefono_movil", ""),
        34: dir_ext.get("fax", ""),
    }


def _build_valores_020(adquirentes: list) -> dict:
    """
    Construye {field_num: value} para la página 020 (3 slots fijos).
    Slots vacíos → ceros/espacios automáticamente.
    Bases de campo: slot1=6, slot2=41, slot3=76.
    """
    slots = list(adquirentes[:3])
    while len(slots) < 3:
        slots.append(None)

    SLOT_BASES = [6, 41, 76]
    valores = {}
    for i, base in enumerate(SLOT_BASES):
        for offset, val in _slot_adquirente(slots[i]).items():
            valores[base + offset] = val
    return valores


def _slot_transmitente(t: dict) -> dict:
    """
    Devuelve {offset: value} para un slot de transmitente (16 campos).
    Offsets 0-15 corresponden a los campos de cada slot en la página 030.
    """
    t       = t or {}
    dir_ext = t.get("direccion_extranjero") or {}
    return {
        0:  t.get("nif", ""),
        1:  t.get("fj", ""),
        2:  t.get("apellidos_nombre", ""),
        3:  t.get("tipo_cuota", ""),               # C/O
        4:  t.get("coef_part_centesimas", 0),       # RAW INT
        5:  t.get("nif_pais_residencia", ""),
        6:  t.get("fecha_nacimiento", ""),
        7:  t.get("lugar_nacimiento_ciudad", ""),
        8:  t.get("lugar_nacimiento_codigo_pais", ""),
        9:  t.get("residencia_fiscal_codigo_pais", ""),
        10: dir_ext.get("domicilio", ""),
        11: dir_ext.get("datos_complementarios", ""),
        12: dir_ext.get("ciudad", ""),
        13: dir_ext.get("codigo_postal_zip", ""),
        14: dir_ext.get("provincia_region", ""),
        15: dir_ext.get("codigo_pais", ""),
    }


def _build_valores_030(transmitentes: list) -> dict:
    """
    Construye {field_num: value} para la página 030 (5 slots fijos).
    Slots vacíos → ceros/espacios automáticamente.
    Bases de campo: slot1=6, slot2=22, slot3=38, slot4=54, slot5=70.
    """
    slots = list(transmitentes[:5])
    while len(slots) < 5:
        slots.append(None)

    SLOT_BASES = [6, 22, 38, 54, 70]
    valores = {}
    for i, base in enumerate(SLOT_BASES):
        for offset, val in _slot_transmitente(slots[i]).items():
            valores[base + offset] = val
    return valores


# ─────────────────────────────────────────────────────────────
#  PASO 4: GENERADOR DE JSON INTERMEDIO
# ─────────────────────────────────────────────────────────────

def generar_json_formateado(pagina: str, field_defs: list,
                            valores: dict, raw_int_fields: set = None) -> dict:
    """
    Para cada campo del CSV genera el dict diagnóstico con valor_raw y
    valor_formateado.

    Args:
        pagina         : "010", "020" o "030"
        field_defs     : salida de parse_csv_page
        valores        : {field_num: value} pre-construido
        raw_int_fields : set de field_num cuyo Num es ya entero (sin ×100)
    """
    raw_int_fields = raw_int_fields or set()
    campos_resultado = []
    campos_ok    = 0
    campos_error = 0

    for field in field_defs:
        num     = field["num"]
        longitud = field["longitud"]

        # ── Valor raw ─────────────────────────────────────────
        if field["es_constante"] or field["es_reservado"]:
            valor_raw = field.get("valor_constante") or ""
        elif num in valores:
            valor_raw = valores[num]
            if valor_raw is None:
                valor_raw = "" if field["tipo"] in ("An", "A") else 0
        else:
            valor_raw = "" if field["tipo"] in ("An", "A") else 0

        # ── Formatear ─────────────────────────────────────────
        # Los campos coef_part traen el entero ya listo (p.ej. 10000 para 100%):
        # sobreescribir es_decimal=False para que no se multiplique ×100.
        if num in raw_int_fields and field["tipo"] == "Num" and field["es_decimal"]:
            field_def = dict(field, es_decimal=False)
        else:
            field_def = field

        try:
            valor_formateado    = formatear_campo(field_def, valor_raw)
            longitud_verificada = len(valor_formateado)
            ok = longitud_verificada == longitud
        except Exception as e:
            valor_formateado    = f"ERROR: {e}"
            longitud_verificada = 0
            ok = False

        if ok:
            campos_ok += 1
        else:
            campos_error += 1

        campos_resultado.append({
            "num":                 num,
            "posicion":            field["posicion"],
            "longitud":            longitud,
            "tipo":                field["tipo"],
            "descripcion":         field["descripcion"],
            "valor_raw":           str(valor_raw) if valor_raw is not None else "",
            "valor_formateado":    valor_formateado,
            "longitud_verificada": longitud_verificada,
            "ok":                  ok,
        })

    return {
        "pagina":            pagina,
        "longitud_total":    TOTAL_LONGITUDES[pagina],
        "longitud_generada": None,
        "campos_ok":         campos_ok,
        "campos_error":      campos_error,
        "todos_ok":          campos_error == 0,
        "campos":            campos_resultado,
    }


# ─────────────────────────────────────────────────────────────
#  PASO 5: ENSAMBLADOR DE REGISTRO DE TEXTO
# ─────────────────────────────────────────────────────────────

def json_a_registro(diagnostico: dict) -> str:
    """
    Construye el registro de longitud fija insertando cada campo en
    posicion-1 (base 0). Verifica longitud, tag de inicio y tag de fin.
    """
    pagina         = diagnostico["pagina"]
    longitud_total = TOTAL_LONGITUDES[pagina]

    registro = list(" " * longitud_total)
    for campo in diagnostico["campos"]:
        pos_base0 = campo["posicion"] - 1
        for i, ch in enumerate(campo["valor_formateado"]):
            idx = pos_base0 + i
            if idx < longitud_total:
                registro[idx] = ch

    texto  = "".join(registro)
    inicio = f"<T211{pagina}>"
    fin    = f"</T211{pagina}>"

    if len(texto) != longitud_total:
        raise ValueError(f"Pág {pagina}: longitud {len(texto)} != {longitud_total}")
    if not texto.startswith(inicio):
        raise ValueError(
            f"Pág {pagina}: no empieza con '{inicio}'. Primeros 10: '{texto[:10]}'"
        )
    if not texto.endswith(fin):
        raise ValueError(
            f"Pág {pagina}: no termina con '{fin}'. Últimos 15: '{texto[-15:]}'"
        )

    diagnostico["longitud_generada"] = len(texto)
    return texto


# ─────────────────────────────────────────────────────────────
#  PASO 6: ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────

def generar_modelo211(datos_json_path, output_path=None):
    """
    Orquestador principal.

    Genera SIEMPRE los 3 registros (010 + 020 + 030), total 6600 chars.
    Los slots vacíos en páginas 020 y 030 se rellenan con ceros/espacios.

    Args:
        datos_json_path : ruta al JSON de entrada
        output_path     : directorio de salida (por defecto MODELIA/Output/)

    Returns:
        Texto final completo (str, 6600 chars).
    """
    datos_json_path = Path(datos_json_path)
    if output_path is None:
        output_path = MODELIA_DIR / "Output"
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(datos_json_path, encoding="utf-8") as f:
        datos_completos = json.load(f)

    datos_010     = datos_completos.get("pagina_010", {})
    adquirentes   = datos_completos.get("pagina_020", {}).get("adquirentes", [])
    transmitentes = datos_completos.get("pagina_030", {}).get("transmitentes", [])

    print(f"\n{'='*60}")
    print(f"  GENERADOR MODELO 211 - AEAT")
    print(f"{'='*60}")
    print(f"  Datos    : {datos_json_path.name}")
    print(f"  Salida   : {output_path}")
    print(f"  Páginas  : 010 + 020 + 030 (siempre, total 6600 chars)")
    print(f"  Adqs p020: {len(adquirentes)} slot(s) informado(s) de 3")
    print(f"  Trans p030: {len(transmitentes)} slot(s) informado(s) de 5")

    # Pre-construir valores para cada página
    pipeline = [
        ("010", parse_csv_page("010"), _build_valores_010(datos_010),           None),
        ("020", parse_csv_page("020"), _build_valores_020(adquirentes),   RAW_INT_FIELDS["020"]),
        ("030", parse_csv_page("030"), _build_valores_030(transmitentes), RAW_INT_FIELDS["030"]),
    ]

    registros = []

    for pagina, field_defs, valores, raw_int_flds in pipeline:
        lng_esp = TOTAL_LONGITUDES[pagina]
        print(f"\n{'─'*60}")
        print(f"  Pág {pagina}  ({lng_esp} chars, {len(field_defs)} campos)")

        diag = generar_json_formateado(pagina, field_defs, valores, raw_int_flds)

        try:
            registro = json_a_registro(diag)
        except ValueError as e:
            print(f"  ERROR al ensamblar: {e}")
            raise

        registros.append(registro)

        # Guardar diagnóstico
        diag_path = output_path / f"diagnostico_{pagina}.json"
        with open(diag_path, "w", encoding="utf-8") as f:
            json.dump(diag, f, ensure_ascii=False, indent=2)

        total_c = diag["campos_ok"] + diag["campos_error"]
        print(f"  Longitud  : {len(registro)} / {lng_esp} chars")
        print(f"  Campos OK : {diag['campos_ok']} / {total_c}")

        if not diag["todos_ok"]:
            print(f"  CAMPOS CON ERROR:")
            for c in diag["campos"]:
                if not c["ok"]:
                    print(
                        f"    Campo {c['num']:3d} [pos={c['posicion']:5d} lon={c['longitud']:3d}] "
                        f"{c['descripcion'][:45]}"
                    )
                    print(f"           raw='{c['valor_raw']}'  fmt='{c['valor_formateado']}'")

    # Fichero final (sin saltos de línea)
    texto_final = "".join(registros)
    txt_path = output_path / "211.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(texto_final)

    print(f"\n{'='*60}")
    print(f"  COMPLETADO")
    print(f"{'='*60}")
    print(f"  Fichero : {txt_path}")
    print(f"  Total   : {len(texto_final)} chars (esperado: 6600)")
    print(f"\n  Verificaciones por página:")
    for pagina, registro in zip(["010", "020", "030"], registros):
        lng    = TOTAL_LONGITUDES[pagina]
        ok_lng = len(registro) == lng
        ok_ini = registro.startswith(f"<T211{pagina}>")
        ok_fin = registro.endswith(f"</T211{pagina}>")
        est    = "OK" if (ok_lng and ok_ini and ok_fin) else "ERROR"
        print(
            f"  [{est}] Pág {pagina}: len={len(registro)} "
            f"inicio={'✓' if ok_ini else '✗'}  fin={'✓' if ok_fin else '✗'}"
        )

    return texto_final
