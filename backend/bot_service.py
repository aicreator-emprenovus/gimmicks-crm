"""
AI-powered conversational bot for Gimmicks CRM.
Human-like sales assistant that guides customers through catalog, quoting, and purchase.
"""
import os
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Ana, asesora comercial de Gimmicks Marketing Services, empresa ecuatoriana de productos promocionales y publicitarios.

PERSONALIDAD:
- Habla como persona real, cálida y profesional
- Mensajes cortos, máximo 300 caracteres
- NO uses emojis nunca
- NO uses formato markdown, listas con guiones ni asteriscos
- Tutea al cliente
- Ortografía impecable: siempre usa tildes (qué, cuántos, cuál, información, personalización, cotización, dirección, etc.)
- Solo haz UNA pregunta por mensaje

REGLA MÁS IMPORTANTE - LEE ESTO PRIMERO:
Antes de responder, REVISA con atención el HISTORIAL COMPLETO y los DATOS YA RECOPILADOS.
Si un dato ya fue proporcionado por el cliente en cualquier punto de la conversación, NUNCA lo pidas de nuevo.
NUNCA repitas un mensaje que ya enviaste antes. Si necesitas comunicar algo similar, reformúlalo con palabras diferentes y más breves.
No confirmes datos ya conocidos. No repitas información que ya diste.
Simplemente avanza al siguiente dato que FALTE o responde la nueva consulta del cliente.

EXTRACCIÓN DE DATOS - REGLA CRÍTICA:
SIEMPRE extrae TODOS los datos que el cliente proporcione en CADA mensaje, sin importar en qué paso del flujo estés.
Si el cliente dice "Soy Laura de Grupo ABC, quiero 500 gorras GORALN00001, mi correo es laura@abc.com, en Quito":
- extracted_data.nombre = "Laura"
- extracted_data.empresa = "Grupo ABC"
- extracted_data.codigos_producto = "GORALN00001"
- extracted_data.cantidades_por_producto = "GORALN00001:500"
- extracted_data.correo = "laura@abc.com"
- extracted_data.ciudad = "Quito"
NUNCA ignores datos que el cliente ya proporcionó. Extrae TODO en extracted_data y solo pregunta por lo que FALTA.

FLUJO OBLIGATORIO DE LA CONVERSACIÓN (SIGUE ESTE ORDEN ESTRICTAMENTE):

PASO 1 - SALUDO:
Cuando el cliente escribe por primera vez o saluda:
- Saluda cordialmente y preséntate como Ana de Gimmicks.
- Pregunta en qué le puedes ayudar.

PASO 2 - NOMBRE DEL CLIENTE:
Antes de avanzar con productos, NECESITAS el nombre del cliente.
- Si aún no tienes el nombre, pregúntale: "¿Me compartes tu nombre para registrarte?"
- Guarda el nombre en extracted_data.nombre.
- Una vez que tengas el nombre, úsalo para dirigirte al cliente de ahí en adelante.

PASO 3 - PRODUCTO:
Si el cliente PIDE o MENCIONA cualquier tipo de producto (termos, jarros, gorras, tazas, zapatos, camisetas, etc.):
- Confirma brevemente que vas a buscar opciones.
- SIEMPRE pon catalog_search con la palabra clave del producto, incluso si no estás seguro de que lo tengamos. El sistema decidirá qué link enviar.
- NO preguntes cantidad ni nada más. Solo presenta las opciones y pide que te compartan los códigos de los productos que les gusten.
- Termina el mensaje pidiendo que revisen el catálogo y compartan los códigos.

Si el cliente pide el "catálogo completo" o "catálogo general" o "todo el catálogo":
- NO pongas catalog_search. El sistema enviará automáticamente el PDF del catálogo completo.
- Solo responde que le enviarás el catálogo completo para que pueda revisarlo.

PASO 4 - CONFIRMACIÓN DE CÓDIGOS:
Si el cliente comparte CÓDIGOS de productos (como GIMN06001, JARPOR00391, etc.):
- Agrégalos a extracted_data.codigos_producto (SIEMPRE la lista COMPLETA acumulada, separada por comas).
- Si el cliente pide QUITAR un código, devuelve la lista sin ese código.
- AHORA sí pregunta la cantidad exacta de cada producto, MENCIONANDO EL NOMBRE de cada uno. Ejemplo: "¿Cuántas unidades necesitas de cada uno? Por ejemplo, del Jarro Porcelana 11oz y del Jarro Bali 11oz."
- Usa extracted_data.cantidades_por_producto con formato "CODIGO:cantidad, CODIGO:cantidad".

