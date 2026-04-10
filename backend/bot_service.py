"""
AI-powered conversational bot for Gimmicks CRM.
Sequential sales flow: greeting → name → product search → codes → quantities → additional data → quote.
"""
import asyncio
import os
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Per-phone concurrency lock to prevent race conditions when multiple messages arrive quickly
_phone_locks: Dict[str, asyncio.Lock] = {}

SYSTEM_PROMPT = """Eres Ana, asesora comercial de Gimmicks Marketing Services, empresa ecuatoriana de productos promocionales y publicitarios.

PERSONALIDAD:
- Responde con mensajes cortos, de manera natural, sin emojis
- Maximo 300 caracteres por mensaje
- NO uses formato markdown, listas con guiones ni asteriscos
- Tutea al cliente
- Ortografia impecable: siempre usa tildes (que, cuantos, cual, informacion, personalizacion, cotizacion, direccion, etc.)
- Solo haz UNA pregunta por mensaje

REGLA MAS IMPORTANTE - LEE ESTO PRIMERO:
Antes de responder, REVISA con atencion el HISTORIAL COMPLETO y los DATOS YA RECOPILADOS.
Si un dato ya fue proporcionado por el cliente en cualquier punto de la conversacion, NUNCA lo pidas de nuevo.
NUNCA repitas un mensaje que ya enviaste antes. Si necesitas comunicar algo similar, reformulalo con palabras diferentes y mas breves.
No confirmes datos ya conocidos. No repitas informacion que ya diste.
Simplemente avanza al siguiente dato que FALTE o responde la nueva consulta del cliente.

EXTRACCION DE DATOS - REGLA CRITICA:
SIEMPRE extrae TODOS los datos que el cliente proporcione en CADA mensaje, sin importar en que paso del flujo estes.
Si el cliente dice "Soy Laura de Grupo ABC, quiero 500 gorras GORALN00001, mi correo es laura@abc.com, en Quito":
- extracted_data.nombre = "Laura"
- extracted_data.empresa = "Grupo ABC"
- extracted_data.codigos_producto = "GORALN00001"
- extracted_data.cantidades_por_producto = "GORALN00001:500"
- extracted_data.correo = "laura@abc.com"
- extracted_data.ciudad = "Quito"
NUNCA ignores datos que el cliente ya proporciono. Extrae TODO en extracted_data y solo pregunta por lo que FALTA.

FLUJO OBLIGATORIO DE LA CONVERSACION (SIGUE ESTE ORDEN ESTRICTAMENTE):

PASO 1 - SALUDO INICIAL:
Cuando el cliente escribe por primera vez o saluda (hola, buenas, buenos dias, etc.):
- Responde UNICAMENTE con un saludo cordial y pregunta: "En que puedo ayudarte hoy?"
- Si ya conoces su nombre del historial, usalo: "Hola [nombre], en que puedo ayudarte hoy?"
- NO pidas el nombre, NO pidas codigos, NO pidas datos, NO menciones cotizaciones pendientes. SOLO saluda y pregunta en que puedes ayudar.
- Si el cliente menciona un producto EN EL MISMO mensaje del saludo, ve directo al PASO 2.
- SIEMPRE lee el historial de conversacion (ultimos 20 mensajes minimo). Si el cliente ya habia conversado antes, retoma el contexto pero respondiendo al saludo primero.

PASO 2 - PRODUCTO (PRIORIDAD MAXIMA - OBLIGATORIO):
Si el cliente PIDE o MENCIONA un tipo de producto (termos, jarros, gorras, tazas, esferos, etc.) o pregunta si tienes algo:
- De manera INMEDIATA busca en el inventario interno del sistema. Pon catalog_search con la palabra clave del producto.
- Si el sistema te proporciona un LINK DEL CATALOGO FILTRADO, es OBLIGATORIO incluirlo EXACTAMENTE en tu respuesta. NUNCA omitas el link.
- Ejemplo de respuesta correcta: "Tengo varias opciones de termos. Aqui puedes verlos con fotos y codigos: [LINK]. Revisalos y me compartes los codigos que te gusten."
- NO pidas nombre, email, codigos ni ningun otro dato antes de enviar el link. PRIMERO el link, DESPUES todo lo demas.
- REGLA CRITICA: NUNCA menciones codigos de productos si NO has enviado primero el link del catalogo. Los codigos solo se mencionan DESPUES de enviar el link.
- REGLA CRITICA: NUNCA digas "un agente te enviara el catalogo" si el sistema encontro productos. Esa frase SOLO se usa cuando NO hay productos en el inventario del sistema.

PASO 3 - NOMBRE Y APELLIDO DEL CLIENTE:
Despues de entender que articulos desea el cliente (despues de mostrar opciones o recibir codigos):
- Si aun no tienes el nombre, pidelo de forma natural: "Me compartes tu nombre y apellido para registrarte?"
- Guarda el nombre completo (nombre y apellido) en extracted_data.nombre.
- Una vez que tengas el nombre, usalo para dirigirte al cliente de ahi en adelante.

PASO 4 - CONFIRMACION DE CODIGOS:
Si el cliente comparte CODIGOS de productos (como GIMN06001, JARPOR00391, etc.):
- Agregalos a extracted_data.codigos_producto (SIEMPRE la lista COMPLETA acumulada, separada por comas).
- Si el cliente pide QUITAR un codigo, devuelve la lista sin ese codigo.
- AHORA si pregunta la cantidad exacta de cada producto, MENCIONANDO EL NOMBRE de cada uno.
- Usa extracted_data.cantidades_por_producto con formato "CODIGO:cantidad, CODIGO:cantidad".

PASO 5 - DATOS PERSONALES (uno a la vez, SOLO despues de tener codigos Y cantidades):
Solicita los datos personales UNICAMENTE despues de entender cuales articulos desea el cliente.
Una vez que tengas codigos Y cantidades, pide los datos que falten de UNO EN UNO en este orden:
1. Tipo de personalizacion (serigrafia, bordado, UV, laser, sublimacion)
2. Correo electronico
3. Nombre de empresa
4. Ciudad de entrega
5. Fecha de entrega deseada

REGLAS ADICIONALES:
- Si el cliente SALUDA (hola, buenas, buenos dias, etc.): Saluda y pregunta en que le puedes ayudar. NO pidas el nombre de inmediato.
- Si el cliente quiere COTIZAR pero no dice que producto: Pregunta que tipo de producto necesita. NO exijas el nombre primero.
- Si el cliente hace una PREGUNTA (precios, tiempos de entrega, etc.): Responde y guia hacia la accion comercial.
- Si el cliente envia algo que NO ENTIENDES o es ambiguo: Interpreta lo mejor posible. Si definitivamente no puedes dar una respuesta util, marca needs_human=true para que un asesor lo atienda.
- extracted_data.cantidad es la cantidad general (si aplica a todos los productos por igual).
- Si el cliente menciona un producto generico (ej: "jarros"), ponlo en extracted_data.producto.

REGLA CRITICA SOBRE PRODUCTOS NO ENCONTRADOS:
- NUNCA digas que no tienes un producto o articulo. NUNCA uses frases como "no encontre", "no tenemos", "no hay en inventario".
- Si el sistema indica que NO HAY PRODUCTOS para la busqueda: SOLO en este caso, responde que tienes muchas opciones y que un agente le enviara el catalogo completo, que por favor espere unos minutos.
- UNICAMENTE cuando NO hay productos en el inventario interno puedes mencionar que "un agente enviara el catalogo". En CUALQUIER otro caso, TU envias el link interno directamente.
- NO pidas el correo electronico para enviar catalogo. El agente humano se encargara directamente.

COTIZACION:
Marca needs_quote=true UNICAMENTE cuando tengas TODOS estos datos: codigos de producto + cantidad + correo electronico + nombre de empresa. Los cuatro datos son obligatorios.
NUNCA marques needs_quote=true si aun no tienes el correo Y la empresa del cliente.
Si el cliente cambia productos o cantidades DESPUES de la primera cotizacion, marca needs_quote=true de nuevo para actualizarla.

REGLA CRITICA - NUMERO DE COTIZACION:
- NUNCA menciones el numero de cotizacion al cliente (ej: #4700, #4701, etc.). Es un dato interno del sistema.
- Cuando confirmes una cotizacion, solo di que fue registrada y sera enviada. JAMAS incluyas el numero.

INFORMACION DE LA EMPRESA:
- Gimmicks esta en Quito, Ecuador
- Envios a todo el pais
- Personalizacion: serigrafia, bordado, grabado laser, impresion UV, sublimacion
- Pedido minimo: generalmente desde 50 unidades
- Tiempos de entrega: 7-15 dias habiles
- Metodos de pago: transferencia bancaria, tarjeta de credito
- Facturacion electronica disponible

CALIFICACION:
- caliente: tiene codigos + cantidad + datos de contacto
- tibio: pidio catalogo o mostro interes concreto
- frio: pregunta general sin intencion de compra

REGLA CRITICA:
- NUNCA menciones URLs externas como gimmicks.com.ec ni inventes links.

Responde SIEMPRE en JSON valido:
{
  "response": "tu mensaje",
  "extracted_data": {},
  "catalog_search": null,
  "intent": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|pregunta_general|otra",
  "lead_quality": "tibio",
  "category": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|otra",
  "needs_quote": false,
  "needs_human": false,
  "conversation_summary": "resumen"
}"""


