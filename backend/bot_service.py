"""
AI-powered conversational bot for Gimmicks CRM.
Human-like sales assistant that guides customers through catalog, quoting, and purchase.
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
Recibirás el ESTADO ACTUAL de la conversación. Interpreta CADA mensaje del cliente ÚNICAMENTE según ese estado. NUNCA interpretes una respuesta fuera del contexto del estado actual.

ESTADOS POSIBLES Y CÓMO ACTUAR EN CADA UNO:

ESTADO "saludo":
- Si hay nombre en datos recopilados: saluda por nombre, pregunta en qué ayudar
- Si no hay nombre: preséntate como Ana de Gimmicks y pregunta qué necesita
- Siguiente estado: "captura_nombre" si no hay nombre, o "busqueda_producto" si ya tiene nombre

ESTADO "captura_nombre":
- CUALQUIER texto que el cliente envíe es su NOMBRE. No lo interpretes como producto ni código
- Guarda en extracted_data.nombre
- Agradece y pregunta qué producto necesita
- Siguiente estado: "busqueda_producto"

ESTADO "busqueda_producto":
- El cliente describe qué necesita (gorras, termos, jarros, etc.)
- Pon catalog_search con la palabra clave del producto
- Di "te comparto opciones, revisa y compárteme los códigos que te gusten"
- NO preguntes cantidad ni otros datos aún
- Siguiente estado: "esperando_codigos"

ESTADO "esperando_codigos":
- SOLO interpreta como CÓDIGOS los textos alfanuméricos con formato tipo JARPOR00391, GORALN00001, HT2PR2, etc.
- Si el cliente escribe una ciudad, fecha, email, teléfono, nombre: NO es un código. Guárdalo en el campo correcto
- Si pide más opciones o otro producto: vuelve a "busqueda_producto"
- Si pide catálogo completo: marca intent "solicitud_catalogo"
- Cuando recibas códigos válidos: guarda en extracted_data.codigos_producto
- Siguiente estado: "validando_codigos"

ESTADO "validando_codigos":
- Los códigos ya fueron recibidos. Pregunta SOLO la cantidad de cada producto mencionando sus nombres
- Si el cliente da cantidades: guarda en extracted_data.cantidades_por_producto (formato CODIGO:cantidad)
- Si dice "100 de cada uno": asigna 100 a todos los códigos
- NO interpretes números de teléfono como cantidades
- Siguiente estado: "recopilando_datos"

ESTADO "recopilando_datos":
- Tienes códigos y cantidades. Ahora pide UNO por UNO los datos que falten en este orden:
  1. color_logo: "¿El logotipo será a un color o full color?"
  2. correo: "¿A qué correo enviamos la cotización?"
  3. empresa: "¿A nombre de qué empresa?"
  4. ciudad: "¿En qué ciudad se entrega?"
  5. fecha_entrega: "¿Para qué fecha lo necesitas?"
- REGLAS DE INTERPRETACIÓN POR DATO:
  * Si preguntaste COLOR y responde "un color", "full color", "azul", "negro", "sin logo": es color_logo
  * Si preguntaste CORREO y responde algo con @: es correo
  * Si preguntaste EMPRESA y responde un nombre: es empresa
  * Si preguntaste CIUDAD y responde "Quito", "Guayaquil", etc.: es ciudad
  * Si preguntaste FECHA y responde "abril 15", "finales de mes", "esta semana", "para mañana": es fecha_entrega
  * NUNCA interpretes estos datos como códigos de producto
- Si ya tiene TODOS los datos mínimos (códigos + cantidad + correo + empresa): marca needs_quote=true
- Siguiente estado: "revision_humana"

ESTADO "revision_humana":
- La cotización ya se generó. Solo confirma al cliente que un asesor revisará su solicitud
- Si el cliente agrega productos: actualiza la cotización (needs_quote=true) y marca needs_human=true
- NO hagas más preguntas. Si el cliente pregunta algo, responde brevemente
- Siguiente estado: permanece en "revision_humana"

ESTADO "escalado_humano":
- No respondas conversacionalmente. Solo confirma que un asesor se comunicará pronto
- Si el cliente insiste: repite que un asesor lo atenderá

ESCALAMIENTO INMEDIATO - marca needs_human=true y escalate=true cuando:
- El cliente pide hablar con una persona o agente
- Detectas frustración: "terrible", "ya no quiero", "molesto", "pésimo"
- El cliente dice "sin más preguntas", "quiero la cotización ahorita", "pásame con alguien"
- Hay contradicción de inventario que no puedes resolver
- No puedes determinar qué dato recibiste
- El cliente quiere cerrar rápido y ya tienes datos suficientes

Al escalar: di algo como "Entendido, dejo tu solicitud lista para revisión inmediata" y resume los datos recopilados

EXTRACCIÓN DE DATOS - SIEMPRE:
Extrae TODOS los datos del mensaje en extracted_data, sin importar el estado:
- nombre, empresa, correo, ciudad, fecha_entrega, color_logo
- codigos_producto (lista acumulada completa separada por comas)
- cantidades_por_producto (formato CODIGO:cantidad)
- producto (categoría genérica si aplica)

INFORMACIÓN DE GIMMICKS:
- Quito, Ecuador. Envíos a todo el país
- Personalización con logotipo a un color o full color
- Pedido mínimo: generalmente desde 50 unidades
- Entrega: 7-15 días hábiles
- Pago: transferencia bancaria, tarjeta de crédito

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


EXTERNAL_CATALOG_PDF = "https://gimmicks.com.ec/"

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
    "validando_codigos", "recopilando_datos", "revision_humana", "escalado_humano"
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


def build_catalog_url(keyword: str) -> str:
    """Build public catalog URL for the given product keyword.
    Uses CATALOG_BASE_URL if set, otherwise auto-detects the correct base URL."""
    from urllib.parse import quote
    base_url = os.environ.get("CATALOG_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        # Auto-detect: use REACT_APP_BACKEND_URL if available, else production URL
        base_url = os.environ.get("REACT_APP_BACKEND_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = "https://gimmicks-crm-production.up.railway.app"
    clean = keyword.strip().split(",")[0].split("/")[0].strip()
    if not clean:
        clean = keyword.strip()
    return f"{base_url}/catalog?q={quote(clean)}"


def format_price_ecuador(price: float) -> str:
    if price <= 0:
        return "Precio por confirmar"
    return f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def search_products_by_keyword(db: AsyncIOMotorDatabase, keyword: str, limit: int = 8) -> List[Dict]:
    """Search products by keyword in name, description, or categories (supports both old and new schema).
    Excludes deleted products."""
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
    """Validate product codes and return matching products. Handles codes with/without spaces."""
    found = []
    for code in codes:
        code_clean = code.strip().upper().replace(" ", "")
        # Try exact match first, then flexible
        product = await db.products.find_one(
            {"code": {"$regex": f"^{re.escape(code_clean)}", "$options": "i"}},
            {"_id": 0}
        )
        if not product:
            # Try with spaces between letters and numbers
            spaced = re.sub(r'([A-Za-z])(\d)', r'\1 \2', code_clean)
            product = await db.products.find_one(
                {"code": {"$regex": f"^{re.escape(spaced)}", "$options": "i"}},
                {"_id": 0}
            )
        if not product:
            # Try partial match - just the significant part
            product = await db.products.find_one(
                {"code": {"$regex": code_clean[:6], "$options": "i"}},
                {"_id": 0}
            )
        if product:
            found.append(product)
    return found


async def format_catalog_message(products: List[Dict], category_name: str = "") -> str:
    """Format products as a WhatsApp-friendly catalog message"""
    if not products:
        return "No encontre productos en esa categoria. Dime que buscas y te ayudo."

    title = f"CATALOGO {category_name.upper()}" if category_name else "PRODUCTOS DISPONIBLES"
    lines = [f"{title}\n"]
    for i, p in enumerate(products, 1):
        code = p.get("code", "S/C")
        name = p.get("name", "Producto")
        desc = p.get("description") or ""
        desc_short = f" - {desc[:60]}" if desc else ""
        lines.append(f"{i}. Codigo: {code}")
        lines.append(f"   {name}{desc_short}")
        lines.append("")

    lines.append("Revísalo y dime los códigos que te gusten para cotizarlos.")
    return "\n".join(lines)


async def get_conversation_history(db: AsyncIOMotorDatabase, conversation_id: str, limit: int = 50) -> str:
    """Get recent messages formatted as conversation text, filtering out error/fallback messages."""
    # Fallback messages that pollute history and confuse the AI
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
        # Skip error fallback messages from history
        if msg["sender"] != "user" and any(fb in text.lower() for fb in ERROR_FALLBACKS):
            continue
        role = "Cliente" if msg["sender"] == "user" else "Ana (Gimmicks)"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


async def load_known_client_data(db: AsyncIOMotorDatabase, phone_number: str) -> Dict:
    """Load previously saved CONTACT data for a returning client from leads collection.
    Only loads personal/contact info (name, email, company, city).
    Product-specific data (codes, quantities, etc.) should come from the current conversation only."""
    lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
    if not lead:
        return {}
    known = {}
    # Only load contact/personal data — NOT product data
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


async def load_automation_rules(db: AsyncIOMotorDatabase) -> str:
    """Load active automation rules from DB and format them for the AI system prompt."""
    rules = []
    async for rule in db.automation_rules.find({"is_active": True}, {"_id": 0}):
        trigger = rule.get("trigger_type", "")
        trigger_val = rule.get("trigger_value") or ""
        action_type = rule.get("action_type", "")
        action_val = rule.get("action_value", "")
        name = rule.get("name", "")
        if trigger == "new_lead":
            rules.append(f"- NUEVO LEAD: {action_val}")
        elif trigger == "keyword":
            rules.append(f"- Si el cliente menciona [{trigger_val}]: {action_val}")
        elif trigger == "ai_intent":
            rules.append(f"- Intención '{trigger_val}': {action_val}")
        elif trigger == "no_response":
            rules.append(f"- Sin respuesta ({trigger_val}h): {action_val}")
        else:
            rules.append(f"- {name}: {action_val}")
    if not rules:
        return ""
    return "\n=== REGLAS DE AUTOMATIZACIÓN (DEBES SEGUIR ESTAS) ===\n" + "\n".join(rules)



async def call_llm(system_msg: str, user_msg: str, phone_number: str = "") -> Optional[Dict]:
    """Call LLM and parse JSON response. Uses unique session per call to avoid repetition."""
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

        # Strip markdown code fences before parsing
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

    # Check if client already exists by email or phone
    existing = None
    if email:
        existing = await db.clients.find_one({"email": email, "is_deleted": False}, {"_id": 0, "id": 1})
    if not existing and phone_number:
        existing = await db.clients.find_one({"phone": {"$regex": phone_number[-10:]}, "is_deleted": False}, {"_id": 0, "id": 1})

    if existing:
        # Update existing client with new data
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

    # Create new client
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
        "notes": f"Cliente creado automáticamente desde WhatsApp",
        "source": "whatsapp",
        "is_deleted": False,
        "deleted_at": None,
        "created_at": now
    }
    await db.clients.insert_one(client_doc)
    # Log activity
    await db.client_activities.insert_one({
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": "created",
        "details": f"Cliente creado automáticamente desde conversación WhatsApp ({phone_number})",
        "timestamp": now
    })
    logger.info(f"Auto-created client {client_id} for {phone_number}")
    return client_id


async def upsert_quote(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, conversation_id: str) -> str:
    """Create or update a pending quote in quotes_v2 collection. Auto-creates client. Returns confirmation message."""
    now = datetime.now(timezone.utc)

    # Auto-create or find client
    client_id = await auto_create_client(db, collected_data, phone_number)

    # Parse per-product quantities
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
        """Match product code to qty_map flexibly (handles codes like 'JARVID00020 - AZ' vs 'JARVID00020')"""
        code_upper = product_code.upper().strip()
        # Exact match
        if code_upper in qty_map:
            return qty_map[code_upper]
        # Try without spaces and suffixes (e.g. "JARVID00020 - AZ" → "JARVID00020")
        code_base = re.split(r'\s*[-/]\s*', code_upper)[0].strip()
        if code_base in qty_map:
            return qty_map[code_base]
        # Try if any key in qty_map starts with this code or vice versa
        for key, val in qty_map.items():
            key_base = re.split(r'\s*[-/]\s*', key)[0].strip()
            if code_base.startswith(key_base) or key_base.startswith(code_base):
                return val
        return general_qty

    # Build product items from codes
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

    # Fallback: search by product keyword
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

    # Get client name
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
        "validity": "8 días",
        "delivery_time": collected_data.get("fecha_entrega", "Por confirmar"),
        "is_deleted": False,
        "deleted_at": None,
        "created_by_id": "",
        "created_by_name": "Bot WhatsApp",
        "phone_number": phone_number,
        "conversation_id": conversation_id,
    }

    # Check if a pending quote already exists for this phone in quotes_v2
    existing = await db.quotes_v2.find_one(
        {"phone_number": phone_number, "status": "pending", "is_deleted": False},
        {"_id": 0, "id": 1, "quote_number": 1}
    )

    if existing:
        await db.quotes_v2.update_one(
            {"id": existing["id"]},
            {"$set": {**quote_data, "updated_at": now}}
        )
        product_names = ", ".join([p["name"] for p in quote_items[:3]]) if quote_items else collected_data.get("producto", "productos solicitados")
        return (
            f"He actualizado tu cotización con los cambios: {product_names}. "
            f"Nuestro equipo la revisará y te la enviaremos a {collected_data.get('correo', 'tu correo')} pronto."
        )
    else:
        # Generate quote number
        count = await db.quotes_v2.count_documents({})
        quote_number = str(4698 + count)
        quote_data["id"] = str(uuid.uuid4())
        quote_data["quote_number"] = quote_number
        quote_data["created_at"] = now
        await db.quotes_v2.insert_one(quote_data)
        # Log activity
        if client_id:
            await db.client_activities.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "action": "quote_created",
                "details": f"Cotización #{quote_number} generada desde WhatsApp",
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
                "details": f"Cotización creada automáticamente para {client_name} desde WhatsApp",
                "timestamp": now
            })
        product_names = ", ".join([p["name"] for p in quote_items[:3]]) if quote_items else collected_data.get("producto", "productos solicitados")
        return (
            f"Tu solicitud de cotización para {product_names} ha sido registrada. "
            f"Nuestro equipo la revisará y te la enviaremos a {collected_data.get('correo', 'tu correo')} pronto."
        )


# ============== PIPELINE STAGES ==============
PIPELINE_STAGES = {
    "lead": "Lead",
    "cliente_potencial": "Cliente Potencial",
    "cotizacion_generada": "Cotizacion Generada",
    "pedido": "Pedido",
    "perdido": "Perdido"
}


def determine_pipeline_stage(collected_data: Dict, quote_generated: bool, lead_quality: str) -> str:
    """Determine the pipeline stage based on conversation progress"""
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
    """Create a fresh conversation state with stage tracking"""
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
        "last_interaction": now.isoformat(),
        "stage": "saludo",
        "last_question_field": None,
    }


STAFF_NOTIFICATION_PHONE = "593999440910"


async def notify_staff_new_quote(db: AsyncIOMotorDatabase, customer_phone: str, collected_data: Dict, is_update: bool, send_message_fn):
    """Send WhatsApp notification to staff when a new/updated quote is created"""
    try:
        client_name = collected_data.get("nombre", "Cliente desconocido")
        correo = collected_data.get("correo", "No proporcionado")
        producto = collected_data.get("codigos_producto") or collected_data.get("producto", "No especificado")
        action = "ACTUALIZADA" if is_update else "NUEVA"

        # Get the quote number
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

        # Find or create a conversation for the staff number
        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"

        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        logger.info(f"Staff notification sent to {STAFF_NOTIFICATION_PHONE} for quote from {customer_phone}")
    except Exception as e:
        logger.error(f"Failed to send staff notification: {e}")



async def send_escalation_summary(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, reason: str, send_message_fn):
    """Send a structured summary to the staff when escalating to a human agent."""
    try:
        client_name = collected_data.get("nombre", "No proporcionado")
        correo = collected_data.get("correo", "No proporcionado")
        empresa = collected_data.get("empresa", "No proporcionado")
        codigos = collected_data.get("codigos_producto", "No proporcionado")
        cantidades = collected_data.get("cantidades_por_producto") or collected_data.get("cantidad", "No proporcionado")
        ciudad = collected_data.get("ciudad", "No proporcionado")
        fecha = collected_data.get("fecha_entrega", "No proporcionado")
        color_logo = collected_data.get("color_logo", "No proporcionado")

        summary = (
            f"ESCALAMIENTO A ASESOR HUMANO\n\n"
            f"Cliente: {client_name}\n"
            f"Teléfono: {phone_number}\n"
            f"Email: {correo}\n"
            f"Empresa: {empresa}\n"
            f"Productos solicitados: {codigos}\n"
            f"Cantidades: {cantidades}\n"
            f"Ciudad: {ciudad}\n"
            f"Fecha requerida: {fecha}\n"
            f"Tipo de impresión/logo: {color_logo}\n"
            f"Motivo de escalamiento: {reason}\n\n"
            f"Revisar en CRM para más detalles."
        )

        staff_conv = await db.conversations.find_one({"phone_number": STAFF_NOTIFICATION_PHONE}, {"_id": 0, "id": 1})
        staff_conv_id = staff_conv["id"] if staff_conv else "notification"
        await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, summary)
        logger.info(f"Escalation summary sent for {phone_number}: {reason}")
    except Exception as e:
        logger.error(f"Failed to send escalation summary: {e}")


def detect_escalation(message_text: str) -> str:
    """Check if the user's message contains escalation triggers. Returns reason or empty string."""
    msg_lower = message_text.lower().strip()
    for keyword in ESCALATION_KEYWORDS:
        if keyword in msg_lower:
            return f"Cliente solicitó: '{keyword}'"
    return ""