PASO 5 - DATOS ADICIONALES (uno a la vez, SOLO después de tener códigos Y cantidades):
Una vez que tengas códigos Y cantidades, pide los datos que falten de UNO EN UNO en este orden:
1. Color de logotipo: pregunta "¿El logotipo de tu empresa será a un color o full color?"
2. Correo electrónico
3. Nombre de empresa
4. Ciudad de entrega
5. Fecha de entrega deseada

REGLAS ADICIONALES:
- Si el cliente SALUDA (hola, buenas, buenos días, etc.): Saluda, preséntate y pregunta en qué le puedes ayudar. Si no tienes su nombre, pídelo.
- Si el cliente quiere COTIZAR pero no dice qué producto: Primero asegúrate de tener su nombre, luego pregunta qué tipo de producto necesita.
- Si el cliente hace una PREGUNTA (precios, tiempos de entrega, etc.): Responde y guía hacia la acción comercial.
- Si el cliente envía algo que NO ENTIENDES o es ambiguo: Interpreta lo mejor posible.
- extracted_data.cantidad es la cantidad general (si aplica a todos los productos por igual).
- Si el cliente menciona un producto genérico (ej: "jarros"), ponlo en extracted_data.producto.

COTIZACIÓN:
Marca needs_quote=true ÚNICAMENTE cuando tengas TODOS estos datos: códigos de producto + cantidad + correo electrónico + nombre de empresa. Los cuatro datos son obligatorios.
NUNCA marques needs_quote=true si aún no tienes el correo Y la empresa del cliente.
Si el cliente cambia productos o cantidades DESPUÉS de la primera cotización, marca needs_quote=true de nuevo para actualizarla.

INFORMACIÓN DE LA EMPRESA:
- Gimmicks está en Quito, Ecuador
- Envíos a todo el país
- Personalización disponible con logotipo a un color o full color
- Pedido mínimo: generalmente desde 50 unidades
- Tiempos de entrega: 7-15 días hábiles
- Métodos de pago: transferencia bancaria, tarjeta de crédito
- Facturación electrónica disponible

CALIFICACIÓN:
- caliente: tiene códigos + cantidad + datos de contacto
- tibio: pidió catálogo o mostró interés concreto
- frio: pregunta general sin intención de compra

Responde SIEMPRE en JSON válido:
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


EXTERNAL_CATALOG_PDF = "https://gimmicks.com.ec/wp-content/uploads/2026/01/CATALOGO-2026-CON-PRECIOS-2.pdf"


def build_catalog_url(keyword: str) -> str:
    """Build public catalog URL for the given product keyword"""
    from urllib.parse import quote
    base_url = os.environ.get("CATALOG_BASE_URL", "").strip().rstrip("/")
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
    """Search products by keyword in name, description, or categories (supports both old and new schema)"""
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
    products = await db.products.find(
        {"$or": [
            {"name": {"$regex": regex, "$options": "i"}},
            {"description": {"$regex": regex, "$options": "i"}},
            {"categories": {"$regex": regex, "$options": "i"}},
            {"category_1": {"$regex": regex, "$options": "i"}},
            {"category_2": {"$regex": regex, "$options": "i"}},
            {"category_3": {"$regex": regex, "$options": "i"}}
        ]},
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
    """Get recent messages formatted as conversation text"""
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0, "sender": 1, "content": 1}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    messages.reverse()

    lines = []
    for msg in messages:
        role = "Cliente" if msg["sender"] == "user" else "Ana (Gimmicks)"
        text = msg.get("content", {}).get("text", "")
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


async def load_known_client_data(db: AsyncIOMotorDatabase, phone_number: str) -> Dict:
    """Load previously saved data for a returning client from leads collection"""
    lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
    if not lead:
        return {}
    known = {}
    field_map = {
        "name": "nombre",
        "empresa": "empresa",
        "ciudad": "ciudad",
        "correo": "correo",
        "producto_interes": "producto",
        "codigos_producto": "codigos_producto",
        "cantidad_estimada": "cantidad",
        "fecha_entrega": "fecha_entrega",
        "personalizacion": "color_logo",
    }
    for src, dst in field_map.items():
        val = lead.get(src)
        if val and str(val).strip() and str(val).lower() not in ("none", "null", "n/a"):
            known[dst] = str(val).strip()
    return known


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
        chat.with_model("openai", "gpt-4o")
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
    """Create a fresh conversation state"""
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
        "last_interaction": now.isoformat()
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