# Escalation trigger keywords — detected before AI to ensure immediate escalation
ESCALATION_KEYWORDS = [
    "pasame con alguien", "quiero hablar con una persona",
    "quiero hablar con alguien", "agente humano", "asesor humano", "persona real",
    "terrible", "pesimo", "ya no quiero nada", "ya no quiero",
    "sin mas preguntas", "no mas preguntas",
    "quiero la cotizacion ahorita", "quiero la cotizacion ya",
    "estoy molesto", "estoy frustrado", "estoy enojado",
    "hablar con alguien", "con una persona", "un humano",
]

# Field name normalization map
FIELD_ALIASES = {
    "tipo_de_personalizacion": "personalizacion",
    "tipo_personalizacion": "personalizacion",
    "personalizacion_tipo": "personalizacion",
    "color_logo": "personalizacion",
    "color_logotipo": "personalizacion",
    "email": "correo",
    "mail": "correo",
    "correo_electronico": "correo",
    "e_mail": "correo",
    "codigos": "codigos_producto",
    "codigo": "codigos_producto",
    "codigos_productos": "codigos_producto",
    "nombre_empresa": "empresa",
    "nombre_de_empresa": "empresa",
    "cantidad_unidades": "cantidad",
    "cantidad_de_unidades": "cantidad",
    "unidades": "cantidad",
    "numero_unidades": "cantidad",
    "ciudad_de_entrega": "ciudad",
    "ciudad_entrega": "ciudad",
    "fecha_de_entrega": "fecha_entrega",
    "fecha_entrega_deseada": "fecha_entrega",
    "plazo_entrega": "fecha_entrega",
    "nombre_completo": "nombre",
    "nombre_cliente": "nombre",
    "factura_nombre": "empresa",
    "nombre_factura": "empresa",
    "telefono": "telefono",
    "whatsapp": "telefono",
    "numero_telefono": "telefono",
}


def format_price_ecuador(price: float) -> str:
    if price <= 0:
        return "Precio por confirmar"
    return f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def search_products_by_keyword(db: AsyncIOMotorDatabase, keyword: str, limit: int = 8) -> List[Dict]:
    """Search products by keyword in name, description, or categories."""
    if not keyword:
        return []
    STOPWORDS = {
        "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
        "para", "por", "con", "sin", "que", "como", "pero", "mas", "muy",
        "ese", "esa", "esos", "esas", "este", "esta", "estos", "estas",
        "al", "en", "es", "son", "ser", "hay", "ya", "yo", "tu", "su",
        "me", "te", "se", "le", "lo", "mi", "nos", "les", "hola", "buenas",
        "necesito", "quiero", "busco", "tengo", "puede", "puedo", "favor",
    }
    words = keyword.strip().split()
    stems = set()
    for w in words:
        w_lower = w.lower()
        if w_lower in STOPWORDS or len(w_lower) < 3:
            continue
        stems.add(w_lower)
        if w_lower.endswith("es") and len(w_lower) > 4:
            stems.add(w_lower[:-2])
        if w_lower.endswith("s") and len(w_lower) > 3:
            stems.add(w_lower[:-1])
    if not stems:
        return []
    regex = "|".join(stems)
    query = {
        "$and": [
            {"is_deleted": {"$ne": True}},
            {"$or": [
                {"name": {"$regex": regex, "$options": "i"}},
                {"description": {"$regex": regex, "$options": "i"}},
                {"categories": {"$regex": regex, "$options": "i"}},
                {"category_1": {"$regex": regex, "$options": "i"}},
                {"category_2": {"$regex": regex, "$options": "i"}},
                {"category_3": {"$regex": regex, "$options": "i"}}
            ]}
        ]
    }
    products = await db.products.find(
        query,
        {"_id": 0, "code": 1, "name": 1, "description": 1, "price": 1, "cost": 1, "image_url": 1, "categories": 1}
    ).limit(limit).to_list(limit)
    return products


