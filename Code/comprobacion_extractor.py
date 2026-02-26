"""
comprobacion_extractor.py
Extrae datos estructurados de escritura, Modelo 211 y Modelo 600 usando GPT-4o
con function calling, para la verificación cruzada (comprobación).
"""

import json
from openai import OpenAI


# ── Schemas comunes ──────────────────────────────────────────────────────────

_COMMON_BUYER_PROPS = {
    "comprador_nif":        {"type": "string", "description": "NIF/NIE/CIF del comprador"},
    "comprador_nombre":     {"type": "string", "description": "Nombre completo del comprador en MAYUSCULAS"},
    "comprador_domicilio":  {"type": "string", "description": "Dirección completa del comprador"},
    "comprador_cp":         {"type": "string", "description": "Código postal del comprador"},
    "comprador_municipio":  {"type": "string", "description": "Municipio del comprador"},
    "comprador_provincia":  {"type": "string", "description": "Provincia del comprador"},
}

_COMMON_SELLER_PROPS = {
    "vendedor_nif":               {"type": "string", "description": "NIF/NIE del vendedor"},
    "vendedor_nombre":            {"type": "string", "description": "Nombre completo del vendedor en MAYUSCULAS"},
    "vendedor_pais_residencia":   {"type": "string", "description": "País de residencia fiscal del vendedor (código ISO o nombre)"},
    "vendedor_fecha_nacimiento":  {"type": "string", "description": "Fecha de nacimiento del vendedor (cualquier formato)"},
    "vendedor_domicilio":         {"type": "string", "description": "Dirección del vendedor en el extranjero"},
}

_COMMON_PROPERTY_PROPS = {
    "inmueble_direccion":      {"type": "string", "description": "Dirección completa del inmueble"},
    "inmueble_cp":             {"type": "string", "description": "Código postal del inmueble"},
    "inmueble_municipio":      {"type": "string", "description": "Municipio del inmueble"},
    "inmueble_provincia":      {"type": "string", "description": "Provincia del inmueble"},
    "inmueble_ref_catastral":  {"type": "string", "description": "Referencia catastral del inmueble"},
}

_COMMON_TRANSACTION_PROPS = {
    "importe_transmision":  {"type": "number", "description": "Precio de compraventa en euros (número sin símbolo €)"},
    "fecha_operacion":      {"type": "string", "description": "Fecha de la operación/escritura (cualquier formato)"},
    "notario_nombre":       {"type": "string", "description": "Nombre del notario en MAYUSCULAS"},
    "num_protocolo":        {"type": "string", "description": "Número de protocolo notarial"},
}


# ── Schema: Escritura ───────────────────────────────────────────────────────

EXTRACT_ESCRITURA = {
    "type": "function",
    "function": {
        "name": "extract_escritura",
        "description": "Extrae datos clave de una escritura notarial de compraventa de inmueble.",
        "parameters": {
            "type": "object",
            "properties": {
                **_COMMON_BUYER_PROPS,
                **_COMMON_SELLER_PROPS,
                **_COMMON_PROPERTY_PROPS,
                **_COMMON_TRANSACTION_PROPS,
            },
        },
    },
}

SYSTEM_ESCRITURA = """Eres un experto en derecho notarial español. Tu tarea es extraer los datos clave de una escritura de compraventa de inmueble.

Instrucciones:
1. Extrae SOLO datos que aparezcan claramente en el documento. Si un dato no está presente, omítelo.
2. Para importes: extrae como número sin símbolo € (ej: 168000).
3. Para nombres: MAYÚSCULAS sin tildes.
4. Para fechas: extráelas tal cual aparecen (DD/MM/YYYY o en letras).
5. Para NIFs: incluye letra, sin espacios ni guiones.
6. La referencia catastral tiene hasta 20 caracteres alfanuméricos.
7. El vendedor (transmitente) suele ser no residente en España.
8. El comprador (adquirente) suele ser residente en España."""


# ── Schema: Modelo 211 ──────────────────────────────────────────────────────

EXTRACT_211 = {
    "type": "function",
    "function": {
        "name": "extract_modelo211",
        "description": "Extrae datos de un Modelo 211 AEAT ya cumplimentado.",
        "parameters": {
            "type": "object",
            "properties": {
                **_COMMON_BUYER_PROPS,
                **_COMMON_SELLER_PROPS,
                **_COMMON_PROPERTY_PROPS,
                **_COMMON_TRANSACTION_PROPS,
                "porcentaje_retencion":  {"type": "number", "description": "Porcentaje de retención (normalmente 3%)"},
                "importe_retencion":     {"type": "number", "description": "Importe de la retención en euros"},
                "resultado_ingresar":    {"type": "number", "description": "Resultado a ingresar en euros"},
                "forma_pago":            {"type": "string", "description": "Forma de pago (1=cargo cuenta, 2=NRC, 3=reconocimiento deuda)"},
                "iban":                  {"type": "string", "description": "IBAN para el cargo en cuenta"},
            },
        },
    },
}

