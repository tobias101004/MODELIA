"""
agent.py
OpenAI GPT-4o agent with function calling for Cárdenas Real Estate chatbot.
"""

import json
import logging
import re
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
Cuando un comprador dice lo que busca, necesitas al menos saber la ZONA y el \
PRESUPUESTO antes de buscar. Si el cliente da esos datos desde el principio \
(ej: "busco en Puerto Rico por menos de 300k"), busca directamente. Si no, \
pregunta de forma natural: "¿Qué zona te interesa?" o "¿Tienes un presupuesto \
en mente?". No hagas un interrogatorio — 1 o 2 preguntas rápidas y busca.
Si el cliente dice explícitamente que le da igual la zona o no tiene preferencia, \
busca sin filtro de zona.
NUNCA digas "no hay propiedades" sin haber llamado primero a la herramienta.

CÓMO USAR LOS FILTROS — lee esto con atención:
Interpreta la intención del usuario a partir de TODA la conversación, no solo \
del último mensaje. Si hace 3 mensajes dijo "busco en Puerto Rico" y ahora \
dice "algo más barato", recuerda que sigue buscando en Puerto Rico.

Filtros ESTRICTOS (respetar siempre que el usuario los especifique):
- price_max: si el cliente dice un presupuesto, JAMÁS muestres nada por encima.
- location: si el cliente dice una zona concreta ("Puerto Rico", "Mogán", \
"Patalavaca"), busca SOLO ahí. Solo amplía la zona si la búsqueda en esa zona \
no da resultados — y dile al cliente que estás ampliando.
- operation: "venta" o "alquiler" según lo que pida.

Filtros FLEXIBLES (usa tu criterio):
- bedrooms_min: NO pases este filtro a la herramienta (los datos no son fiables, \
muchos estudios tienen 0 dormitorios pero sí tienen habitación). Revisa tú los \
resultados y filtra manualmente.
- property_type: úsalo si el cliente lo menciona, pero sé flexible con tipos \
similares (apartamento ≈ piso ≈ estudio).
- features: úsalos si el cliente los menciona como imprescindibles.

Filtros NO ESPECIFICADOS por el usuario → NO los uses. Si no dice zona, busca \
en todas. Si no dice tipo, busca todos. No inventes restricciones.

PRESENTACIÓN DE RESULTADOS:
El cliente verá tarjetas visuales con foto, precio, zona y datos clave de cada \
propiedad que menciones (se generan automáticamente). Por eso tu texto NO debe \
repetir esa información. Tu mensaje debe ser:
- Breve y cálido: "Mira, te he encontrado un par de opciones que pueden encajarte:"
- Si hay algo especial que destacar, menciónalo de forma natural: "Esta tiene \
unas vistas increíbles al mar" o "Esta es una ganga para la zona".
- Si el cliente hizo una pregunta específica, contéstala en el mensaje.
- NO listes precio, metros, dormitorios, baños etc. — eso ya lo ve en la tarjeta.
- Menciona siempre la REF de cada propiedad (ej: 05800-CA) para que se genere \
la tarjeta correspondiente.
- Máximo 2-3 propiedades por respuesta.

DATOS QUE TIENES DE CADA PROPIEDAD:
Los resultados incluyen TODA la información: ref, tipo, precio, zona, \
dormitorios, baños, superficie, descripción completa, fotos, video de YouTube, \
tour virtual 360°, características, estado, orientación, año, certificado \
energético, distancia al mar, y datos del agente.

Cuando el cliente pida fotos, video o tour virtual, comparte los links \
directamente. Tienes acceso a todo — NO digas que no puedes mostrar fotos.