async def validate_product_codes(db: AsyncIOMotorDatabase, codes: List[str]) -> List[Dict]:
    """Validate product codes and return matching products."""
    found = []
    for code in codes:
        code_clean = code.strip().upper().replace(" ", "")
        product = await db.products.find_one(
            {"code": {"$regex": f"^{re.escape(code_clean)}", "$options": "i"}},
            {"_id": 0}
        )
        if not product:
            spaced = re.sub(r'([A-Za-z])(\d)', r'\1 \2', code_clean)
            product = await db.products.find_one(
                {"code": {"$regex": f"^{re.escape(spaced)}", "$options": "i"}},
                {"_id": 0}
            )
        if not product:
            product = await db.products.find_one(
                {"code": {"$regex": code_clean[:6], "$options": "i"}},
                {"_id": 0}
            )
        if product:
            found.append(product)
    return found


async def get_conversation_history(db: AsyncIOMotorDatabase, conversation_id: str, limit: int = 50) -> str:
    """Get recent messages formatted as conversation text, filtering out error/fallback messages."""
    ERROR_FALLBACKS = [
        "gracias por contactarnos, en un momento atenderemos tu requerimiento",
        "gracias por tu mensaje",
    ]
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0, "sender": 1, "content": 1}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    messages.reverse()

    lines = []
    for msg in messages:
        text = msg.get("content", {}).get("text", "")
        if not text:
            continue
        if msg["sender"] != "user" and any(fb in text.lower() for fb in ERROR_FALLBACKS):
            continue
        role = "Cliente" if msg["sender"] == "user" else "Ana (Gimmicks)"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


async def load_known_client_data(db: AsyncIOMotorDatabase, phone_number: str) -> Dict:
    """Load previously saved CONTACT data for a returning client from leads collection."""
    lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
    if not lead:
        return {}
    known = {}
    field_map = {
        "name": "nombre",
        "empresa": "empresa",
        "ciudad": "ciudad",
        "correo": "correo",
    }
    for src, dst in field_map.items():
        val = lead.get(src)
        if val and str(val).strip() and str(val).lower() not in ("none", "null", "n/a"):
            known[dst] = str(val).strip()
    return known