def determine_stage(collected_data: Dict, catalogs_sent: list, quote_generated: bool, current_stage: str) -> str:
    """Determine the current conversation stage based on collected data."""
    if current_stage == "escalado_humano":
        return "escalado_humano"
    if quote_generated:
        return "revision_humana"
    has_name = bool(collected_data.get("nombre"))
    has_codes = bool(collected_data.get("codigos_producto"))
    has_qty = bool(collected_data.get("cantidad") or collected_data.get("cantidades_por_producto"))
    has_product = bool(collected_data.get("producto"))
    has_catalog = len(catalogs_sent) > 0
    has_email = bool(collected_data.get("correo"))
    has_empresa = bool(collected_data.get("empresa"))

    if has_codes and has_qty and has_email and has_empresa:
        return "recopilando_datos"  # Will transition to revision_humana after quote
    if has_codes and has_qty:
        return "recopilando_datos"
    if has_codes:
        return "validando_codigos"
    if has_catalog or (has_product and has_catalog):
        return "esperando_codigos"
    if has_product or has_name:
        return "busqueda_producto"
    if not has_name and current_stage == "saludo":
        return "captura_nombre"
    return current_stage or "saludo"


async def process_ai_conversation(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    message_text: str,
    conversation_id: str,
    send_message_fn
):
    """Main AI conversation handler with per-phone concurrency lock."""
    # Acquire a per-phone lock to prevent race conditions with rapid messages
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
    """Inner conversation handler — always called under per-phone lock."""
    message_sent = False  # Track if we already sent a message to avoid double-sending on error
    try:
        now = datetime.now(timezone.utc)

        # Get or create conversation state
        state = await db.conversation_states.find_one({"phone_number": phone_number}, {"_id": 0})

        if not state:
            # Brand new conversation - but check if client has previous data
            state = _new_state(phone_number, now)
            known_data = await load_known_client_data(db, phone_number)
            if known_data:
                state["collected_data"] = known_data
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": state},
                upsert=True
            )
        else:
            # Check how long since last interaction
            last_interaction = state.get("last_interaction")
            hours_inactive = 0
            if last_interaction:
                if isinstance(last_interaction, str):
                    last_dt = datetime.fromisoformat(last_interaction.replace('Z', '+00:00'))
                else:
                    last_dt = last_interaction
                hours_inactive = (now - last_dt).total_seconds() / 3600

            had_pending_data = bool(state.get("collected_data"))
            was_completed = state.get("quote_generated") or state.get("transferred_to_human")

            # If 12+ hours inactive: ask to resume or start new
            if hours_inactive >= 12:
                if had_pending_data and not was_completed:
                    # Had pending conversation - ask if they want to resume
                    collected = state.get("collected_data", {})
                    nombre = collected.get("nombre", "")
                    saludo = f"Hola{' ' + nombre if nombre else ''}, "
                    producto = collected.get("producto") or collected.get("codigos_producto") or ""
                    if producto:
                        resume_msg = (
                            f"{saludo}veo que estábamos avanzando con una consulta sobre {producto}. "
                            f"¿Te gustaría que retomemos donde quedamos o prefieres empezar una nueva consulta?"
                        )
                    else:
                        resume_msg = (
                            f"{saludo}teníamos una conversación pendiente. "
                            f"¿Quieres que la retomemos o prefieres empezar de cero?"
                        )
                    await send_message_fn(phone_number, conversation_id, resume_msg)
                    message_sent = True
                    # Mark as waiting for resume decision
                    await db.conversation_states.update_one(
                        {"phone_number": phone_number},
                        {"$set": {
                            "waiting_resume_decision": True,
                            "last_interaction": now.isoformat(),
                            "transferred_to_human": False,
                            "reminder_sent": False
                        }}
                    )
                    return
                else:
                    # Was completed or no data - start fresh but load known client data
                    state = _new_state(phone_number, now)
                    known_data = await load_known_client_data(db, phone_number)
                    if known_data:
                        state["collected_data"] = known_data
                    await db.conversation_states.replace_one(
                        {"phone_number": phone_number},
                        state,
                        upsert=True
                    )

            # Handle resume decision
            if state.get("waiting_resume_decision"):
                msg_lower = message_text.lower().strip()
                wants_new = any(w in msg_lower for w in ["nueva", "nuevo", "cero", "empezar", "otra", "diferente", "no"])
                if wants_new:
                    state = _new_state(phone_number, now)
                    await db.conversation_states.replace_one(
                        {"phone_number": phone_number},
                        state,
                        upsert=True
                    )
                    await send_message_fn(phone_number, conversation_id, "Perfecto, empezamos de cero. ¿En qué te puedo ayudar?")
                    message_sent = True
                    return
                else:
                    # Resume - clear the flag and continue normally
                    await db.conversation_states.update_one(
                        {"phone_number": phone_number},
                        {"$unset": {"waiting_resume_decision": ""}, "$set": {"last_interaction": now.isoformat()}}
                    )
                    state.pop("waiting_resume_decision", None)
                    await send_message_fn(phone_number, conversation_id, "Perfecto, retomamos donde quedamos.")
                    message_sent = True
                    # Fall through to normal processing

        # Reactivate if was perdido or transferred
        if state.get("transferred_to_human"):
            # Check inactivity - if 12h+ auto-reactivate, else ignore
            last_interaction = state.get("last_interaction", "")
            if last_interaction:
                if isinstance(last_interaction, str):
                    last_dt = datetime.fromisoformat(last_interaction.replace('Z', '+00:00'))
                else:
                    last_dt = last_interaction
                hours = (now - last_dt).total_seconds() / 3600
                if hours >= 12:
                    state = _new_state(phone_number, now)
                    await db.conversation_states.replace_one(
                        {"phone_number": phone_number},
                        state,
                        upsert=True
                    )
                else:
                    return
            else:
                return

        lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
        if lead and lead.get("funnel_stage") == "perdido":
            await db.leads.update_one(
                {"phone_number": phone_number},
                {"$set": {"funnel_stage": "lead", "status": "active", "updated_at": now.isoformat()}}
            )
            state["quote_generated"] = False

        collected_data = state.get("collected_data", {})
        msg_count = state.get("message_count", 0) + 1
        current_stage = state.get("stage", "saludo")
        last_question_field = state.get("last_question_field")

        # ===== PRE-AI ESCALATION DETECTION =====
        escalation_reason = detect_escalation(message_text)
        if escalation_reason and current_stage != "escalado_humano":
            # Build summary of what we have
            nombre = collected_data.get("nombre", "")
            saludo = f"{nombre}, e" if nombre else "E"
            summary_parts = []
            for k, v in collected_data.items():
                if v:
                    summary_parts.append(f"{k}: {v}")
            summary_text = ", ".join(summary_parts) if summary_parts else "sin datos recopilados aún"

            escalation_msg = (
                f"{saludo}ntendido, no te hago más preguntas. "
                f"Dejo tu solicitud lista para revisión inmediata por un asesor con estos datos: {summary_text}. "
                f"Te contactamos enseguida."
            )
            await send_message_fn(phone_number, conversation_id, escalation_msg)
            message_sent = True

            # Send structured summary to staff
            await send_escalation_summary(db, phone_number, collected_data, escalation_reason, send_message_fn)

            # Update state
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "stage": "escalado_humano",
                    "transferred_to_human": True,
                    "message_count": msg_count,
                    "last_interaction": now.isoformat()
                }}
            )
            # Update lead
            await update_lead_from_ai(db, phone_number, collected_data, "caliente", "escalamiento", "cliente_potencial")
            return

        # ===== If already escalated, just confirm =====
        if current_stage == "escalado_humano":
            await send_message_fn(phone_number, conversation_id, "Tu solicitud ya fue enviada a un asesor. Te contactará pronto.")
            message_sent = True
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"message_count": msg_count, "last_interaction": now.isoformat()}}
            )
            return

        # ===== BUILD CONTEXT =====
        history_text = await get_conversation_history(db, conversation_id, limit=40)

        # Refresh contact data from lead
        known_data = await load_known_client_data(db, phone_number)
        for k, v in known_data.items():
            if v and not collected_data.get(k):
                collected_data[k] = v

        # Recalculate stage based on data
        current_stage = determine_stage(collected_data, state.get("catalog_sent", []), state.get("quote_generated", False), current_stage)

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            if parts:
                collected_summary = "\n".join(parts)

        catalogs_sent = state.get("catalog_sent", [])
        catalog_info = f"Catálogos ya enviados: {', '.join(catalogs_sent)}" if catalogs_sent else ""

        # Build stage-specific context for the AI
        stage_instruction = ""
        if current_stage == "saludo":
            if collected_data.get("nombre"):
                stage_instruction = f"ESTADO: saludo. Cliente recurrente: {collected_data['nombre']}. Saluda por nombre y pregunta en qué ayudar. next_stage debe ser 'busqueda_producto'."
            else:
                stage_instruction = "ESTADO: saludo. Cliente nuevo. Preséntate y pregunta en qué ayudar. Si no tiene nombre, next_stage='captura_nombre'."
        elif current_stage == "captura_nombre":
            stage_instruction = "ESTADO: captura_nombre. El cliente debe responder con su NOMBRE. Lo que diga es su nombre, guárdalo. next_stage='busqueda_producto'."
        elif current_stage == "busqueda_producto":
            stage_instruction = "ESTADO: busqueda_producto. El cliente describe qué producto necesita. Pon catalog_search con la palabra clave. NO preguntes cantidad. next_stage='esperando_codigos'."
        elif current_stage == "esperando_codigos":
            stage_instruction = "ESTADO: esperando_codigos. Espera CÓDIGOS de producto (alfanuméricos tipo JARPOR00391). Si el mensaje no parece código, clasifícalo según contexto (ciudad, fecha, email, etc.). next_stage='validando_codigos' cuando recibas códigos."
        elif current_stage == "validando_codigos":
            stage_instruction = "ESTADO: validando_codigos. Ya tienes códigos. Pregunta SOLO cuántas unidades de cada producto. next_stage='recopilando_datos' cuando tengas cantidades."
        elif current_stage == "recopilando_datos":
            # Determine what we're asking for
            missing = []
            for field, label in [("color_logo", "color de logotipo"), ("correo", "correo electrónico"),
                                 ("empresa", "nombre de empresa"), ("ciudad", "ciudad de entrega"),
                                 ("fecha_entrega", "fecha de entrega")]:
                if not collected_data.get(field):
                    missing.append((field, label))
            if missing:
                next_field, next_label = missing[0]
                stage_instruction = f"ESTADO: recopilando_datos. Pregunta SOLO: {next_label}. Interpreta la respuesta del cliente como {next_label}, NO como código de producto."
            else:
                stage_instruction = "ESTADO: recopilando_datos. Ya tienes todos los datos. Marca needs_quote=true. next_stage='revision_humana'."
        elif current_stage == "revision_humana":
            stage_instruction = "ESTADO: revision_humana. La cotización ya fue generada. No hagas más preguntas. Si el cliente agrega productos, actualiza (needs_quote=true, needs_human=true)."

        # Pre-check catalog availability
        catalog_availability = ""
        if message_text:
            product_keywords = ["jarro", "termo", "gorra", "taza", "agenda", "mochila", "bolso", "esfero",
                              "boligrafo", "bolígrafo", "camiseta", "polo", "tecnolog", "usb", "cargador", "parlante",
                              "botella", "vaso", "llavero", "libreta", "cuaderno", "bolsa", "paragua",
                              "porta celular", "portacelular", "portalapiz", "tomatodo", "lonchera",
                              "set", "kit", "madera", "ecológico", "ecologico", "antiestres", "antiestré",
                              "organizador", "calendario", "mouse", "audifonos", "audífonos", "altavoz",
                              "copa", "mate", "cerámica", "ceramica", "porcelana", "vidrio", "acero"]
            msg_lower_search = message_text.lower()
            matched_kw = None
            for kw in product_keywords:
                if kw in msg_lower_search:
                    matched_kw = kw
                    break
            if not matched_kw and len(msg_lower_search.split()) <= 5:
                for word in msg_lower_search.split():
                    # Strip punctuation
                    clean_word = re.sub(r'[^\w]', '', word)
                    if len(clean_word) >= 5 and clean_word not in (
                        "hola", "quiero", "necesito", "también", "tambien", "tiene", "tienen",
                        "puedo", "envíame", "enviame", "dame", "mándame", "mandame", "muestrame",
                        "muéstrame", "buenas", "buenos", "días", "tardes", "noches", "favor",
                        "gracias", "donde", "cuando", "cuanto", "cuánto", "precio", "cuesta",
                        "cotizar", "cotización", "cotizacion", "sería", "seria", "podría", "podria",
                    ):
                        matched_kw = clean_word
                        break
            # Only search for products when appropriate — NOT during name capture, code entry, or pure greetings
            is_greeting_only = re.match(r'^(hola|buenos?\s*(días|tardes|noches)|buenas)\b', msg_lower_search) and len(msg_lower_search.split()) <= 4
            # Don't search when in stages that receive codes, quantities, or other data
            allow_search = current_stage in ("busqueda_producto",)
            if current_stage == "saludo" and not is_greeting_only and matched_kw:
                allow_search = True
            if matched_kw and allow_search:
                prods = await search_products_by_keyword(db, matched_kw, limit=5)
                if prods:
                    prod_details = ", ".join([f"{p.get('name', '')} (código: {p.get('code', '')})" for p in prods[:5]])
                    catalog_availability = f"\nPRODUCTOS ENCONTRADOS EN INVENTARIO ACTUAL para '{matched_kw}': {prod_details}. Menciona SOLO estos productos."
                else:
                    catalog_availability = f"\nNO HAY PRODUCTOS en inventario actual para '{matched_kw}'. Informa que no tenemos esa línea y sugiere el catálogo completo en gimmicks.com.ec."

        # Resolve product names for codes (if in validando_codigos stage)
        codes_context = ""
        codes_raw = collected_data.get("codigos_producto", "")
        if codes_raw and current_stage in ("validando_codigos", "recopilando_datos"):
            clean = str(codes_raw).replace("[","").replace("]","").replace("'","").replace('"','')
            code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
            validated = await validate_product_codes(db, code_list)
            if validated:
                codes_context = "\nPRODUCTOS CONFIRMADOS: " + ", ".join([f"{p.get('name','')} ({p.get('code','')})" for p in validated])

        quote_context = ""
        if state.get("quote_generated", False):
            quote_context = "NOTA: Ya existe una cotización pendiente. Si el cliente agrega/cambia productos, marca needs_quote=true y needs_human=true."

        user_prompt = f"""{stage_instruction}

Revisa historial y datos recopilados. NO pidas nada que ya tengas. UNA pregunta por mensaje. Respuesta coherente en UN solo mensaje.
En extracted_data.codigos_producto siempre la lista COMPLETA ACUMULADA.
PROHIBIDO repetir tu mensaje anterior.

{catalog_info}
{catalog_availability}
{codes_context}
{quote_context}

=== HISTORIAL ===
{history_text}

=== DATOS YA RECOPILADOS (NO volver a pedir) ===
{collected_summary if collected_summary else "Ninguno aún"}

MENSAJE DEL CLIENTE: {message_text}"""

        # Call AI with persistent session per phone - inject automation rules
        automation_rules_text = await load_automation_rules(db)
        system_with_rules = SYSTEM_PROMPT + automation_rules_text if automation_rules_text else SYSTEM_PROMPT
        ai_result = await call_llm(system_with_rules, user_prompt, phone_number)

        # If LLM failed, respond with friendly greeting
        if ai_result is None:
            is_first_msg = msg_count <= 1
            if is_first_msg:
                fallback = "Hola, gracias por contactarnos. ¿En qué te puedo ayudar?"
            else:
                fallback = "Gracias por tu mensaje. ¿En qué más te puedo ayudar?"
            await send_message_fn(phone_number, conversation_id, fallback)
            message_sent = True
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"message_count": msg_count, "last_interaction": now.isoformat()}}
            )
            return

        response_text = ai_result.get("response", "Hola, gracias por contactarnos. ¿En qué te puedo ayudar?")
        # Clean response: strip any JSON/code artifacts that the LLM might have leaked
        if response_text:
            # Remove markdown code blocks
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            # If response still looks like JSON, extract just the text
            if response_text.strip().startswith('{') and '"response"' in response_text:
                try:
                    parsed = json.loads(re.search(r'\{[\s\S]*\}', response_text).group())
                    response_text = parsed.get("response", response_text)
                except Exception:
                    pass
            response_text = response_text.strip()

        # Remove redundant greetings in follow-up messages (not the first message)
        if msg_count > 1 and response_text:
            # Strip leading "Hola José," or "Hola José Silva," patterns from follow-up messages
            response_text = re.sub(r'^Hola\s+[\w\s]+?,\s*', '', response_text, count=1)
            # Also handle "Hola, " at the start
            response_text = re.sub(r'^Hola,\s*', '', response_text, count=1)
            # Capitalize first letter after stripping
            if response_text and response_text[0].islower():
                response_text = response_text[0].upper() + response_text[1:]

        extracted = ai_result.get("extracted_data", {})
        catalog_search = ai_result.get("catalog_search")
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)
        ai_escalate = ai_result.get("escalate", False)
        ai_escalate_reason = ai_result.get("escalate_reason", "")
        ai_next_stage = ai_result.get("next_stage", "")

        # Handle AI-detected escalation
        if ai_escalate and current_stage != "escalado_humano":
            await send_message_fn(phone_number, conversation_id, response_text)
            message_sent = True
            reason = ai_escalate_reason or "Escalamiento detectado por el bot"
            # Merge extracted data first
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

        # Anti-duplication: check if response is too similar to last bot message
        last_bot_msg = await db.messages.find_one(
            {"conversation_id": conversation_id, "sender": {"$in": ["bot", "business"]}},
            {"_id": 0, "content": 1},
            sort=[("timestamp", -1)]
        )
        if last_bot_msg:
            last_text = last_bot_msg.get("content", {}).get("text", "")
            if last_text and response_text:
                # Simple similarity: if >60% of words overlap, ask LLM to rephrase
                last_words = set(last_text.lower().split())
                new_words = set(response_text.lower().split())
                if last_words and new_words:
                    overlap = len(last_words & new_words) / max(len(last_words), len(new_words))
                    if overlap > 0.6:
                        rephrase_result = await call_llm(
                            "Eres un asistente que reformula mensajes. Devuelve SOLO un JSON con el campo 'response'.",
                            f"Reformula este mensaje con palabras COMPLETAMENTE DIFERENTES, más corto y directo. NO repitas las mismas frases. Mensaje original: \"{response_text}\"",
                        )
                        if rephrase_result and rephrase_result.get("response"):
                            response_text = rephrase_result["response"]

        # Merge extracted data - normalize field names
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                normalized_key = FIELD_ALIASES.get(key, key)
                collected_data[normalized_key] = str(value).strip()

        # Check if quote will be generated BEFORE sending AI response
        # Force quote creation when all required data is present (codes + qty + email + empresa)
        # BUT do NOT force a quote if the user is asking for a catalog — respond to catalog request first
        will_generate_quote = False
        msg_lower_for_quote = message_text.lower()
        is_catalog_request_msg = any(w in msg_lower_for_quote for w in ["catálogo", "catalogo", "catlogo", "catalog"])
        if not needs_quote and not state.get("quote_generated", False) and not is_catalog_request_msg:
            has_codes = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
            has_qty = bool(collected_data.get("cantidad") or collected_data.get("cantidades_por_producto"))
            has_email = bool(collected_data.get("correo"))
            has_empresa = bool(collected_data.get("empresa"))
            if has_codes and has_qty and has_email and has_empresa:
                needs_quote = True
                will_generate_quote = True
                logger.info(f"Force needs_quote=True for {phone_number} (all required data collected)")
        if needs_quote:
            has_products = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
            has_qty = bool(collected_data.get("cantidad") or collected_data.get("cantidades_por_producto"))
            has_email = bool(collected_data.get("correo"))
            has_empresa = bool(collected_data.get("empresa"))
            will_generate_quote = has_products and has_qty and has_email and has_empresa

        # Handle catalog search - COMBINE with AI response in ONE message
        # Priority: 1) Public catalog link (if products found), 2) External PDF (fallback)
        msg_lower = message_text.lower()
        catalog_full_keywords = [
            "catálogo completo", "catalogo completo", "catálogo general", "catalogo general",
            "todo el catálogo", "todo el catalogo", "catálogo pdf", "catalogo pdf",
            "todos los productos", "ver todo", "catalogo entero", "catálogo entero",
            "ver mas productos", "ver más productos",
        ]
        # Broader: any mention of "catálogo"/"catalogo" without a specific product keyword
        catalog_single_words = ["catálogo", "catalogo", "catlogo"]
        is_full_catalog_request = any(kw in msg_lower for kw in catalog_full_keywords)
        if not is_full_catalog_request:
            # If user mentions "catálogo" without specifying a product search keyword, treat as full catalog
            has_catalog_word = any(w in msg_lower for w in catalog_single_words)
            if has_catalog_word and not catalog_search:
                is_full_catalog_request = True
        # Also detect if AI intent is full catalog or response mentions the gimmicks.com.ec URL
        if not is_full_catalog_request and ai_result.get("intent") == "solicitud_catalogo" and not catalog_search:
            is_full_catalog_request = True
        if not is_full_catalog_request and "gimmicks.com.ec" in response_text.lower():
            is_full_catalog_request = True

        # Only send AI response if we are NOT about to generate a quote
        if not will_generate_quote:
            if is_full_catalog_request:
                # Remove any duplicate URL or web mention the AI may have included
                clean_response = response_text.replace("https://gimmicks.com.ec/", "").replace("https://gimmicks.com.ec", "")
                # Clean up dangling colons or spaces from removed URLs
                clean_response = re.sub(r':\s*\?', '? ', clean_response)
                clean_response = re.sub(r':\s*$', '', clean_response).strip()
                catalog_msg = (
                    f"{clean_response}\n\n"
                    f"Revisa nuestro catálogo completo en la web de Gimmicks: {EXTERNAL_CATALOG_PDF}"
                )
                await send_message_fn(phone_number, conversation_id, catalog_msg)
                message_sent = True
                catalogs_sent.append("catalogo_completo")
            elif catalog_search and catalog_search not in catalogs_sent:
                catalog_url = build_catalog_url(catalog_search)
                products = await search_products_by_keyword(db, catalog_search, limit=5)
                if products:
                    catalog_msg = (
                        f"{response_text}\n\n"
                        f"Revisa nuestro catálogo aquí: {catalog_url}"
                    )
                else:
                    catalog_msg = (
                        f"{response_text}\n\n"
                        f"Revisa nuestro catálogo completo en la web de Gimmicks: {EXTERNAL_CATALOG_PDF}"
                    )
                await send_message_fn(phone_number, conversation_id, catalog_msg)
                message_sent = True
                catalogs_sent.append(catalog_search)
            else:
                await send_message_fn(phone_number, conversation_id, response_text)
                message_sent = True

        # Handle quote creation
        if will_generate_quote:
            existing_quote = await db.quotes_v2.find_one(
                {"phone_number": phone_number, "status": "pending", "is_deleted": False},
                {"_id": 0, "items": 1, "client_name": 1}
            )
            quote_msg = await upsert_quote(db, phone_number, collected_data, conversation_id)
            state_quote = True

            # Notify staff via WhatsApp
            await notify_staff_new_quote(db, phone_number, collected_data, existing_quote is not None, send_message_fn)

            if not existing_quote:
                correo = collected_data.get("correo", "tu correo")
                quote_notify = f"Tu cotización ha sido registrada y será enviada a {correo}. Nuestro equipo la revisará pronto."
                await send_message_fn(phone_number, conversation_id, quote_notify)
                message_sent = True
            else:
                # Quote was updated - still respond to the user
                update_notify = response_text or "Tu cotización ha sido actualizada. Nuestro equipo la revisará pronto."
                await send_message_fn(phone_number, conversation_id, update_notify)
                message_sent = True
        else:
            state_quote = state.get("quote_generated", False)

        # Determine pipeline stage
        pipeline_stage = determine_pipeline_stage(collected_data, state_quote, lead_quality)
        if needs_quote and state_quote:
            pipeline_stage = "cotizacion_generada"

        # Handle human transfer
        transferred = state.get("transferred_to_human", False)
        if needs_human and not transferred:
            transfer_msg = "Voy a pasar tu caso a Ana María, nuestra asesora. Ella te contactará pronto."
            await send_message_fn(phone_number, conversation_id, transfer_msg)
            transferred = True

        # Update state
        # Calculate next stage
        new_stage = current_stage
        if ai_next_stage and ai_next_stage in VALID_STAGES:
            new_stage = ai_next_stage
        else:
            new_stage = determine_stage(collected_data, catalogs_sent, state_quote, current_stage)

        # If needs_human, send notification
        if needs_human and not state.get("transferred_to_human"):
            transferred = True
            reason = ai_escalate_reason or "El bot detectó que se necesita revisión humana"
            await send_escalation_summary(db, phone_number, collected_data, reason, send_message_fn)

        await db.conversation_states.update_one(
            {"phone_number": phone_number},
            {"$set": {
                "collected_data": collected_data,
                "lead_quality": lead_quality,
                "category": category,
                "catalog_sent": catalogs_sent,
                "quote_generated": state_quote,
                "transferred_to_human": transferred,
                "message_count": msg_count,
                "last_interaction": now.isoformat(),
                "stage": new_stage,
                "last_question_field": None,
            }}
        )

        # Update lead
        await update_lead_from_ai(db, phone_number, collected_data, lead_quality, category, pipeline_stage)

    except Exception as e:
        logger.error(f"Error in AI conversation for {phone_number}: {e}", exc_info=True)
        # Only send fallback if NO message was already sent during this processing
        if not message_sent:
            try:
                await send_message_fn(phone_number, conversation_id, "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías repetirlo?")
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
    """Update lead record with AI-extracted data"""
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