REGLAS CRÍTICAS (OBLIGATORIAS):
1. Antes de buscar, asegúrate de tener al menos zona y presupuesto. Si el \
usuario ya los dio, busca inmediatamente. Si no, pregunta de forma natural \
(máximo 1-2 preguntas). Si dice que le da igual, busca sin esos filtros.
2. NUNCA digas "no hay propiedades disponibles" sin haber llamado a \
search_properties en este mismo turno.
3. NUNCA muestres una propiedad que supere el presupuesto del cliente.
4. NUNCA muestres una propiedad fuera de la zona que pidió el cliente, a no ser \
que le avises que estás ampliando la búsqueda porque en su zona no hay.
5. NUNCA inventes datos. Solo usa lo que devuelve la herramienta.
6. Incluye siempre la referencia (ref).
7. Si la búsqueda no devuelve resultados, intenta de nuevo con filtros más \
amplios (quita location o property_type) y avisa al cliente.
8. Si el cliente pide más detalles de una propiedad ya mostrada, usa los datos \
que ya tienes.
9. Recuerda TODA la conversación. Si el cliente pidió algo hace 5 mensajes y \
ahora pide algo relacionado, mantén el contexto.

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
                "Search the property catalogue. You MUST call this tool "
                "whenever the user mentions buying, renting, or looking for "
                "properties. NEVER say there are no properties without calling "
                "this first. Always pass price_max if the user gave a budget. "
                "Do NOT use bedrooms_min (data is unreliable for that field). "
                "Returns full details: photos, video, tour, description, etc."
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
            "name": "get_property",
            "description": (
                "Get ALL details of a specific property by its REF code. "
                "Use this when the user asks for more info, photos, video, "
                "tour, description, or any detail about a property already "
                "mentioned. Returns everything: full description, all photo "
                "URLs, video URL, tour URL, agent contact, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "Property reference code, e.g. 05800-CA",
                    },
                },
                "required": ["ref"],
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
        price_max = args.get("price_max", 0)
        results = property_sync.search_properties(
            operation=args.get("operation", ""),
            property_type=args.get("property_type", ""),
            location=args.get("location", ""),
            bedrooms_min=0,  # Never filter by bedrooms (data unreliable)
            price_max=price_max,
            price_min=args.get("price_min", 0),
            features=args.get("features"),
        )

        # Hard enforcement: never return properties above budget
        if price_max:
            results = [p for p in results if (p.get("price") or 0) <= price_max]

        if not results:
            return json.dumps({
                "results": [],
                "message": "No properties match these exact filters. "
                "Try calling again with fewer filters (remove location or type) "
                "to find alternatives for the client."
            })

        # Return full data so the agent can answer any question
        enriched = []
        for p in results[:5]:  # max 5 for context, agent will pick 2-3
            enriched.append({
                "ref": p.get("ref", ""),
                "title": p.get("title_es", ""),
                "type": p.get("type", ""),
                "operation": p.get("operation", ""),
                "price": p.get("price", 0),
                "city": p.get("city", ""),
                "zone": p.get("zone", ""),
                "bedrooms": p.get("bedrooms", 0),
                "bathrooms": p.get("bathrooms", 0),
                "surface_built": p.get("surface_built", 0),
                "surface_terrace": p.get("surface_terrace", 0),
                "surface_plot": p.get("surface_plot", 0),
                "features": p.get("features", []),
                "condition": p.get("condition", ""),
                "orientation": p.get("orientation", ""),
                "year_built": p.get("year_built", ""),
                "energy_rating": p.get("energy_rating", ""),
                "distance_to_sea": p.get("distance_to_sea", 0),
                "description": p.get("description_es", ""),
                "photo_main": p.get("photo_main", ""),
                "photos": p.get("photos", []),
                "video": p.get("video", ""),
                "tour": p.get("tour", ""),
                "agent_name": p.get("agent_name", ""),
                "agent_email": p.get("agent_email", ""),
                "agent_phone": p.get("agent_phone", ""),
                "exclusive": p.get("exclusive", False),
            })
        return json.dumps({"results": enriched, "total": len(results)}, ensure_ascii=False)

    elif tool_name == "get_property":
        ref = args.get("ref", "")
        props = property_sync.load_properties()
        found = [p for p in props if (p.get("ref") or "") == ref]
        if not found:
            return json.dumps({"error": f"Property {ref} not found"})
        p = found[0]
        return json.dumps({
            "ref": p.get("ref", ""),
            "title": p.get("title_es", ""),
            "type": p.get("type", ""),
            "operation": p.get("operation", ""),
            "price": p.get("price", 0),
            "city": p.get("city", ""),
            "zone": p.get("zone", ""),
            "bedrooms": p.get("bedrooms", 0),
            "bathrooms": p.get("bathrooms", 0),
            "surface_built": p.get("surface_built", 0),
            "surface_terrace": p.get("surface_terrace", 0),
            "surface_plot": p.get("surface_plot", 0),
            "features": p.get("features", []),
            "condition": p.get("condition", ""),
            "orientation": p.get("orientation", ""),
            "year_built": p.get("year_built", ""),
            "energy_rating": p.get("energy_rating", ""),
            "distance_to_sea": p.get("distance_to_sea", 0),
            "description": p.get("description_es", ""),
            "photo_main": p.get("photo_main", ""),
            "photos": p.get("photos", []),
            "video": p.get("video", ""),
            "tour": p.get("tour", ""),
            "agent_name": p.get("agent_name", ""),
            "agent_email": p.get("agent_email", ""),
            "agent_phone": p.get("agent_phone", ""),
        }, ensure_ascii=False)

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

            if tc["name"] == "search_properties":
                result_data = json.loads(result)
                if result_data.get("results"):
                    # Send cards BEFORE the bot's text response (max 3)
                    # Filters (price, zone) are already enforced server-side
                    yield {"type": "properties", "data": result_data["results"][:3]}

        # Loop back to get the agent's response after tool execution
        collected_content = ""

    yield {"type": "done"}