async def call_llm(system_msg: str, user_msg: str, phone_number: str = "") -> Optional[Dict]:
    """Call LLM and parse JSON response. Falls back to gpt-4o if gpt-5.2 fails."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.error("No EMERGENT_LLM_KEY configured")
        return None

    models = [("openai", "gpt-5.2"), ("openai", "gpt-4o")]
    for provider, model_name in models:
        try:
            session_id = f"gimmicks-{uuid.uuid4().hex[:12]}"
            chat = LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg)
            chat.with_model(provider, model_name)
            response_text = await chat.send_message(UserMessage(text=user_msg))

            cleaned = re.sub(r'```json\s*', '', response_text)
            cleaned = re.sub(r'```\s*', '', cleaned).strip()

            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            return {
                "response": response_text,
                "extracted_data": {},
                "catalog_search": None,
                "intent": "otra",
                "lead_quality": "frio",
                "category": "otra",
                "needs_quote": False,
                "needs_human": False,
                "conversation_summary": ""
            }
        except Exception as e:
            logger.error(f"LLM call failed with {model_name}: {e}")
            if model_name != models[-1][1]:
                logger.info(f"Retrying with fallback model {models[-1][1]}...")
            continue
    return None


async def auto_create_client(db: AsyncIOMotorDatabase, collected_data: Dict, phone_number: str) -> str:
    """Auto-create or update a client from bot collected data. Returns client_id."""
    email = collected_data.get("correo", "")
    name = collected_data.get("nombre", "") or collected_data.get("empresa", "")
    if not name and not email:
        return ""

    existing = None
    if email:
        existing = await db.clients.find_one({"email": email, "is_deleted": False}, {"_id": 0, "id": 1})
    if not existing and phone_number:
        existing = await db.clients.find_one({"phone": {"$regex": phone_number[-10:]}, "is_deleted": False}, {"_id": 0, "id": 1})

    if existing:
        update_fields = {}
        if name:
            update_fields["name"] = name
        if collected_data.get("ciudad"):
            update_fields["city"] = collected_data["ciudad"]
        if collected_data.get("empresa"):
            update_fields["sector_details"] = collected_data["empresa"]
        if update_fields:
            await db.clients.update_one({"id": existing["id"]}, {"$set": update_fields})
        return existing["id"]

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    client_doc = {
        "id": client_id,
        "name": name or f"Cliente WhatsApp {phone_number[-4:]}",
        "email": email or "",
        "commercial_email": "",
        "phone": phone_number,
        "contact_person": collected_data.get("nombre", ""),
        "address": "",
        "city": collected_data.get("ciudad", ""),
        "tax_id": "",
        "sector": "",
        "sector_details": collected_data.get("empresa", ""),
        "notes": "Cliente creado automaticamente desde WhatsApp",
        "source": "whatsapp",
        "is_deleted": False,
        "deleted_at": None,
        "created_at": now
    }
    await db.clients.insert_one(client_doc)
    await db.client_activities.insert_one({
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": "created",
        "details": f"Cliente creado automaticamente desde conversacion WhatsApp ({phone_number})",
        "timestamp": now
    })
    logger.info(f"Auto-created client {client_id} for {phone_number}")
    return client_id


async def upsert_quote(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, conversation_id: str) -> str:
    """Create or update a pending quote in quotes_v2 collection."""
    now = datetime.now(timezone.utc)

    client_id = await auto_create_client(db, collected_data, phone_number)

    qty_map = {}
    qty_raw = collected_data.get("cantidades_por_producto", "")
    if qty_raw:
        for pair in str(qty_raw).split(","):
            pair = pair.strip()
            if ":" in pair:
                code_part, qty_part = pair.split(":", 1)
                try:
                    qty_map[code_part.strip().upper()] = int(re.search(r'\d+', qty_part).group())
                except Exception:
                    qty_map[code_part.strip().upper()] = 1

    general_qty_str = str(collected_data.get("cantidad", ""))
    try:
        general_qty = int(re.search(r'\d+', general_qty_str).group()) if general_qty_str else 1
    except Exception:
        general_qty = 1

    def match_qty(product_code: str) -> int:
        code_upper = product_code.upper().strip()
        if code_upper in qty_map:
            return qty_map[code_upper]
        code_base = re.split(r'\s*[-/]\s*', code_upper)[0].strip()
        if code_base in qty_map:
            return qty_map[code_base]
        for key, val in qty_map.items():
            key_base = re.split(r'\s*[-/]\s*', key)[0].strip()
            if code_base.startswith(key_base) or key_base.startswith(code_base):
                return val
        return general_qty

    codes_raw = collected_data.get("codigos_producto", "")
    quote_items = []

    if codes_raw:
        clean = str(codes_raw).replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
        products = await validate_product_codes(db, code_list)
        for p in products:
            code = p.get("code", "")
            qty = match_qty(code)
            unit_price = p.get("price", 0) or p.get("cost", 0) or 0
            total_price = unit_price * qty
            quote_items.append({
                "item_id": str(uuid.uuid4()),
                "product_id": p.get("id", ""),
                "code": code,
                "name": p.get("name", ""),
                "description": (p.get("description") or "")[:100],
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": total_price,
                "image_url": p.get("image_url", ""),
                "categories": p.get("categories", []),
                "discount_amount": 0,
                "discount_type": "$",
                "additional_amount": 0,
                "additional_type": "$",
                "otros": collected_data.get("personalizacion", "")
            })

    if not quote_items and collected_data.get("producto"):
        products = await search_products_by_keyword(db, collected_data["producto"], limit=5)
        for p in products:
            code = p.get("code", "")
            qty = match_qty(code)
            unit_price = p.get("price", 0) or p.get("cost", 0) or 0
            total_price = unit_price * qty
            quote_items.append({
                "item_id": str(uuid.uuid4()),
                "product_id": p.get("id", ""),
                "code": code,
                "name": p.get("name", ""),
                "description": (p.get("description") or "")[:100],
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": total_price,
                "image_url": p.get("image_url", ""),
                "categories": p.get("categories", []),
                "discount_amount": 0,
                "discount_type": "$",
                "additional_amount": 0,
                "additional_type": "$",
                "otros": collected_data.get("personalizacion", "")
            })

    client_name = collected_data.get("nombre", "")
    if not client_name:
        client_name = collected_data.get("empresa", "")
    if not client_name:
        lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0, "name": 1})
        if not lead:
            phone_alt = phone_number.lstrip("+")
            lead = await db.leads.find_one({"phone_number": phone_alt}, {"_id": 0, "name": 1})
        if lead and lead.get("name"):
            client_name = lead["name"]
    if not client_name:
        client_name = f"Cliente {phone_number[-4:]}"

    subtotal = sum(item["total_price"] for item in quote_items)
    tax = subtotal * 0.15
    total = subtotal + tax

    quote_data = {
        "doc_type": "QUOTE",
        "client_id": client_id,
        "client_name": client_name,
        "client_contact": collected_data.get("nombre", ""),
        "client_email": collected_data.get("correo", ""),
        "items": quote_items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "status": "pending",
        "payment_terms": "50% anticipo, 50% contra entrega",
        "validity": "8 dias",
        "delivery_time": collected_data.get("fecha_entrega", "Por confirmar"),
        "is_deleted": False,
        "deleted_at": None,
        "created_by_id": "",
        "created_by_name": "Bot WhatsApp",
        "phone_number": phone_number,
        "conversation_id": conversation_id,
    }

    existing = await db.quotes_v2.find_one(
        {"phone_number": phone_number, "status": "pending", "is_deleted": False},
        {"_id": 0, "id": 1, "quote_number": 1}
    )

    if existing:
        await db.quotes_v2.update_one(
            {"id": existing["id"]},
            {"$set": {**quote_data, "updated_at": now}}
        )
        return "updated"
    else:
        count = await db.quotes_v2.count_documents({})
        quote_number = str(4698 + count)
        quote_data["id"] = str(uuid.uuid4())
        quote_data["quote_number"] = quote_number
        quote_data["created_at"] = now
        await db.quotes_v2.insert_one(quote_data)
        if client_id:
            await db.client_activities.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "action": "quote_created",
                "details": f"Cotizacion #{quote_number} generada desde WhatsApp",
                "timestamp": now
            })
            await db.document_activities.insert_one({
                "_id": str(uuid.uuid4()),
                "document_id": quote_data["id"],
                "document_number": quote_number,
                "document_type": "QUOTE",
                "action": "created",
                "user_id": "",
                "user_name": "Bot WhatsApp",
                "user_email": "",
                "details": f"Cotizacion creada automaticamente para {client_name} desde WhatsApp",
                "timestamp": now
            })
        return "created"


# ============== PIPELINE STAGES ==============
PIPELINE_STAGES = {
    "lead": "Lead",
    "cliente_potencial": "Cliente Potencial",
    "cotizacion_generada": "Cotizacion Generada",
    "pedido": "Pedido",
    "perdido": "Perdido"
}


def determine_pipeline_stage(collected_data: Dict, quote_generated: bool, lead_quality: str) -> str:
    if quote_generated:
        return "cotizacion_generada"
    has_interest = bool(collected_data.get("producto") or collected_data.get("codigos_producto"))
    has_data = bool(collected_data.get("nombre") or collected_data.get("correo"))
    if has_interest and has_data:
        return "cliente_potencial"
    if has_interest or lead_quality in ("tibio", "caliente"):
        return "cliente_potencial"
    return "lead"


# ============== MAIN CONVERSATION HANDLER ==============

def _new_state(phone_number: str, now: datetime) -> dict:
    return {
        "phone_number": phone_number,
        "collected_data": {},
        "lead_quality": "frio",
        "category": None,
        "quote_generated": False,
        "transferred_to_human": False,
        "message_count": 0,
        "reminder_sent": False,
        "reminder_count": 0,
        "last_interaction": now.isoformat(),
    }


STAFF_NOTIFICATION_PHONE = "593963560326"


async def notify_staff_new_quote(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, is_update: bool, send_message_fn):
    try:
        action = "COTIZACION ACTUALIZADA" if is_update else "NUEVA COTIZACION"
        client_name = collected_data.get("nombre", "No proporcionado")
        correo = collected_data.get("correo", "No proporcionado")
        empresa = collected_data.get("empresa", "No proporcionado")
        codigos = collected_data.get("codigos_producto", "No proporcionado")
        cantidades = collected_data.get("cantidades_por_producto") or collected_data.get("cantidad", "No proporcionado")
        ciudad = collected_data.get("ciudad", "No proporcionado")
        personalizacion = collected_data.get("personalizacion", "No proporcionado")

        notification = (
            f"{action} DESDE WHATSAPP\n\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {phone_number}\n"
            f"Email: {correo}\n"
            f"Empresa: {empresa}\n"
            f"Productos: {codigos}\n"
            f"Cantidades: {cantidades}\n"
            f"Ciudad: {ciudad}\n"
            f"Personalizacion: {personalizacion}\n\n"
            f"Revisar en CRM."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        logger.info(f"Staff notification sent for {phone_number} quote: {action}")
    except Exception as e:
        logger.error(f"Failed to send staff notification: {e}")


async def send_escalation_summary(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, reason: str, send_message_fn):
    try:
        client_name = collected_data.get("nombre", "No proporcionado")
        correo = collected_data.get("correo", "No proporcionado")
        empresa = collected_data.get("empresa", "No proporcionado")
        codigos = collected_data.get("codigos_producto", "No proporcionado")
        cantidades = collected_data.get("cantidades_por_producto") or collected_data.get("cantidad", "No proporcionado")
        ciudad = collected_data.get("ciudad", "No proporcionado")
        personalizacion = collected_data.get("personalizacion", "No proporcionado")

        summary = (
            f"ESCALAMIENTO A ASESOR HUMANO\n\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {phone_number}\n"
            f"Email: {correo}\n"
            f"Empresa: {empresa}\n"
            f"Productos: {codigos}\n"
            f"Cantidades: {cantidades}\n"
            f"Ciudad: {ciudad}\n"
            f"Personalizacion: {personalizacion}\n"
            f"Motivo: {reason}\n\n"
            f"Revisar en CRM."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, summary)
        logger.info(f"Escalation summary sent for {phone_number}: {reason}")
    except Exception as e:
        logger.error(f"Failed to send escalation summary: {e}")


async def notify_staff_catalog_request(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, product_request: str, send_message_fn):
    """Send immediate WhatsApp alert to staff when product search returns no results."""
    try:
        client_name = collected_data.get("nombre", "Cliente sin nombre")

        notification = (
            f"PRODUCTO NO ENCONTRADO EN INVENTARIO\n\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {phone_number}\n"
            f"Busqueda: {product_request}\n\n"
            f"Enviar link del catalogo al cliente por WhatsApp."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        logger.info(f"Catalog email request notification sent for {phone_number} to staff")
    except Exception as e:
        logger.error(f"Failed to send catalog request notification: {e}")


def detect_escalation(message_text: str) -> str:
    msg_lower = message_text.lower().strip()
    for keyword in ESCALATION_KEYWORDS:
        if keyword in msg_lower:
            return f"Cliente solicito: '{keyword}'"
    return ""


async def notify_staff_bot_confused(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, message_text: str, send_message_fn):
    """Send WhatsApp alert to staff when the bot cannot provide a clear response."""
    try:
        client_name = collected_data.get("nombre", "Cliente sin nombre")

        notification = (
            f"BOT NO PUEDE CONTINUAR CONVERSACION\n\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {phone_number}\n"
            f"Ultimo mensaje: {message_text[:200]}\n\n"
            f"El bot no pudo procesar la solicitud. Revisar conversacion en CRM."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        logger.info(f"Bot-confused notification sent for {phone_number}")
    except Exception as e:
        logger.error(f"Failed to send bot-confused notification: {e}")


# ============== CONVERSATION CONTEXT BUILDER ==============

# Ordered list of additional data fields to collect (Step 5)
ADDITIONAL_FIELDS = [
    ("personalizacion", "Tipo de personalizacion (serigrafia, bordado, UV, laser, sublimacion)"),
    ("correo", "Correo electronico"),
    ("empresa", "Nombre de empresa"),
    ("ciudad", "Ciudad de entrega"),
    ("fecha_entrega", "Fecha de entrega deseada"),
]


async def _build_conversation_context(db, phone_number, collected_data, message_text, conversation_id):
    """Build all context variables for the user prompt following the 5-step flow."""

    # --- catalog_info: track what product searches have been shown ---
    catalog_info = ""
    if collected_data.get("codigos_producto"):
        catalog_info = "El cliente ya selecciono codigos de producto."

    # --- catalog_availability: search products based on context ---
    catalog_availability = ""
    has_codes = bool(collected_data.get("codigos_producto"))

    # Search products when: message could be about products
    # Don't search if message looks like pure data (email, short confirmations, codes)
    msg_lower = message_text.lower().strip()
    is_data_input = (
        '@' in message_text or
        len(message_text.strip()) < 3 or
        msg_lower in ('si', 'no', 'ok', 'bueno', 'dale', 'listo', 'gracias')
    )
    # Check if message contains potential product codes (alphanumeric 5+ chars)
    has_code_pattern = bool(re.search(r'[A-Z]{2,}[0-9]{2,}', message_text.upper()))

    # Detect greetings - these should NOT trigger product search
    GREETING_WORDS = {
        'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
        'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
    }
    msg_words = set(msg_lower.split())
    is_greeting = (
        msg_lower in GREETING_WORDS or
        msg_lower.startswith('hola ') or
        msg_lower.startswith('buenas ') or
        msg_lower.startswith('buenos ') or
        (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
    )

    no_products_found = False
    catalog_link = ""
    should_search = not is_data_input and not has_code_pattern and not is_greeting
    if should_search:
        products_found = await search_products_by_keyword(db, message_text.strip(), limit=8)
        if products_found:
            # Build catalog link with search query
            base_url = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
            if not base_url:
                base_url = os.environ.get("CATALOG_BASE_URL", "").rstrip("/")
            if not base_url:
                # Last resort: read from frontend .env
                try:
                    fe_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", ".env")
                    with open(fe_env) as f:
                        for line in f:
                            if line.startswith("REACT_APP_BACKEND_URL="):
                                base_url = line.split("=", 1)[1].strip().rstrip("/")
                                break
                except Exception:
                    pass
            from urllib.parse import quote as url_quote
            # Use only meaningful search terms (no stopwords) for the catalog link
            LINK_STOPWORDS = {
                "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
                "para", "por", "con", "sin", "que", "como", "pero", "mas", "muy",
                "necesito", "quiero", "busco", "tengo", "puede", "puedo", "favor",
                "me", "te", "se", "le", "mi", "hola", "buenas", "buenos", "dias",
                "cotizar", "cotizacion", "ver", "enviar", "envie", "opciones",
                "saber", "tienen", "tener", "tienes", "hay", "donde",
                "queria", "quisiera", "podria", "puedes", "pueden",
            }
            clean_terms = [w for w in message_text.strip().split() if w.lower() not in LINK_STOPWORDS and len(w) > 2]
            search_term = " ".join(clean_terms) if clean_terms else message_text.strip()
            catalog_link = f"{base_url}/catalog?q={url_quote(search_term)}" if base_url else ""

            prod_lines = []
            for p in products_found:
                code = p.get("code", "S/C")
                name = p.get("name", "Producto")
                desc = p.get("description", "")
                desc_short = f" - {desc[:60]}" if desc else ""
                prod_lines.append(f"Codigo: {code} | {name}{desc_short}")
            catalog_availability = "PRODUCTOS ENCONTRADOS EN INVENTARIO:\n" + "\n".join(prod_lines)
            if catalog_link:
                catalog_availability += (
                    f"\n\nLINK DEL CATALOGO FILTRADO (OBLIGATORIO ENVIAR): {catalog_link}\n"
                    f"INSTRUCCION: Es OBLIGATORIO incluir este link EXACTO en tu respuesta. "
                    f"Ejemplo: 'Aqui puedes ver las opciones con fotos y codigos: {catalog_link}'. "
                    f"Pide que revise el catalogo y te comparta los codigos que le gusten. "
                    f"PROHIBIDO decir 'un agente te enviara el catalogo' porque SI hay productos. TU envias el link."
                )
        elif len(message_text.strip()) > 3:
            no_products_found = True
            catalog_availability = (
                "SIN RESULTADOS EN INVENTARIO para esta busqueda.\n"
                "INSTRUCCION: NO digas que no tienes el producto. "
                "Responde que tienes muchas opciones y que un agente le enviara el catalogo completo, "
                "que por favor espere unos minutos. NO pidas correo. NO menciones links externos."
            )

    # Validate and show currently selected codes
    if has_codes:
        codes_raw = collected_data.get("codigos_producto", "")
        clean = str(codes_raw).replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
        validated = await validate_product_codes(db, code_list)
        if validated:
            codes_info = "PRODUCTOS SELECCIONADOS POR EL CLIENTE: " + ", ".join(
                [f"{p.get('name', '')} ({p.get('code', '')})" for p in validated]
            )
            catalog_availability = (catalog_availability + "\n" + codes_info).strip() if catalog_availability else codes_info

    # --- quote_context ---
    quote_context = ""
    existing_quote = await db.quotes_v2.find_one(
        {"phone_number": phone_number, "status": "pending", "is_deleted": False},
        {"_id": 0, "quote_number": 1}
    )
    if existing_quote:
        quote_context = "Ya existe una cotizacion pendiente para este cliente. NO menciones el numero de cotizacion."

    # --- missing_fields ---
    all_required = [
        ("nombre", "Nombre del cliente"),
        ("codigos_producto", "Codigos de producto seleccionados"),
    ]
    # cantidades: check both possible fields
    has_qty = bool(collected_data.get("cantidades_por_producto") or collected_data.get("cantidad"))
    if not has_qty:
        all_required.append(("cantidades_por_producto", "Cantidades por producto"))

    # Add step 5 fields
    for field, label in ADDITIONAL_FIELDS:
        all_required.append((field, label))

    missing = []
    for field, label in all_required:
        if field == "cantidades_por_producto" and has_qty:
            continue
        if not collected_data.get(field):
            missing.append(label)

    missing_fields = "\n".join(f"- {m}" for m in missing) if missing else "Todos los datos recopilados."

    # --- next_to_ask ---
    next_to_ask = ""
    if missing:
        next_to_ask = f"SIGUIENTE DATO A PEDIR: {missing[0]}"
    else:
        next_to_ask = "Ya tienes todos los datos. Si aun no se ha generado cotizacion y tienes codigos + cantidad + correo + empresa, marca needs_quote=true."

    return catalog_info, catalog_availability, quote_context, missing_fields, next_to_ask, no_products_found, catalog_link


def _merge_extracted_data(extracted: Dict, collected_data: Dict) -> Dict:
    """Merge and normalize AI extracted data into collected_data."""
    for key, value in extracted.items():
        if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
            normalized_key = FIELD_ALIASES.get(key, key)
            if normalized_key == "cantidades_por_producto" and isinstance(value, dict):
                parts = []
                for k, v in value.items():
                    if ":" in str(k):
                        parts.append(str(k))
                    else:
                        parts.append(f"{k}:{v}")
                collected_data[normalized_key] = ", ".join(parts)
            elif normalized_key == "codigos_producto" and isinstance(value, list):
                collected_data[normalized_key] = ", ".join(str(v) for v in value)
            else:
                collected_data[normalized_key] = str(value).strip()
    return collected_data


def _is_quote_ready(collected_data: Dict) -> bool:
    """Check if all required data for quote generation is present.
    Per new flow: codes + quantity + email + company are the 4 mandatory fields."""
    has_codes = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
    has_qty = bool(collected_data.get("cantidad") or collected_data.get("cantidades_por_producto"))
    has_email = bool(collected_data.get("correo"))
    has_empresa = bool(collected_data.get("empresa"))
    return has_codes and has_qty and has_email and has_empresa


async def process_ai_conversation(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    message_text: str,
    conversation_id: str,
    send_message_fn
):
    if phone_number not in _phone_locks:
        _phone_locks[phone_number] = asyncio.Lock()
    async with _phone_locks[phone_number]:
        await _process_ai_conversation_inner(db, phone_number, message_text, conversation_id, send_message_fn)


async def _process_ai_conversation_inner(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    message_text: str,
    conversation_id: str,
    send_message_fn
):
    """Inner conversation handler following the 5-step sequential flow."""
    message_sent = False
    try:
        now = datetime.now(timezone.utc)

        # === COOLDOWN: Skip if bot responded in the last 8 seconds ===
        last_bot = await db.messages.find_one(
            {"conversation_id": conversation_id, "sender": {"$in": ["bot", "business"]}},
            {"_id": 0, "timestamp": 1},
            sort=[("timestamp", -1)]
        )
        if last_bot and last_bot.get("timestamp"):
            try:
                last_ts = datetime.fromisoformat(last_bot["timestamp"].replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                if (now - last_ts).total_seconds() < 8:
                    logger.info(f"Cooldown active for {phone_number}, skipping bot response")
                    return
            except Exception:
                pass

        # Get or create conversation state
        state = await db.conversation_states.find_one({"phone_number": phone_number}, {"_id": 0})

        if not state:
            state = _new_state(phone_number, now)
            known_data = await load_known_client_data(db, phone_number)
            if known_data:
                state["collected_data"] = known_data
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": state},
                upsert=True
            )

        # If transferred to human, don't process (human handles it)
        if state.get("transferred_to_human"):
            return

        # Reactivate if lead was "perdido"
        lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
        if lead and lead.get("funnel_stage") == "perdido":
            await db.leads.update_one(
                {"phone_number": phone_number},
                {"$set": {"funnel_stage": "lead", "status": "active", "updated_at": now.isoformat()}}
            )
            state = _new_state(phone_number, now)
            known_data = await load_known_client_data(db, phone_number)
            if known_data:
                state["collected_data"] = known_data
            await db.conversation_states.replace_one(
                {"phone_number": phone_number}, state, upsert=True
            )

        collected_data = state.get("collected_data", {})
        msg_count = state.get("message_count", 0) + 1

        # ===== PRE-AI ESCALATION DETECTION =====
        escalation_reason = detect_escalation(message_text)
        if escalation_reason:
            if not state.get("transferred_to_human"):
                nombre = collected_data.get("nombre", "")
                saludo = f"{nombre}, e" if nombre else "E"

                escalation_msg = (
                    f"{saludo}ntendido, no te hago mas preguntas. "
                    f"Dejo tu solicitud lista para revision por un asesor. "
                    f"Te contactamos enseguida."
                )
                await send_message_fn(phone_number, conversation_id, escalation_msg)
                message_sent = True
                await send_escalation_summary(db, phone_number, collected_data, escalation_reason, send_message_fn)

                await db.conversation_states.update_one(
                    {"phone_number": phone_number},
                    {"$set": {
                        "transferred_to_human": True,
                        "message_count": msg_count,
                        "last_interaction": now.isoformat()
                    }}
                )
                await update_lead_from_ai(db, phone_number, collected_data, "caliente", "escalamiento", "cliente_potencial")
                return

        # ===== BUILD CONTEXT FOR AI =====
        history_text = await get_conversation_history(db, conversation_id, limit=40)

        # Refresh contact data from lead
        known_data = await load_known_client_data(db, phone_number)
        for k, v in known_data.items():
            if v and not collected_data.get(k):
                collected_data[k] = v

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            if parts:
                collected_summary = "\n".join(parts)

        # ===== BUILD CONVERSATION CONTEXT =====
        catalog_info, catalog_availability, quote_context, missing_fields, next_to_ask, no_products_found, catalog_link = \
            await _build_conversation_context(db, phone_number, collected_data, message_text, conversation_id)

        # ===== BUILD USER PROMPT (new template) =====
        user_prompt = f"""INSTRUCCION: Revisa TODO el historial y los datos recopilados. NO pidas nada que ya se haya proporcionado. Haz UNA sola pregunta por mensaje. Tu respuesta debe ser UN solo mensaje coherente.