async def process_ai_conversation(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    message_text: str,
    conversation_id: str,
    send_message_fn
):
    """Main AI conversation handler"""
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
                    return
                else:
                    # Resume - clear the flag and continue normally
                    await db.conversation_states.update_one(
                        {"phone_number": phone_number},
                        {"$unset": {"waiting_resume_decision": ""}, "$set": {"last_interaction": now.isoformat()}}
                    )
                    state.pop("waiting_resume_decision", None)
                    await send_message_fn(phone_number, conversation_id, "Perfecto, retomamos donde quedamos.")
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

        # Build context - load FULL conversation history
        history_text = await get_conversation_history(db, conversation_id, limit=40)

        # Refresh collected_data from lead (in case admin updated it)
        known_data = await load_known_client_data(db, phone_number)
        for k, v in known_data.items():
            if v and not collected_data.get(k):
                collected_data[k] = v

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            if parts:
                collected_summary = "\n".join(parts)

        catalogs_sent = state.get("catalog_sent", [])
        catalog_info = f"Catalogos ya enviados: {', '.join(catalogs_sent)}" if catalogs_sent else ""

        # Determine next data to ask - follow the strict flow
        has_codes = bool(collected_data.get("codigos_producto"))
        has_product_interest = bool(collected_data.get("producto"))
        catalog_already_sent = len(catalogs_sent) > 0

        ordered_fields = []
        next_to_ask = ""
        all_required_done = False
        missing_fields = []

        if has_codes:
            # Client confirmed codes -> now ask quantity, then rest
            ordered_fields = [
                ("cantidad", "cantidad exacta de unidades para cada producto"),
                ("color_logo", "color de logotipo (un color o full color)"),
                ("correo", "correo electrónico"),
                ("empresa", "nombre de empresa"),
                ("ciudad", "ciudad de entrega"),
                ("fecha_entrega", "fecha de entrega deseada"),
            ]
            # Also check cantidades_por_producto as valid quantity
            for field_key, field_label in ordered_fields:
                val = collected_data.get(field_key)
                if field_key == "cantidad":
                    val = val or collected_data.get("cantidades_por_producto")
                if not val:
                    missing_fields.append(field_label)

            has_min = (collected_data.get("cantidad") or collected_data.get("cantidades_por_producto")) and collected_data.get("correo") and collected_data.get("empresa")
            if has_min:
                # Required data complete - generate quote. Optional fields can be asked after.
                all_required_done = True
                optional_missing = [f for f in missing_fields if f in ("ciudad de entrega", "fecha de entrega deseada")]
                if optional_missing:
                    next_to_ask = f"IMPORTANTE: Ya tienes TODOS los datos obligatorios. DEBES marcar needs_quote=true AHORA. Además, puedes preguntar: {optional_missing[0]}"
                else:
                    next_to_ask = "Ya tienes todos los datos necesarios. Marca needs_quote=true."
            elif missing_fields:
                next_to_ask = f"SIGUIENTE dato a pedir (SOLO este, nada más): {missing_fields[0]}"

            # Resolve product names for codes so bot can mention them
            codes_raw = collected_data.get("codigos_producto", "")
            if codes_raw and not collected_data.get("cantidad"):
                clean = str(codes_raw).replace("[","").replace("]","").replace("'","").replace('"','')
                code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
                validated = await validate_product_codes(db, code_list)
                if validated:
                    product_names_list = ", ".join([f"{p.get('name','')} ({p.get('code','')})" for p in validated])
                    next_to_ask += f"\nPRODUCTOS CONFIRMADOS POR EL CLIENTE: {product_names_list}. Pregunta cuántas unidades de CADA UNO mencionando sus nombres."

        elif has_product_interest and catalog_already_sent:
            # Catalog was sent, waiting for codes
            next_to_ask = "ESPERANDO: El cliente ya vio el catálogo. Espera a que comparta los CÓDIGOS de los productos que le gusten. NO pidas cantidad todavía. Si el cliente pregunta algo, responde y recuérdale que comparta los códigos."
        elif has_product_interest and not catalog_already_sent:
            # Product mentioned but catalog not sent yet
            next_to_ask = "Debes enviar el catálogo (catalog_search) con la palabra clave del producto. NO preguntes cantidad."
        else:
            next_to_ask = "Aún no se ha definido el producto. Pregunta qué necesita el cliente."
        
        # Pre-check catalog availability for product searches
        catalog_availability = ""
        if message_text:
            # Simple keyword detection to pre-check inventory
            product_keywords = ["jarro", "termo", "gorra", "taza", "agenda", "mochila", "bolso", "esfero",
                              "boligrafo", "camiseta", "polo", "tecnolog", "usb", "cargador", "parlante",
                              "botella", "vaso", "llavero", "libreta", "cuaderno", "bolsa", "paragua"]
            msg_lower = message_text.lower()
            for kw in product_keywords:
                if kw in msg_lower:
                    prods = await search_products_by_keyword(db, kw, limit=3)
                    if prods:
                        names = ", ".join([p.get("name", "") for p in prods[:3]])
                        catalog_availability = f"\nPRODUCTOS ENCONTRADOS para '{kw}': {names}. Sí tenemos productos en esta categoría."
                    else:
                        catalog_availability = f"\nNO HAY PRODUCTOS en inventario para '{kw}'. Informa al cliente que por el momento no tenemos esa línea disponible y recomiéndale productos similares que sí tengamos."
                    break

        # Check if there's already a quote for context
        has_existing_quote = state.get("quote_generated", False)
        quote_context = ""
        if has_existing_quote:
            quote_context = "NOTA: Ya existe una cotización pendiente. Si el cliente agrega, quita o cambia productos/cantidades, marca needs_quote=true para ACTUALIZAR la cotización."

        user_prompt = f"""INSTRUCCIÓN: Revisa TODO el historial y los datos recopilados. NO pidas nada que ya se haya proporcionado. Haz UNA sola pregunta por mensaje. Tu respuesta debe ser UN solo mensaje coherente.
IMPORTANTE: En extracted_data.codigos_producto siempre devuelve la lista COMPLETA ACUMULADA de códigos (no solo los nuevos).
Si vas a enviar un catálogo (catalog_search), NO hagas otra pregunta en el mismo mensaje. Solo presenta opciones y el catálogo.
PROHIBIDO repetir o parafrasear tu mensaje anterior. Si ya confirmaste algo, avanza directamente al siguiente paso.
PROHIBIDO pedir el nombre si ya lo tienes en los datos recopilados. Dirígete al cliente por su nombre.
Pide UN SOLO dato por mensaje. No combines preguntas.

{catalog_info}
{catalog_availability}
{quote_context}

=== HISTORIAL COMPLETO DE LA CONVERSACIÓN ===
{history_text}

=== DATOS YA RECOPILADOS (PROHIBIDO volver a pedir estos) ===
{collected_summary if collected_summary else "Ninguno aún"}

=== DATOS QUE AÚN FALTAN ===
{', '.join(missing_fields) if missing_fields else 'Ninguno' if all_required_done else 'Aún no se ha definido el producto'}

{next_to_ask}

MENSAJE ACTUAL DEL CLIENTE: {message_text}"""

        # Call AI with persistent session per phone
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt, phone_number)

        # If LLM failed, respond with friendly greeting
        if ai_result is None:
            is_first_msg = msg_count <= 1
            if is_first_msg:
                fallback = "Hola, gracias por contactarnos. ¿En qué te puedo ayudar?"
            else:
                fallback = "Gracias por tu mensaje. ¿En qué más te puedo ayudar?"
            await send_message_fn(phone_number, conversation_id, fallback)
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
        extracted = ai_result.get("extracted_data", {})
        catalog_search = ai_result.get("catalog_search")
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)

        # Anti-duplication: check if response is too similar to last bot message
        last_bot_msg = await db.messages.find_one(
            {"conversation_id": conversation_id, "sender": "bot"},
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
        field_aliases = {
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
        }
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                normalized_key = field_aliases.get(key, key)
                collected_data[normalized_key] = str(value).strip()

        # Check if quote will be generated BEFORE sending AI response
        # Force quote creation when all required data is present (codes + qty + email + empresa)
        will_generate_quote = False
        if not needs_quote and not state.get("quote_generated", False):
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
        catalog_full_keywords = ["catálogo completo", "catalogo completo", "catálogo general", "catalogo general", "todo el catálogo", "todo el catalogo", "catálogo pdf", "catalogo pdf"]
        is_full_catalog_request = any(kw in message_text.lower() for kw in catalog_full_keywords)

        # Only send AI response if we are NOT about to generate a quote
        if not will_generate_quote:
            if is_full_catalog_request:
                catalog_msg = (
                    f"{response_text}\n\n"
                    f"Aquí puedes revisar nuestro catálogo completo con precios: {EXTERNAL_CATALOG_PDF}"
                )
                await send_message_fn(phone_number, conversation_id, catalog_msg)
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
                        f"Puedes revisar nuestro catálogo completo con precios aquí: {EXTERNAL_CATALOG_PDF}"
                    )
                await send_message_fn(phone_number, conversation_id, catalog_msg)
                catalogs_sent.append(catalog_search)
            else:
                await send_message_fn(phone_number, conversation_id, response_text)

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
            else:
                # Quote was updated - still respond to the user
                update_notify = response_text or "Tu cotización ha sido actualizada. Nuestro equipo la revisará pronto."
                await send_message_fn(phone_number, conversation_id, update_notify)
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
                "last_interaction": now.isoformat()
            }}
        )

        # Update lead
        await update_lead_from_ai(db, phone_number, collected_data, lead_quality, category, pipeline_stage)

    except Exception as e:
        logger.error(f"Error in AI conversation for {phone_number}: {e}", exc_info=True)
        try:
            await send_message_fn(phone_number, conversation_id, "Gracias por contactarnos, en un momento atenderemos tu requerimiento.")
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
