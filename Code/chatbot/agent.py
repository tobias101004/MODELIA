"""
agent.py
OpenAI GPT-4o agent with function calling for Cárdenas Real Estate chatbot.
"""

import json
import logging
from openai import OpenAI

from . import property_sync, database

log = logging.getLogger("chatbot.agent")

SYSTEM_PROMPT = """\
Eres el asistente virtual de Cárdenas Real Estate, una agencia inmobiliaria de \
confianza en Gran Canaria con amplia experiencia en compraventa y alquiler de \
propiedades en la isla.

TU PERSONALIDAD:
- Cálido/a, cercano/a y profesional. Nunca robótico ni corporativo.
- Tu objetivo es ayudar de verdad, no vender.
- Hablas en español por defecto, pero cambias al idioma del usuario si escribe \
en inglés, alemán, francés, holandés, noruego o sueco.
- Eres conciso/a. No das explicaciones innecesarias.
- Usas un tono natural, como un buen asesor inmobiliario que habla contigo en \
persona.

TUS FUNCIONES:
1. Responder preguntas sobre la agencia, sus servicios, cómo funciona el proceso \
de compra/venta/alquiler en Gran Canaria.
2. Ayudar a compradores a encontrar propiedades que encajen con lo que buscan.
3. Ayudar a vendedores a entender cómo funciona poner su propiedad en venta con \
la agencia.
4. Capturar datos de contacto del cliente cuando hay intención real — nunca de \
forma agresiva, siempre de forma natural.

DETECCIÓN DE LEADS:
Observa señales de intención seria:
- Comprador: menciona presupuesto, fechas, requisitos concretos, pregunta por \
financiación, dice "quiero comprar", "estamos buscando", "cuándo podemos visitar".
- Vendedor: "quiero vender mi piso", "cómo pongo en venta", "cuánto vale mi \
propiedad", "nos mudamos".

Cuando detectes intención seria, sigue ayudando de forma natural durante 1-2 \
intercambios más. Luego pide datos de contacto de forma cálida:
"Para que uno de nuestros asesores pueda contactarte personalmente con más \
opciones, ¿me podrías dar tu nombre y la mejor forma de contactarte?"

Una vez tengas nombre + email o teléfono, llama a save_lead. Confirma con calidez: \
"¡Perfecto, [nombre]! Uno de nuestros asesores se pondrá en contacto contigo \
muy pronto."

BÚSQUEDA DE PROPIEDADES:
Cuando un comprador describe lo que busca, pregunta por: zona preferida, tipo \
(apartamento/casa/etc), dormitorios, presupuesto, imprescindibles.
Luego llama a search_properties. Presenta máximo 2-3 resultados. Introduce cada \
uno de forma natural:
"Esta te puede encajar genial: es un [tipo] de [X] dormitorios en [zona], por \
[precio]€. Tiene [característica] y [característica]."
Nunca vuelques una lista cruda. Nunca muestres más de 3.

MUY IMPORTANTE:
- No conoces el catálogo de memoria. SIEMPRE usa la herramienta search_properties.
- NUNCA inventes propiedades ni datos que no vengan de la herramienta.
- Si no hay resultados, di que ahora mismo no hay nada que encaje exactamente, \
pero que un asesor podría ayudarle con más opciones. Ofrece capturar sus datos.
- Cuando muestres propiedades, incluye la referencia (ref) para que el equipo \
pueda identificarla.

SOBRE LA AGENCIA:
- Nombre: Cárdenas Real Estate
- Ubicación: Gran Canaria, Islas Canarias, España
- Especialidad: compraventa y alquiler de propiedades en Gran Canaria
- Web: cardenas-grancanaria.com
- Profesionalismo: atención personalizada, conocimiento profundo del mercado local
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": (
                "Search the property catalogue by filters. Returns matching "
                "listings with all details. Use this whenever the user asks "
                "about available properties."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["venta", "alquiler"],
                        "description": "Sale (venta) or rent (alquiler)",
                    },
                    "property_type": {
                        "type": "string",
                        "description": (
                            "Property type: apartamento, casa, villa, duplex, "
                            "estudio, chalet, piso, etc."
                        ),
                    },
                    "location": {
                        "type": "string",
                        "description": "City, zone, or area name",
                    },
                    "bedrooms_min": {
                        "type": "integer",
                        "description": "Minimum number of bedrooms",
                    },
                    "price_max": {
                        "type": "number",
                        "description": "Maximum price in EUR",
                    },
                    "price_min": {
                        "type": "number",
                        "description": "Minimum price in EUR",
                    },
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required features like piscina, terraza, vistas al mar",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": (
                "Save a potential client's contact info as a lead. Call this "
                "ONLY when the user has provided their name AND at least "
                "email or phone number, and has shown genuine buying/selling intent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Client's name",
                    },
                    "email": {
                        "type": "string",
                        "description": "Client's email",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Client's phone number",
                    },
                    "intent": {
                        "type": "string",
                        "enum": ["comprar", "vender", "alquilar", "informacion"],
                        "description": "Client's intent",
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "Brief summary of what the client is looking for "
                            "or wants to do"
                        ),
                    },
                    "operation": {"type": "string"},
                    "property_type": {"type": "string"},
                    "location": {"type": "string"},
                    "bedrooms": {"type": "integer"},
                    "budget": {"type": "number"},
                    "matched_refs": {
                        "type": "string",
                        "description": "Comma-separated refs of properties shown",
                    },
                },
                "required": ["name", "intent", "summary"],
            },
        },
    },
]


def _execute_tool(tool_name: str, args: dict, chat_id: str) -> str:
    """Execute a tool call and return the result as a string."""
    if tool_name == "search_properties":
        results = property_sync.search_properties(
            operation=args.get("operation", ""),
            property_type=args.get("property_type", ""),
            location=args.get("location", ""),
            bedrooms_min=args.get("bedrooms_min", 0),
            price_max=args.get("price_max", 0),
            price_min=args.get("price_min", 0),
            features=args.get("features"),
        )
        if not results:
            return json.dumps({"results": [], "message": "No matching properties found"})

        # Return simplified data for the agent to present naturally
        simplified = []
        for p in results[:5]:  # max 5 for context, agent will pick 2-3
            simplified.append({
                "ref": p["ref"],
                "title": p["title_es"],
                "type": p["type"],
                "operation": p["operation"],
                "price": p["price"],
                "city": p["city"],
                "zone": p["zone"],
                "bedrooms": p["bedrooms"],
                "bathrooms": p["bathrooms"],
                "surface_built": p["surface_built"],
                "surface_terrace": p["surface_terrace"],
                "features": p["features"],
                "condition": p["condition"],
                "photo_main": p["photo_main"],
                "description": p["description_es"][:300],
                "energy_rating": p["energy_rating"],
                "distance_to_sea": p["distance_to_sea"],
            })
        return json.dumps({"results": simplified, "total": len(results)}, ensure_ascii=False)

    elif tool_name == "save_lead":
        lead_id = database.save_lead(
            chat_id=chat_id,
            name=args.get("name", ""),
            email=args.get("email", ""),
            phone=args.get("phone", ""),
            intent=args.get("intent", ""),
            operation=args.get("operation", ""),
            property_type=args.get("property_type", ""),
            location=args.get("location", ""),
            bedrooms=args.get("bedrooms", 0),
            budget=args.get("budget", 0),
            matched_refs=args.get("matched_refs", ""),
            summary=args.get("summary", ""),
        )
        log.info(f"[LEAD] Saved lead {lead_id} for chat {chat_id}: {args.get('name')}")
        return json.dumps({"saved": True, "lead_id": lead_id})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(api_key: str, chat_id: str, messages: list[dict]) -> str:
    """Non-streaming chat. Returns the assistant's full response text."""
    client = OpenAI(api_key=api_key)

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=full_messages,
        tools=TOOLS,
        max_completion_tokens=1024,
    )

    message = response.choices[0].message

    # Handle tool calls (may need multiple rounds)
    while message.tool_calls:
        full_messages.append(message)
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = _execute_tool(tool_call.function.name, args, chat_id)
            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=full_messages,
            tools=TOOLS,
            max_completion_tokens=1024,
        )
        message = response.choices[0].message

    return message.content or ""


