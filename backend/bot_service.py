"""
AI-powered conversational bot for Gimmicks CRM.
Strict state-machine sales assistant: greeting → name → product search → codes → quantities → logo → data → quote.
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

SYSTEM_PROMPT = """Eres Ana, asesora comercial de Gimmicks Marketing Services, empresa ecuatoriana de productos promocionales.

PERSONALIDAD:
- Cálida, profesional, directa
- Mensajes cortos, máximo 300 caracteres
- SIN emojis, SIN markdown, SIN listas con guiones
- Tutea al cliente, ortografía impecable con tildes
- UNA sola pregunta por mensaje
- NUNCA saludes con "Hola" más de una vez en la conversación

REGLA MAESTRA - MÁQUINA DE ESTADOS:
Sigue ESTRICTAMENTE el estado indicado. Cada mensaje del cliente se interpreta ÚNICAMENTE según el estado actual. NUNCA saltes estados ni interpretes datos fuera de contexto.

ESTADOS:

ESTADO "saludo":
- Preséntate como Ana de Gimmicks Marketing Services
- Pregunta el nombre del cliente
- next_stage: "captura_nombre"

ESTADO "captura_nombre":
- CUALQUIER texto que el cliente envíe es su NOMBRE. NUNCA lo interpretes como producto ni código
- Guarda en extracted_data.nombre
- Agradece y pregunta qué producto o artículo promocional necesita
- next_stage: "busqueda_producto"

ESTADO "busqueda_producto":
- El cliente describe qué necesita (gorras, termos, jarros, etc.)
- Pon catalog_search con la palabra clave del producto
- Si hay PRODUCTOS ENCONTRADOS: muéstralos mencionando nombre y código, pide que comparta los códigos que le interesen
- Si NO hay productos: informa y sugiere revisar el catálogo completo
- next_stage: "esperando_codigos"

ESTADO "esperando_codigos":
- SOLO interpreta como CÓDIGOS los textos alfanuméricos tipo JARPOR00391, GORALN00001, HT2PR2
- Si pide más opciones u otro producto: next_stage="busqueda_producto"
- Si pide catálogo completo: marca intent "solicitud_catalogo"
- Cuando recibas códigos válidos: guarda en extracted_data.codigos_producto
- next_stage: "validando_codigos"

ESTADO "validando_codigos":
- Ya tienes códigos. Pregunta SOLO cuántas unidades de cada producto mencionando sus nombres
- Si dice "100 de cada uno": asigna esa cantidad a todos
- Guarda en extracted_data.cantidades_por_producto (formato CODIGO:cantidad)
- next_stage: "tipo_logo"

ESTADO "tipo_logo":
- Pregunta: "¿El logotipo será a un color o full color?"
- Guarda en extracted_data.color_logo
- next_stage: "recopilando_datos"

ESTADO "recopilando_datos":
- Pide UNO por UNO los datos que falten en este ORDEN ESTRICTO:
  1. correo: "¿A qué correo enviamos la cotización?"
  2. ciudad: "¿En qué ciudad estás?"
  3. empresa: "¿A nombre de qué empresa?"
- REGLAS DE INTERPRETACIÓN:
  * Si preguntaste CORREO y responde algo con @: es correo
  * Si preguntaste CIUDAD y responde un lugar: es ciudad
  * Si preguntaste EMPRESA y responde un nombre: es empresa
  * NUNCA interpretes estos datos como códigos de producto
- Cuando tengas los 3 datos: marca needs_quote=true
- next_stage: "confirmacion"

ESTADO "confirmacion":
- La cotización fue generada. Agradece al cliente
- Informa que la cotización será enviada al email registrado
- NO hagas más preguntas
- Si el cliente agrega productos: needs_quote=true, needs_human=true

ESTADO "escalado_humano":
- Solo confirma que un asesor se comunicará pronto

ESCALAMIENTO INMEDIATO - marca needs_human=true y escalate=true cuando:
- El cliente pide hablar con una persona o agente
- Detectas frustración: "terrible", "ya no quiero", "molesto", "pésimo"
- No puedes entender la solicitud del cliente
- El cliente quiere cerrar rápido

INFORMACIÓN DE GIMMICKS:
- Quito, Ecuador. Envíos a todo el país
- Personalización con logotipo a un color o full color
- Pedido mínimo: generalmente desde 50 unidades
- Entrega: 7-15 días hábiles

Solo menciona productos que aparezcan en PRODUCTOS ENCONTRADOS. NUNCA inventes nombres ni códigos.

