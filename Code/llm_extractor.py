"""
llm_extractor.py
Extrae campos del Modelo 211 de un texto notarial usando GPT-5 (OpenAI).
Usa function calling para obtener un JSON estructurado sin alucinaciones.
"""

import json
from openai import OpenAI


# ── Helpers de schema ─────────────────────────────────────────────────────────

def _dir_espana_props() -> dict:
    return {
        "tipo_via":              {"type": "string", "description": "Tipo de vía: CALLE, AVDA, PLAZA, etc."},
        "nombre_via":            {"type": "string", "description": "Nombre de la vía"},
        "tipo_numeracion":       {"type": "string", "description": "Tipo numeración: NUM, KM, S/N, etc."},
        "num_casa":              {"type": "integer", "description": "Número de la casa/portal"},
        "calificador":           {"type": "string"},
        "bloque":                {"type": "string"},
        "portal":                {"type": "string"},
        "escalera":              {"type": "string"},
        "planta":                {"type": "string"},
        "puerta":                {"type": "string"},
        "datos_complementarios": {"type": "string"},
        "localidad":             {"type": "string", "description": "Localidad en mayúsculas sin tildes"},
        "codigo_postal":         {"type": "integer", "description": "Código postal (5 dígitos)"},
        "municipio":             {"type": "string", "description": "Nombre del municipio en ASCII sin tildes"},
        "codigo_ine":            {"type": "integer", "description": "Código INE del municipio (5 dígitos)"},
        "provincia":             {"type": "integer", "description": "Código numérico de provincia (01-52)"},
        "telefono_fijo":         {"type": "integer"},
        "telefono_movil":        {"type": "integer"},
        "fax":                   {"type": "integer"},
    }


def _dir_extranjero_props() -> dict:
    return {
        "domicilio":             {"type": "string", "description": "Calle y número en el extranjero"},
        "datos_complementarios": {"type": "string"},
        "ciudad":                {"type": "string", "description": "Ciudad en mayúsculas sin tildes"},
        "email":                 {"type": "string"},
        "codigo_postal_zip":     {"type": "string"},
        "provincia_region":      {"type": "string"},
        "codigo_pais":           {"type": "string", "description": "Código ISO 3166-1 alpha-2 (ej: NO, IE, GB, DE)"},
        "telefono_fijo":         {"type": "string"},
        "telefono_movil":        {"type": "string"},
        "fax":                   {"type": "string"},
    }


# ── Schema de la herramienta (formato OpenAI function calling) ────────────────