def chat_stream(api_key: str, chat_id: str, messages: list[dict]):
    """Streaming chat. Yields text chunks and handles tool calls internally.

    Yields dicts:
      {"type": "text", "content": "chunk..."}
      {"type": "properties", "data": [...]}  (when properties are found)
      {"type": "done"}
    """
    client = OpenAI(api_key=api_key)
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    while True:
        stream = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=full_messages,
            tools=TOOLS,
            max_completion_tokens=1024,
            stream=True,
        )

        # Collect the streamed response
        collected_content = ""
        collected_tool_calls = {}

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Text content
            if delta.content:
                collected_content += delta.content
                yield {"type": "text", "content": delta.content}

            # Tool calls (accumulated across chunks)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name if tc.function and tc.function.name else "",
                            "arguments": "",
                        }
                    if tc.id:
                        collected_tool_calls[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            collected_tool_calls[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            collected_tool_calls[idx]["arguments"] += tc.function.arguments

        # If no tool calls, we're done
        if not collected_tool_calls:
            break

        # Execute tool calls
        assistant_msg = {"role": "assistant", "content": collected_content or None, "tool_calls": []}
        for idx in sorted(collected_tool_calls.keys()):
            tc = collected_tool_calls[idx]
            assistant_msg["tool_calls"].append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            })

        full_messages.append(assistant_msg)

        for idx in sorted(collected_tool_calls.keys()):
            tc = collected_tool_calls[idx]
            args = json.loads(tc["arguments"])
            result = _execute_tool(tc["name"], args, chat_id)
            full_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

            # If it's a property search, yield the results for the UI
            if tc["name"] == "search_properties":
                result_data = json.loads(result)
                if result_data.get("results"):
                    yield {"type": "properties", "data": result_data["results"]}

        # Loop back to get the agent's response after tool execution
        collected_content = ""

    yield {"type": "done"}