SYSTEM_211 = """Eres un experto fiscal español. Tu tarea es extraer datos de un Modelo 211 de la AEAT ya cumplimentado (retención IRNR en adquisición de inmuebles a no residentes).

Instrucciones:
1. Los datos aparecen en casillas numeradas del formulario oficial.
2. Extrae SOLO datos que encuentres claramente. No inventes valores.
3. Para importes: extrae como número sin símbolo € ni separadores de miles.
4. Para nombres: MAYÚSCULAS sin tildes.
5. Para NIFs: incluye letra, sin espacios ni guiones.
6. El porcentaje de retención habitual es 3%.
7. El importe de retención = importe transmisión × porcentaje / 100.
8. Para fechas: extrae tal cual aparecen."""


# ── Schema: Modelo 600 ──────────────────────────────────────────────────────

EXTRACT_600 = {
    "type": "function",
    "function": {
        "name": "extract_modelo600",
        "description": "Extrae datos de un Modelo 600 de Canarias ya cumplimentado (ITP/AJD).",
        "parameters": {
            "type": "object",
            "properties": {
                **_COMMON_BUYER_PROPS,
                **_COMMON_SELLER_PROPS,
                **_COMMON_PROPERTY_PROPS,
                **_COMMON_TRANSACTION_PROPS,
                "base_imponible":       {"type": "number", "description": "Base imponible en euros"},
                "tipo_impuesto":        {"type": "string", "description": "Tipo de impuesto: TPO o AJD"},
                "tipo_gravamen":        {"type": "number", "description": "Tipo de gravamen (porcentaje)"},
                "cuota_tributaria":     {"type": "number", "description": "Cuota tributaria en euros"},
                "sujeto_pasivo_nif":    {"type": "string", "description": "NIF del sujeto pasivo"},
                "sujeto_pasivo_nombre": {"type": "string", "description": "Nombre del sujeto pasivo en MAYUSCULAS"},
            },
        },
    },
}

SYSTEM_600 = """Eres un experto fiscal español especializado en tributos autonómicos. Tu tarea es extraer datos de un Modelo 600 de Canarias ya cumplimentado (Impuesto sobre Transmisiones Patrimoniales y Actos Jurídicos Documentados).

Instrucciones:
1. Extrae SOLO datos que encuentres claramente en el documento. No inventes valores.
2. Para importes: extrae como número sin símbolo € ni separadores de miles.
3. Para nombres: MAYÚSCULAS sin tildes.
4. Para NIFs: incluye letra, sin espacios ni guiones.
5. La base imponible suele coincidir con el precio de compraventa.
6. El sujeto pasivo en TPO suele ser el comprador.
7. Identifica si es TPO (Transmisiones Patrimoniales Onerosas) o AJD (Actos Jurídicos Documentados).
8. Para fechas: extrae tal cual aparecen."""


# ── Función genérica de extracción ───────────────────────────────────────────

def _extraer_con_llm(texto: str, api_key: str, system_prompt: str,
                     tool_schema: dict, user_prompt: str) -> dict:
    """Llama a GPT-4o con function calling y devuelve el dict extraído."""
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=[tool_schema],
        tool_choice={"type": "function", "function": {"name": tool_schema["function"]["name"]}},
    )

    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name == tool_schema["function"]["name"]:
                return json.loads(tool_call.function.arguments)

    raise RuntimeError("El modelo no devolvió ningún function call.")


# ── Funciones públicas ───────────────────────────────────────────────────────

def extraer_datos_escritura(texto: str, api_key: str) -> dict:
    """Extrae datos de una escritura notarial de compraventa."""
    return _extraer_con_llm(
        texto, api_key, SYSTEM_ESCRITURA, EXTRACT_ESCRITURA,
        f"Extrae los datos de la siguiente escritura notarial de compraventa:\n\n{texto}"
    )


def extraer_datos_211(texto: str, api_key: str) -> dict:
    """Extrae datos de un Modelo 211 ya cumplimentado."""
    return _extraer_con_llm(
        texto, api_key, SYSTEM_211, EXTRACT_211,
        f"Extrae los datos del siguiente Modelo 211 cumplimentado:\n\n{texto}"
    )


def extraer_datos_600(texto: str, api_key: str) -> dict:
    """Extrae datos de un Modelo 600 de Canarias ya cumplimentado."""
    return _extraer_con_llm(
        texto, api_key, SYSTEM_600, EXTRACT_600,
        f"Extrae los datos del siguiente Modelo 600 cumplimentado:\n\n{texto}"
    )