IMPORTANTE: En extracted_data.codigos_producto siempre devuelve la lista COMPLETA ACUMULADA de codigos (no solo los nuevos).
Si el sistema te proporciona un LINK DEL CATALOGO, es OBLIGATORIO incluirlo en tu respuesta. NUNCA lo omitas. Ejemplo: "Aqui puedes ver las opciones: [link]"
NUNCA menciones codigos de productos si no has incluido el link del catalogo en tu respuesta. Los codigos solo se presentan junto con o despues del link.
NUNCA digas "un agente te enviara el catalogo" si el sistema ENCONTRO productos. La frase "agente enviara catalogo" SOLO se usa cuando el sistema dice "SIN RESULTADOS EN INVENTARIO".
Si el cliente saluda, responde SOLO con un saludo y "en que puedo ayudarte hoy". NO pidas codigos, NO menciones cotizaciones pendientes.
PROHIBIDO repetir o parafrasear tu mensaje anterior. Si ya confirmaste algo, avanza directamente al siguiente paso.
PROHIBIDO pedir el nombre si ya lo tienes en los datos recopilados. Dirigete al cliente por su nombre.
Pide UN SOLO dato por mensaje. No combines preguntas.
Lee siempre el historial completo. Si el cliente ya habia conversado antes, retoma desde donde quedo.