Responde SIEMPRE en JSON válido:
{
  "response": "tu mensaje",
  "extracted_data": {},
  "catalog_search": null,
  "intent": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pregunta_general|escalamiento|otra",
  "lead_quality": "tibio",
  "category": "cotizacion_directa|solicitud_catalogo|consulta_ideas|otra",
  "needs_quote": false,
  "needs_human": false,
  "escalate": false,
  "escalate_reason": "",
  "next_stage": "",
  "conversation_summary": "resumen"
}"""


EXTERNAL_CATALOG_URL = "https://gimmicks.com.ec/"

# Escalation trigger keywords — detected before AI to ensure immediate escalation
ESCALATION_KEYWORDS = [
    "pásame con alguien", "pasame con alguien", "quiero hablar con una persona",
    "quiero hablar con alguien", "agente humano", "asesor humano", "persona real",
    "terrible", "pésimo", "pesimo", "ya no quiero nada", "ya no quiero",
    "sin más preguntas", "sin mas preguntas", "no más preguntas", "no mas preguntas",
    "quiero la cotización ahorita", "quiero la cotizacion ahorita",
    "quiero la cotización ya", "quiero la cotizacion ya",
    "estoy molesto", "estoy frustrado", "estoy enojado",
    "hablar con alguien", "con una persona", "un humano",
]

# Valid conversation stages
VALID_STAGES = [
    "saludo", "captura_nombre", "busqueda_producto", "esperando_codigos",
    "validando_codigos", "tipo_logo", "recopilando_datos", "confirmacion", "escalado_humano"
]

# Field name normalization map
FIELD_ALIASES = {
    "tipo_de_personalizacion": "color_logo",
    "tipo_personalizacion": "color_logo",
    "color_logo": "color_logo",
    "color_logotipo": "color_logo",
    "email": "correo",
    "mail": "correo",
    "correo_electronico": "correo",
    "correo_electrónico": "correo",
    "e_mail": "correo",
    "codigos": "codigos_producto",
    "codigo": "codigos_producto",
    "códigos": "codigos_producto",
    "código": "codigos_producto",
    "codigos_productos": "codigos_producto",
    "códigos_producto": "codigos_producto",
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
    words = keyword.strip().split()
    stems = set()
    for w in words:
        stems.add(w)
        if w.endswith("es") and len(w) > 3:
            stems.add(w[:-2])
        if w.endswith("s") and len(w) > 2:
            stems.add(w[:-1])
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
    """Call LLM and parse JSON response."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("No EMERGENT_LLM_KEY configured")
            return None
        session_id = f"gimmicks-{uuid.uuid4().hex[:12]}"
        chat = LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg)
        chat.with_model("openai", "gpt-5.2")
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
        logger.error(f"LLM call failed: {e}")
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
                except:
                    qty_map[code_part.strip().upper()] = 1

    general_qty_str = str(collected_data.get("cantidad", ""))
    try:
        general_qty = int(re.search(r'\d+', general_qty_str).group()) if general_qty_str else 1
    except:
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
                "otros": collected_data.get("color_logo", "")
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
                "otros": collected_data.get("color_logo", "")
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
        "catalog_sent": [],
        "quote_generated": False,
        "transferred_to_human": False,
        "message_count": 0,
        "reminder_sent": False,
        "reminder_count": 0,
        "last_interaction": now.isoformat(),
        "stage": "saludo",
    }


STAFF_NOTIFICATION_PHONE = "593999440910"