EXTRACT_FUNCTION = {
    "type": "function",
    "function": {
        "name": "extract_modelo211",
        "description": (
            "Extrae todos los campos necesarios para generar el Modelo 211 (AEAT) "
            "de una escritura notarial de compraventa de inmueble. "
            "Rellena solo los campos que encuentres con certeza en el documento."
        ),
        "parameters": {
            "type": "object",
            "required": ["pagina_010", "pagina_020", "pagina_030"],
            "properties": {

                # ── Página 010 ────────────────────────────────────────────────
                "pagina_010": {
                    "type": "object",
                    "description": "Datos generales de la operación",
                    "properties": {

                        "header": {
                            "type": "object",
                            "properties": {
                                "tipo_declaracion": {
                                    "type": "string",
                                    "description": "I=ingreso (operación normal), N=negativa, C=complementaria",
                                    "enum": ["I", "N", "C"],
                                },
                                "fecha_devengo": {
                                    "type": "string",
                                    "description": "Fecha de la escritura / fecha de la operación. Cualquier formato.",
                                },
                            },
                        },

                        "adquirente": {
                            "type": "object",
                            "description": "Comprador del inmueble",
                            "properties": {
                                "nif":                {"type": "string", "description": "NIF/NIE/CIF del comprador"},
                                "apellidos_nombre":   {"type": "string", "description": "APELLIDOS, NOMBRE en mayúsculas sin tildes"},
                                "fj":                 {"type": "string", "description": "F=persona física, J=persona jurídica", "enum": ["F", "J"]},
                                "num_adquirentes":    {"type": "integer", "description": "Número total de compradores"},
                                "nif_pais_residencia":{"type": "string", "description": "NIF fiscal del país de residencia (extranjero)"},
                                "domicilio_espana":   {"type": "object", "properties": _dir_espana_props()},
                                "direccion_extranjero":{"type": "object", "properties": _dir_extranjero_props()},
                            },
                        },

                        "representante_adquirente": {
                            "type": "object",
                            "description": "Representante, gestoría o abogado del adquirente (si actúa en su nombre)",
                            "properties": {
                                "nif":              {"type": "string", "description": "NIF/CIF del representante"},
                                "fj":               {"type": "string", "description": "F=física, J=jurídica", "enum": ["F", "J"]},
                                "apellidos_nombre": {"type": "string"},
                                "domicilio":        {"type": "object", "properties": _dir_espana_props()},
                            },
                        },

                        "transmitente": {
                            "type": "object",
                            "description": "Vendedor del inmueble (no residente en España)",
                            "properties": {
                                "nif":                           {"type": "string", "description": "NIF/NIE del vendedor"},
                                "fj":                            {"type": "string", "description": "F=física, J=jurídica", "enum": ["F", "J"]},
                                "apellidos_nombre":              {"type": "string", "description": "APELLIDOS, NOMBRE en mayúsculas sin tildes"},
                                "num_transmitentes":             {"type": "integer", "description": "Número total de vendedores"},
                                "nif_pais_residencia":           {"type": "string"},
                                "fecha_nacimiento":              {"type": "string", "description": "Fecha de nacimiento. Cualquier formato."},
                                "lugar_nacimiento_ciudad":       {"type": "string", "description": "Ciudad de nacimiento en mayúsculas"},
                                "lugar_nacimiento_codigo_pais":  {"type": "string", "description": "Código ISO país de nacimiento"},
                                "residencia_fiscal_codigo_pais": {"type": "string", "description": "Código ISO país de residencia fiscal"},
                                "direccion_extranjero":          {"type": "object", "properties": _dir_extranjero_props()},
                            },
                        },

                        "inmueble": {
                            "type": "object",
                            "description": "Dirección y datos del inmueble transmitido",
                            "properties": {
                                "tipo_via":             {"type": "string", "description": "CALLE, AVDA, PLAZA, PASEO, etc."},
                                "nombre_via":           {"type": "string"},
                                "tipo_numeracion":      {"type": "string", "description": "NUM, KM, S/N, etc."},
                                "num_casa":             {"type": "integer"},
                                "calificador":          {"type": "string"},
                                "bloque":               {"type": "string"},
                                "portal":               {"type": "string"},
                                "escalera":             {"type": "string"},
                                "planta":               {"type": "string"},
                                "puerta":               {"type": "string"},
                                "datos_complementarios":{"type": "string", "description": "Datos adicionales de la dirección (urbanización, etc.)"},
                                "localidad":            {"type": "string"},
                                "codigo_postal":        {"type": "integer"},
                                "municipio":            {"type": "string", "description": "Municipio en ASCII sin tildes"},
                                "codigo_ine":           {"type": "integer", "description": "Código INE municipio (5 dígitos)"},
                                "provincia":            {"type": "integer", "description": "Código numérico provincia"},
                                "referencia_catastral": {"type": "string", "description": "Referencia catastral (hasta 20 caracteres)"},
                                "tipo_documento":       {"type": "string", "description": "P=protocolo notarial"},
                                "notario":              {"type": "string", "description": "Nombre completo del notario en mayúsculas"},
                                "num_protocolo":        {"type": "integer", "description": "Número de protocolo notarial"},
                            },
                        },

                        "liquidacion": {
                            "type": "object",
                            "description": "Datos económicos de la retención",
                            "properties": {
                                "importe_transmision":      {"type": "number", "description": "Precio de venta en euros (número sin símbolo €)"},
                                "porcentaje_retencion":     {"type": "number", "description": "Porcentaje de retención (normalmente 3.00)"},
                                "retencion_ingreso_cuenta": {"type": "number", "description": "Importe retención = importe × porcentaje / 100"},
                                "resultados_anteriores":    {"type": "number", "description": "Resultado de declaraciones anteriores (normalmente 0)"},
                                "resultado_ingresar":       {"type": "number", "description": "Importe a ingresar (normalmente = retencion_ingreso_cuenta)"},
                            },
                        },

                        "complementaria": {
                            "type": "object",
                            "properties": {
                                "es_complementaria":          {"type": "boolean", "description": "True solo si esta es una declaración complementaria"},
                                "num_justificante_anterior":  {"type": "integer", "description": "Nº justificante de la declaración anterior (si es complementaria)"},
                            },
                        },

                        "pago": {
                            "type": "object",
                            "properties": {
                                "forma_pago": {"type": "string", "description": "1=cargo en cuenta, 2=NRC, 3=reconocimiento deuda"},
                                "iban":       {"type": "string", "description": "IBAN para cargo en cuenta (si aplica)"},
                            },
                        },
                    },
                },

                # ── Página 020 ────────────────────────────────────────────────
                "pagina_020": {
                    "type": "object",
                    "description": "Lista de compradores (adquirentes)",
                    "properties": {
                        "adquirentes": {
                            "type": "array",
                            "description": (
                                "Lista de compradores. Si solo hay 1 comprador incluir 1 elemento. "
                                "Máximo 3 elementos."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "nif":                 {"type": "string"},
                                    "fj":                  {"type": "string", "enum": ["F", "J"]},
                                    "apellidos_nombre":    {"type": "string"},
                                    "nif_pais_residencia": {"type": "string"},
                                    "tipo_cuota":          {"type": "string", "description": "C=cuota de participación informada", "enum": ["C", "O"]},
                                    "coef_part_porcentaje":{"type": "number", "description": "Porcentaje de participación 0-100. Ej: 100 si es propietario único, 50 si son dos al 50%."},
                                    "domicilio_espana":    {"type": "object", "properties": _dir_espana_props()},
                                    "direccion_extranjero":{"type": "object", "properties": _dir_extranjero_props()},
                                },
                            },
                        },
                    },
                },

                # ── Página 030 ────────────────────────────────────────────────
                "pagina_030": {
                    "type": "object",
                    "description": "Lista de vendedores no residentes (transmitentes)",
                    "properties": {
                        "transmitentes": {
                            "type": "array",
                            "description": (
                                "Lista de vendedores. Si solo hay 1 vendedor incluir 1 elemento. "
                                "Máximo 5 elementos."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "nif":                           {"type": "string"},
                                    "fj":                            {"type": "string", "enum": ["F", "J"]},
                                    "apellidos_nombre":              {"type": "string"},
                                    "tipo_cuota":                    {"type": "string", "enum": ["C", "O"]},
                                    "coef_part_porcentaje":          {"type": "number", "description": "Porcentaje de participación 0-100"},
                                    "nif_pais_residencia":           {"type": "string"},
                                    "fecha_nacimiento":              {"type": "string", "description": "Fecha de nacimiento. Cualquier formato."},
                                    "lugar_nacimiento_ciudad":       {"type": "string"},
                                    "lugar_nacimiento_codigo_pais":  {"type": "string", "description": "Código ISO país de nacimiento"},
                                    "residencia_fiscal_codigo_pais": {"type": "string", "description": "Código ISO país de residencia fiscal"},
                                    "direccion_extranjero":          {"type": "object", "properties": _dir_extranjero_props()},
                                },
                            },
                        },
                    },
                },

            },
        },
    },
}


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un experto en derecho notarial español y tributación de no residentes (IRNR).