{catalog_info}
{catalog_availability}
{quote_context}

=== HISTORIAL COMPLETO DE LA CONVERSACION ===
{history_text}

=== DATOS YA RECOPILADOS (PROHIBIDO volver a pedir estos) ===
{collected_summary if collected_summary else "Ninguno aun"}

=== DATOS QUE AUN FALTAN ===
{missing_fields}

{next_to_ask}

MENSAJE ACTUAL DEL CLIENTE: {message_text}"""

        # ===== CALL AI =====
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt, phone_number)

        if ai_result is None:
            if msg_count <= 1:
                fallback = "Hola, soy Ana de Gimmicks Marketing Services. En que puedo ayudarte?"
            else:
                fallback = "Disculpa, tuve un problema. Podrias repetir tu mensaje?"
            await send_message_fn(phone_number, conversation_id, fallback)
            message_sent = True
            # Alert #4: Bot cannot continue - notify staff
            await notify_staff_bot_confused(db, phone_number, collected_data, message_text, send_message_fn)
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"message_count": msg_count, "last_interaction": now.isoformat()}}
            )
            return

        response_text = ai_result.get("response", "")
        # Clean response
        if response_text:
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            if response_text.strip().startswith('{') and '"response"' in response_text:
                try:
                    parsed = json.loads(re.search(r'\{[\s\S]*\}', response_text).group())
                    response_text = parsed.get("response", response_text)
                except Exception:
                    pass
            response_text = response_text.strip()

        # Remove redundant greetings in follow-up messages
        if msg_count > 1 and response_text:
            response_text = re.sub(r'^Hola\s+[\w\s]+?,\s*', '', response_text, count=1)
            response_text = re.sub(r'^Hola,\s*', '', response_text, count=1)
            if response_text and response_text[0].islower():
                response_text = response_text[0].upper() + response_text[1:]

        extracted = ai_result.get("extracted_data", {})
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))

        # ===== MERGE EXTRACTED DATA =====
        collected_data = _merge_extracted_data(extracted, collected_data)

        # ===== CHECK IF READY TO GENERATE QUOTE =====
        will_generate_quote = False
        if (needs_quote or _is_quote_ready(collected_data)) and not state.get("quote_generated", False):
            will_generate_quote = True

        # ===== SEND RESPONSE =====
        if not will_generate_quote:
            # Remove any external/invented URLs (keep only our catalog link)
            if response_text:
                if catalog_link:
                    # Temporarily replace our link to preserve it
                    placeholder = "___CATALOG_LINK___"
                    response_text = response_text.replace(catalog_link, placeholder)
                    response_text = re.sub(r'https?://\S+', '', response_text)
                    response_text = response_text.replace(placeholder, catalog_link)
                else:
                    response_text = re.sub(r'https?://\S+', '', response_text)
                response_text = re.sub(r'\s{2,}', ' ', response_text).strip()

            # Append catalog link if AI didn't include it
            if catalog_link and response_text and catalog_link not in response_text:
                response_text = f"{response_text}\n\n{catalog_link}"
                logger.info(f"Catalog link appended for {phone_number}: {catalog_link}")

            # Anti-duplication: if response is too similar to last bot message, skip it
            last_bot_msg = await db.messages.find_one(
                {"conversation_id": conversation_id, "sender": {"$in": ["bot", "business"]}},
                {"_id": 0, "content": 1},
                sort=[("timestamp", -1)]
            )
            if last_bot_msg:
                last_text = last_bot_msg.get("content", {}).get("text", "")
                if last_text and response_text:
                    last_words = set(last_text.lower().split())
                    new_words = set(response_text.lower().split())
                    if last_words and new_words:
                        overlap = len(last_words & new_words) / max(len(last_words), len(new_words))
                        if overlap > 0.7:
                            logger.info(f"Response too similar to last message for {phone_number} (overlap={overlap:.0%}), skipping")
                            return

            await send_message_fn(phone_number, conversation_id, response_text)
            message_sent = True

        # ===== GENERATE QUOTE IF READY =====
        if will_generate_quote:
            existing_quote = await db.quotes_v2.find_one(
                {"phone_number": phone_number, "status": "pending", "is_deleted": False},
                {"_id": 0, "items": 1, "client_name": 1}
            )
            await upsert_quote(db, phone_number, collected_data, conversation_id)
            state_quote = True

            await notify_staff_new_quote(db, phone_number, collected_data, existing_quote is not None, send_message_fn)

            correo = collected_data.get("correo", "tu correo")
            nombre = collected_data.get("nombre", "")
            confirm_msg = (
                f"Gracias{' ' + nombre if nombre else ''}, tu cotizacion ha sido registrada "
                f"y sera enviada a {correo}. Nuestro equipo la revisara pronto."
            )
            await send_message_fn(phone_number, conversation_id, confirm_msg)
            message_sent = True
        else:
            state_quote = state.get("quote_generated", False)

        # ===== PIPELINE STAGE =====
        pipeline_stage = determine_pipeline_stage(collected_data, state_quote, lead_quality)
        if state_quote:
            pipeline_stage = "cotizacion_generada"

        # ===== HANDLE HUMAN TRANSFER =====
        transferred = state.get("transferred_to_human", False)
        if needs_human and not transferred:
            await send_escalation_summary(db, phone_number, collected_data, "El bot detecto que se necesita revision humana", send_message_fn)
            transferred = True

        # ===== ALERT #5: Product not found → immediately notify staff ===
        if no_products_found and not state.get("catalog_alert_sent_for_search"):
            await notify_staff_catalog_request(db, phone_number, collected_data, message_text, send_message_fn)
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"catalog_alert_sent_for_search": True}}
            )

        # ===== UPDATE STATE =====
        state_updates = {
            "collected_data": collected_data,
            "lead_quality": lead_quality,
            "category": category,
            "quote_generated": state_quote,
            "transferred_to_human": transferred,
            "message_count": msg_count,
            "last_interaction": now.isoformat(),
        }

        await db.conversation_states.update_one(
            {"phone_number": phone_number},
            {"$set": state_updates}
        )

        # ===== UPDATE LEAD =====
        await update_lead_from_ai(db, phone_number, collected_data, lead_quality, category, pipeline_stage)

    except Exception as e:
        logger.error(f"Error in AI conversation for {phone_number}: {e}", exc_info=True)
        if not message_sent:
            try:
                await send_message_fn(phone_number, conversation_id, "Disculpa, tuve un problema procesando tu mensaje. Podrias repetirlo?")
            except Exception:
                pass


async def update_lead_from_ai(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    collected_data: Dict,
    lead_quality: str,
    category: Optional[str],
    pipeline_stage: str
):
    now = datetime.now(timezone.utc)
    lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
    if not lead:
        return

    update_fields = {
        "updated_at": now.isoformat(),
        "last_message_at": now.isoformat(),
        "funnel_stage": pipeline_stage
    }

    quality_map = {"caliente": "caliente", "tibio": "tibio", "frio": "frio"}
    if lead_quality in quality_map:
        update_fields["classification"] = quality_map[lead_quality]

    if category:
        update_fields["ai_category"] = category

    if collected_data.get("nombre"):
        update_fields["name"] = collected_data["nombre"]
        await db.conversations.update_one(
            {"phone_number": phone_number},
            {"$set": {"contact_name": collected_data["nombre"]}}
        )

    field_map = {
        "empresa": "empresa", "ciudad": "ciudad", "correo": "correo",
        "producto": "producto_interes", "codigos_producto": "codigos_producto",
        "cantidad": "cantidad_estimada", "fecha_entrega": "fecha_entrega",
        "presupuesto": "presupuesto", "personalizacion": "color_logo"
    }
    for src, dst in field_map.items():
        if collected_data.get(src):
            update_fields[dst] = collected_data[src]

    await db.leads.update_one({"phone_number": phone_number}, {"$set": update_fields})