async def notify_staff_new_quote(db: AsyncIOMotorDatabase, customer_phone: str, collected_data: Dict, is_update: bool, send_message_fn):
    try:
        client_name = collected_data.get("nombre", "Cliente desconocido")
        correo = collected_data.get("correo", "No proporcionado")
        producto = collected_data.get("codigos_producto") or collected_data.get("producto", "No especificado")
        action = "ACTUALIZADA" if is_update else "NUEVA"

        quote = await db.quotes_v2.find_one(
            {"phone_number": customer_phone, "status": "pending", "is_deleted": False},
            {"_id": 0, "quote_number": 1}
        )
        quote_num = quote.get("quote_number", "?") if quote else "?"

        notification = (
            f"ALERTA COTIZACION {action}\n\n"
            f"Cotizacion #{quote_num}\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {customer_phone}\n"
            f"Correo: {correo}\n"
            f"Productos: {producto}\n\n"
            f"Revisa el CRM para mas detalles."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"

        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        logger.info(f"Staff notification sent to {STAFF_NOTIFICATION_PHONE} for quote from {customer_phone}")
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
        color_logo = collected_data.get("color_logo", "No proporcionado")

        summary = (
            f"ESCALAMIENTO A ASESOR HUMANO\n\n"
            f"Cliente: {client_name}\n"
            f"Telefono: {phone_number}\n"
            f"Email: {correo}\n"
            f"Empresa: {empresa}\n"
            f"Productos: {codigos}\n"
            f"Cantidades: {cantidades}\n"
            f"Ciudad: {ciudad}\n"
            f"Logo: {color_logo}\n"
            f"Motivo: {reason}\n\n"
            f"Revisar en CRM."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, summary)
        logger.info(f"Escalation summary sent for {phone_number}: {reason}")
    except Exception as e:
        logger.error(f"Failed to send escalation summary: {e}")


def detect_escalation(message_text: str) -> str:
    msg_lower = message_text.lower().strip()
    for keyword in ESCALATION_KEYWORDS:
        if keyword in msg_lower:
            return f"Cliente solicito: '{keyword}'"
    return ""


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
    """Inner conversation handler with strict state machine."""
    message_sent = False
    try:
        now = datetime.now(timezone.utc)

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
        current_stage = state.get("stage", "saludo")

        # ===== PRE-AI ESCALATION DETECTION =====
        escalation_reason = detect_escalation(message_text)
        if escalation_reason and current_stage != "escalado_humano":
            nombre = collected_data.get("nombre", "")
            saludo = f"{nombre}, e" if nombre else "E"
            summary_parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            summary_text = ", ".join(summary_parts) if summary_parts else "sin datos recopilados"

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
                    "stage": "escalado_humano",
                    "transferred_to_human": True,
                    "message_count": msg_count,
                    "last_interaction": now.isoformat()
                }}
            )
            await update_lead_from_ai(db, phone_number, collected_data, "caliente", "escalamiento", "cliente_potencial")
            return

        # ===== If already escalated =====
        if current_stage == "escalado_humano":
            await send_message_fn(phone_number, conversation_id, "Tu solicitud ya fue enviada a un asesor. Te contactara pronto.")
            message_sent = True
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"message_count": msg_count, "last_interaction": now.isoformat()}}
            )
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

        # ===== BUILD STAGE-SPECIFIC CONTEXT =====
        stage_instruction = ""
        catalog_availability = ""
        codes_context = ""

        if current_stage == "saludo":
            if collected_data.get("nombre"):
                stage_instruction = f"ESTADO: saludo. Cliente recurrente: {collected_data['nombre']}. Saluda por nombre y pregunta en que te puede ayudar. next_stage='busqueda_producto'."
            else:
                stage_instruction = "ESTADO: saludo. Presentate como Ana de Gimmicks Marketing Services y pregunta el nombre del cliente. next_stage='captura_nombre'."

        elif current_stage == "captura_nombre":
            stage_instruction = (
                "ESTADO: captura_nombre. Lo que el cliente diga ES su nombre. "
                "NO lo interpretes como producto. Guardalo en extracted_data.nombre. "
                "Agradece y pregunta que producto o articulo promocional necesita. "
                "next_stage='busqueda_producto'."
            )

        elif current_stage == "busqueda_producto":
            # Search products based on client message
            search_term = message_text.strip()
            products_found = await search_products_by_keyword(db, search_term, limit=8)
            if products_found:
                prod_lines = []
                for p in products_found:
                    code = p.get("code", "S/C")
                    name = p.get("name", "Producto")
                    desc = p.get("description", "")
                    desc_short = f" - {desc[:60]}" if desc else ""
                    prod_lines.append(f"Codigo: {code} | {name}{desc_short}")
                catalog_availability = "\nPRODUCTOS ENCONTRADOS EN INVENTARIO:\n" + "\n".join(prod_lines)
                catalog_availability += "\n\nMuestra estos productos al cliente y pidele que comparta los codigos que le interesen."
                stage_instruction = "ESTADO: busqueda_producto. Hay productos disponibles. Muestralos al cliente con sus codigos y pide que elija. next_stage='esperando_codigos'."
            else:
                catalog_availability = f"\nNO HAY PRODUCTOS en inventario para esa busqueda."
                stage_instruction = (
                    f"ESTADO: busqueda_producto. No se encontraron productos. "
                    f"Informa al cliente y compartele este link del catalogo completo: {EXTERNAL_CATALOG_URL} "
                    f"Pregunta si busca algo mas especifico. next_stage='esperando_codigos'."
                )

        elif current_stage == "esperando_codigos":
            stage_instruction = (
                "ESTADO: esperando_codigos. Espera CODIGOS de producto (alfanumericos tipo JARPOR00391, HT2PR2). "
                "Si el cliente pide mas opciones u otro producto: next_stage='busqueda_producto'. "
                "Si pide catalogo completo: marca intent='solicitud_catalogo'. "
                "Cuando recibas codigos validos: guarda en extracted_data.codigos_producto. next_stage='validando_codigos'."
            )

        elif current_stage == "validando_codigos":
            codes_raw = collected_data.get("codigos_producto", "")
            if codes_raw:
                clean = str(codes_raw).replace("[", "").replace("]", "").replace("'", "").replace('"', '')
                code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
                validated = await validate_product_codes(db, code_list)
                if validated:
                    codes_context = "\nPRODUCTOS CONFIRMADOS: " + ", ".join([f"{p.get('name', '')} ({p.get('code', '')})" for p in validated])
            stage_instruction = (
                "ESTADO: validando_codigos. Ya tienes codigos. Pregunta SOLO cuantas unidades de cada producto. "
                "Guarda en extracted_data.cantidades_por_producto (formato CODIGO:cantidad). "
                "next_stage='tipo_logo'."
            )

        elif current_stage == "tipo_logo":
            stage_instruction = (
                "ESTADO: tipo_logo. Pregunta: El logotipo sera a un color o full color? "
                "Guarda la respuesta en extracted_data.color_logo. "
                "next_stage='recopilando_datos'."
            )

        elif current_stage == "recopilando_datos":
            missing = []
            for field, label in [("correo", "correo electronico"), ("ciudad", "ciudad"), ("empresa", "nombre de empresa")]:
                if not collected_data.get(field):
                    missing.append((field, label))
            if missing:
                next_field, next_label = missing[0]
                stage_instruction = (
                    f"ESTADO: recopilando_datos. Pregunta SOLO: {next_label}. "
                    f"Interpreta la respuesta del cliente como {next_label}, NO como codigo de producto. "
                )
                if len(missing) == 1:
                    stage_instruction += "Cuando tengas este dato: marca needs_quote=true. next_stage='confirmacion'."
                else:
                    stage_instruction += "Quedan mas datos por pedir despues de este."
            else:
                stage_instruction = "ESTADO: recopilando_datos. Ya tienes todos los datos. Marca needs_quote=true. next_stage='confirmacion'."

        elif current_stage == "confirmacion":
            stage_instruction = (
                "ESTADO: confirmacion. La cotizacion fue generada. Agradece al cliente. "
                "Informa que sera enviada al email registrado. NO hagas mas preguntas."
            )

        # ===== Handle full catalog request =====
        msg_lower = message_text.lower()
        catalog_keywords = ["catalogo", "catálogo", "catlogo", "catalog"]
        is_catalog_request = any(w in msg_lower for w in catalog_keywords)

        # ===== BUILD USER PROMPT =====
        user_prompt = f"""{stage_instruction}

Revisa historial y datos recopilados. NO pidas nada que ya tengas. UNA pregunta por mensaje.
En extracted_data.codigos_producto siempre la lista COMPLETA ACUMULADA.
PROHIBIDO repetir tu mensaje anterior.
{catalog_availability}
{codes_context}

=== HISTORIAL ===
{history_text}

=== DATOS YA RECOPILADOS (NO volver a pedir) ===
{collected_summary if collected_summary else "Ninguno aun"}

MENSAJE DEL CLIENTE: {message_text}"""

        # ===== CALL AI =====
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt, phone_number)

        if ai_result is None:
            if msg_count <= 1:
                fallback = "Hola, soy Ana de Gimmicks Marketing Services. Me compartes tu nombre para ayudarte?"
            else:
                fallback = "Disculpa, tuve un problema. Podrias repetir tu mensaje?"
            await send_message_fn(phone_number, conversation_id, fallback)
            message_sent = True
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
        ai_escalate = ai_result.get("escalate", False)
        ai_escalate_reason = ai_result.get("escalate_reason", "")
        ai_next_stage = ai_result.get("next_stage", "")
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))

        # Handle AI-detected escalation
        if ai_escalate and current_stage != "escalado_humano":
            await send_message_fn(phone_number, conversation_id, response_text)
            message_sent = True
            reason = ai_escalate_reason or "Escalamiento detectado por el bot"
            for key, value in extracted.items():
                if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                    normalized_key = FIELD_ALIASES.get(key, key)
                    collected_data[normalized_key] = str(value).strip()
            await send_escalation_summary(db, phone_number, collected_data, reason, send_message_fn)
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "collected_data": collected_data,
                    "stage": "escalado_humano",
                    "transferred_to_human": True,
                    "message_count": msg_count,
                    "last_interaction": now.isoformat()
                }}
            )
            await update_lead_from_ai(db, phone_number, collected_data, lead_quality, "escalamiento", "cliente_potencial")
            return

        # ===== MERGE EXTRACTED DATA =====
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                normalized_key = FIELD_ALIASES.get(key, key)
                # Normalize cantidades_por_producto if AI returns dict
                if normalized_key == "cantidades_por_producto" and isinstance(value, dict):
                    parts = []
                    for k, v in value.items():
                        if ":" in str(k):
                            parts.append(str(k))
                        else:
                            parts.append(f"{k}:{v}")
                    collected_data[normalized_key] = ", ".join(parts)
                # Normalize codigos_producto if AI returns list
                elif normalized_key == "codigos_producto" and isinstance(value, list):
                    collected_data[normalized_key] = ", ".join(str(v) for v in value)
                else:
                    collected_data[normalized_key] = str(value).strip()

        # ===== DETERMINE NEXT STAGE (strict progression) =====
        new_stage = current_stage

        # Trust AI's next_stage if valid
        if ai_next_stage and ai_next_stage in VALID_STAGES:
            new_stage = ai_next_stage

        # Force stage progression based on collected data as safety net
        if current_stage == "saludo":
            if collected_data.get("nombre"):
                new_stage = "busqueda_producto"
            else:
                new_stage = "captura_nombre"
        elif current_stage == "captura_nombre" and collected_data.get("nombre"):
            new_stage = "busqueda_producto"
        elif current_stage == "validando_codigos" and (collected_data.get("cantidades_por_producto") or collected_data.get("cantidad")):
            new_stage = "tipo_logo"
        elif current_stage == "tipo_logo" and collected_data.get("color_logo"):
            new_stage = "recopilando_datos"

        # ===== CHECK IF READY TO GENERATE QUOTE =====
        will_generate_quote = False
        has_codes = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
        has_qty = bool(collected_data.get("cantidad") or collected_data.get("cantidades_por_producto"))
        has_logo = bool(collected_data.get("color_logo"))
        has_email = bool(collected_data.get("correo"))
        has_city = bool(collected_data.get("ciudad"))
        has_empresa = bool(collected_data.get("empresa"))

        if needs_quote or (has_codes and has_qty and has_logo and has_email and has_city and has_empresa):
            if not state.get("quote_generated", False):
                will_generate_quote = True
                new_stage = "confirmacion"

        # ===== SEND RESPONSE =====
        if not will_generate_quote:
            # Handle catalog request: append external URL
            if is_catalog_request and current_stage in ("busqueda_producto", "esperando_codigos"):
                clean_response = response_text.replace("https://gimmicks.com.ec/", "").replace("https://gimmicks.com.ec", "").strip()
                catalog_msg = f"{clean_response}\n\nRevisa nuestro catalogo completo: {EXTERNAL_CATALOG_URL}"
                await send_message_fn(phone_number, conversation_id, catalog_msg)
                message_sent = True
            else:
                # Anti-duplication check
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
                            if overlap > 0.6:
                                rephrase_result = await call_llm(
                                    "Eres un asistente que reformula mensajes. Devuelve SOLO un JSON con el campo 'response'.",
                                    f"Reformula este mensaje con palabras COMPLETAMENTE DIFERENTES, mas corto y directo. Mensaje: \"{response_text}\"",
                                )
                                if rephrase_result and rephrase_result.get("response"):
                                    response_text = rephrase_result["response"]

                await send_message_fn(phone_number, conversation_id, response_text)
                message_sent = True

        # ===== GENERATE QUOTE IF READY =====
        if will_generate_quote:
            existing_quote = await db.quotes_v2.find_one(
                {"phone_number": phone_number, "status": "pending", "is_deleted": False},
                {"_id": 0, "items": 1, "client_name": 1}
            )
            result = await upsert_quote(db, phone_number, collected_data, conversation_id)
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
            reason = ai_escalate_reason or "El bot detecto que se necesita revision humana"
            await send_escalation_summary(db, phone_number, collected_data, reason, send_message_fn)
            transferred = True

        # ===== UPDATE STATE =====
        await db.conversation_states.update_one(
            {"phone_number": phone_number},
            {"$set": {
                "collected_data": collected_data,
                "lead_quality": lead_quality,
                "category": category,
                "catalog_sent": state.get("catalog_sent", []),
                "quote_generated": state_quote,
                "transferred_to_human": transferred,
                "message_count": msg_count,
                "last_interaction": now.isoformat(),
                "stage": new_stage,
            }}
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
        "presupuesto": "presupuesto", "color_logo": "color_logo"
    }
    for src, dst in field_map.items():
        if collected_data.get(src):
            update_fields[dst] = collected_data[src]

    await db.leads.update_one({"phone_number": phone_number}, {"$set": update_fields})