Tu tarea es extraer los datos de una escritura notarial de compraventa de inmueble para cumplimentar el Modelo 211 de la AEAT (Retención IRNR en la adquisición de bienes inmuebles a no residentes sin establecimiento permanente en España).

Instrucciones:
1. Extrae SOLO los datos que encuentres claramente en el documento. Si un dato no está presente o no estás seguro, omite ese campo (no inventes valores).
2. Para fechas escritas en dígitos (DD/MM/YYYY, DD-MM-YYYY, etc.): extráelas tal cual.
   Para fechas escritas EN LETRAS como "a veintinueve de abril del dos mil veinticinco":
   convierte los números a dígitos antes de devolverlos → "29/04/2025".
   Otros ejemplos: "a uno de enero de dos mil veinticuatro" → "01/01/2024",
   "treinta y uno de diciembre de dos mil" → "31/12/2000".
   La fecha de devengo es la fecha de firma de la escritura notarial (fecha del otorgamiento).
3. Para importes: extrae como número (sin símbolo €). Ejemplo: "102.000 €" → 102000.
4. Para países: usa el código ISO 3166-1 alpha-2 de 2 letras (ES, GB, NO, IE, DE, FR, etc.).
5. Para nombres: escríbelos en MAYÚSCULAS y sin caracteres especiales (sin tildes, ñ → N).
6. El transmitente (vendedor) es SIEMPRE no residente en España.
7. El porcentaje de retención habitual es 3% (salvo indicación contraria en el documento).
8. La retención a ingresar = importe_transmision × porcentaje_retencion / 100.
9. El coeficiente de participación (coef_part_porcentaje) es 100 cuando hay un único adquirente o transmitente.
10. Sé conservador: mejor dejar un campo vacío que inventar un valor incorrecto."""


# ── Función principal ─────────────────────────────────────────────────────────

def extraer_campos_llm(texto: str, api_key: str) -> dict:
    """
    Extrae los campos del Modelo 211 del texto usando GPT-5 (OpenAI) con function calling.

    Args:
        texto:   Texto extraído del PDF notarial.
        api_key: API key de OpenAI.

    Returns:
        Dict con estructura pagina_010 / pagina_020 / pagina_030.

    Raises:
        RuntimeError: Si el modelo no devuelve un function call válido.
    """
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extrae los datos del siguiente documento notarial:\n\n{texto}"},
        ],
        tools=[EXTRACT_FUNCTION],
        tool_choice={"type": "function", "function": {"name": "extract_modelo211"}},
    )

    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == "extract_modelo211":
                return json.loads(tool_call.function.arguments)

    raise RuntimeError("El modelo no devolvió ningún function call.")
