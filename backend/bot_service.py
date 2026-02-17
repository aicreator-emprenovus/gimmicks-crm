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

REGLA MAS IMPORTANTE - LEE ESTO PRIMERO:
Antes de responder, REVISA con atención el HISTORIAL COMPLETO y los DATOS YA RECOPILADOS.
Si un dato ya fue proporcionado por el cliente en cualquier punto de la conversación, NUNCA lo pidas de nuevo.
No confirmes datos ya conocidos. No repitas información que ya diste.
Simplemente avanza al siguiente dato que FALTE.

CÓMO RESPONDER SEGÚN EL MENSAJE DEL CLIENTE:

Si el cliente SALUDA (hola, buenas, buenos días, etc.):
- Saluda de vuelta y pregunta en qué le puedes ayudar.
- Ejemplo: "Hola, bienvenido a Gimmicks. ¿En qué te puedo ayudar?"

Si el cliente PIDE o MENCIONA un tipo de producto (termos, jarros, gorras, tazas, agendas, mochilas, etc.):
- Confirma brevemente y pon catalog_search con la palabra clave del producto.
- Ejemplo: "Claro, te comparto nuestro catálogo de termos para que revises las opciones."

Si el cliente quiere COTIZAR pero no dice qué producto:
- Pregunta qué tipo de producto necesita.
- Ejemplo: "Con gusto te ayudo. ¿Qué tipo de producto necesitas cotizar?"

Si el cliente hace una PREGUNTA (precios, tiempos de entrega, métodos de pago, personalización, envíos, facturación, mínimos, etc.):
- Responde su pregunta de forma útil y concreta.
- Luego guía hacia la acción comercial con algo como: "¿Te gustaría ver nuestro catálogo de algún producto en particular?"

Si el cliente comparte CÓDIGOS de productos (como GIMN06001, JARPOR00391, etc.):
- Extráelos en extracted_data.codigos_producto separados por comas.
- Confirma y pregunta por el siguiente dato que falte.

Si el cliente envía algo que NO ENTIENDES o es ambiguo:
- NO digas que no entiendes. Interpreta lo mejor posible y responde algo útil.
- Si no puedes interpretar, di: "Cuéntame un poco más sobre lo que necesitas para poder ayudarte mejor."

RECOPILACIÓN DE DATOS (uno a la vez, en este orden):
Una vez que el cliente haya indicado qué producto quiere, pide los datos que falten de UNO EN UNO:
1. Cantidad de unidades
2. Tipo de personalización (serigrafía, bordado, UV, láser, sublimación)
3. Correo electrónico
4. Nombre y empresa
5. Ciudad de entrega y fecha

COTIZACIÓN:
Marca needs_quote=true solo cuando tengas: producto o códigos + cantidad + correo.

INFORMACIÓN DE LA EMPRESA (para responder preguntas):
- Gimmicks está en Quito, Ecuador
- Hacemos envíos a todo el país
- Personalización: serigrafía, bordado, grabado láser, impresión UV, sublimación
- Pedido mínimo: varía según producto, generalmente desde 50 unidades
- Tiempos de entrega: 7-15 días hábiles según cantidad y personalización
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
    """Search products by keyword in name or description"""
    if not keyword:
        return []
    words = keyword.strip().split()
    regex = "|".join(words)
    products = await db.products.find(
        {"$or": [
            {"name": {"$regex": regex, "$options": "i"}},
            {"description": {"$regex": regex, "$options": "i"}}
        ]},
        {"_id": 0, "code": 1, "name": 1, "description": 1, "price": 1}
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


async def get_conversation_history(db: AsyncIOMotorDatabase, conversation_id: str, limit: int = 20) -> str:
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
            lines.append(f"{role}: {text[:200]}")
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
        "personalizacion": "personalizacion",
    }
    for src, dst in field_map.items():
        val = lead.get(src)
        if val and str(val).strip() and str(val).lower() not in ("none", "null", "n/a"):
            known[dst] = str(val).strip()
    return known


async def call_llm(system_msg: str, user_msg: str) -> Optional[Dict]:
    """Call LLM and parse JSON response. Returns None on failure."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("EMERGENT_LLM_KEY not configured")
            return None

        session_id = f"bot-{uuid.uuid4().hex[:8]}"
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system_msg
        )
        chat.with_model("openai", "gpt-4o-mini")

        response_text = await chat.send_message(UserMessage(text=user_msg))

        json_match = re.search(r'\{[\s\S]*\}', response_text)
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


async def create_pending_quote(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, conversation_id: str) -> str:
    """Create a pending quote for admin review. Returns confirmation message."""
    now = datetime.now(timezone.utc)

    # Find products by codes or keyword
    codes_raw = collected_data.get("codigos_producto", "")
    product_items = []

    if codes_raw:
        # Clean codes string - handle list format ['X', 'Y'] or comma/space separated
        clean = str(codes_raw).replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        code_list = [c.strip() for c in re.split(r'[,\s]+', clean) if c.strip()]
        products = await validate_product_codes(db, code_list)
        for p in products:
            product_items.append({
                "product_id": p.get("id", ""),
                "code": p.get("code", ""),
                "product_name": p.get("name", ""),
                "description": (p.get("description") or "")[:100],
                "price": p.get("price", 0) or 0,
            })

    # Fallback: search by product keyword
    if not product_items and collected_data.get("producto"):
        products = await search_products_by_keyword(db, collected_data["producto"], limit=3)
        for p in products:
            product_items.append({
                "product_id": p.get("id", ""),
                "code": p.get("code", ""),
                "product_name": p.get("name", ""),
                "description": (p.get("description") or "")[:100],
                "price": p.get("price", 0) or 0,
            })

    quote_doc = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "phone_number": phone_number,
        "status": "pending",
        "client_name": collected_data.get("nombre", ""),
        "client_empresa": collected_data.get("empresa", ""),
        "client_correo": collected_data.get("correo", ""),
        "client_ciudad": collected_data.get("ciudad", ""),
        "items": product_items,
        "cantidad": collected_data.get("cantidad", ""),
        "fecha_entrega": collected_data.get("fecha_entrega", ""),
        "personalizacion": collected_data.get("personalizacion", ""),
        "necesita_diseno": collected_data.get("necesita_diseno", ""),
        "total": 0,
        "notes": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.quotes.insert_one(quote_doc)

    product_names = ", ".join([p["product_name"] for p in product_items[:3]]) if product_items else collected_data.get("producto", "productos solicitados")
    return (
        f"Listo, tu solicitud de cotización para {product_names} ha sido registrada.\n\n"
        f"Nuestro equipo la revisará y te la enviaremos a {collected_data.get('correo', 'tu correo')} muy pronto.\n\n"
        f"Cualquier duda adicional me escribes por aquí."
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

        # Determine next data to ask - ONE at a time in order
        has_product = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
        ordered_fields = [
            ("cantidad", "cantidad de unidades"),
            ("personalizacion", "tipo de personalización"),
            ("correo", "correo electrónico"),
            ("nombre", "nombre"),
            ("empresa", "empresa"),
            ("ciudad", "ciudad de entrega"),
            ("fecha_entrega", "fecha de entrega"),
        ]
        
        next_to_ask = ""
        all_required_done = False
        missing_fields = []
        if has_product:
            for field_key, field_label in ordered_fields:
                if not collected_data.get(field_key):
                    missing_fields.append(field_label)
            
            has_min = collected_data.get("cantidad") and collected_data.get("correo")
            if has_min and not missing_fields:
                all_required_done = True
                next_to_ask = "Ya tienes todos los datos necesarios. Marca needs_quote=true."
            elif missing_fields:
                next_to_ask = f"SIGUIENTE dato a pedir (SOLO este, nada más): {missing_fields[0]}"
        
        user_prompt = f"""INSTRUCCIÓN: Revisa TODO el historial y los datos recopilados. NO pidas nada que ya se haya proporcionado. Haz UNA sola pregunta.

{catalog_info}

=== HISTORIAL COMPLETO DE LA CONVERSACIÓN ===
{history_text}

=== DATOS YA RECOPILADOS (PROHIBIDO volver a pedir estos) ===
{collected_summary if collected_summary else "Ninguno aún"}

=== DATOS QUE AÚN FALTAN ===
{', '.join(missing_fields) if missing_fields else 'Ninguno' if all_required_done else 'Aún no se ha definido el producto'}

{next_to_ask}

MENSAJE ACTUAL DEL CLIENTE: {message_text}"""

        # Call AI
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt)

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
        extracted = ai_result.get("extracted_data", {})
        catalog_search = ai_result.get("catalog_search")
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)

        # Merge extracted data - normalize field names
        field_aliases = {
            "tipo_de_personalizacion": "personalizacion",
            "tipo_personalizacion": "personalizacion",
            "email": "correo",
            "mail": "correo",
            "codigos": "codigos_producto",
            "codigo": "codigos_producto",
            "nombre_empresa": "empresa",
        }
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                normalized_key = field_aliases.get(key, key)
                collected_data[normalized_key] = str(value).strip()

        # Send bot response
        await send_message_fn(phone_number, conversation_id, response_text)

        # Handle catalog search - send catalog LINK instead of text
        if catalog_search and catalog_search not in catalogs_sent:
            catalog_url = build_catalog_url(catalog_search)
            products = await search_products_by_keyword(db, catalog_search, limit=3)
            if products:
                preview_names = ", ".join([p.get("name", "") for p in products[:3]])
                catalog_msg = (
                    f"Aquí tienes el catálogo de {catalog_search}: {catalog_url}\n\n"
                    f"Encontrarás opciones como: {preview_names}.\n\n"
                    f"Revisa las fotos y compárteme los códigos de los que te gusten para cotizarlos."
                )
            else:
                catalog_msg = f"Revisa nuestro catálogo aquí: {catalog_url}\n\nDime los códigos que te interesen."
            await send_message_fn(phone_number, conversation_id, catalog_msg)
            catalogs_sent.append(catalog_search)

        # Handle quote
        if needs_quote and not state.get("quote_generated"):
            quote_confirm = await create_pending_quote(db, phone_number, collected_data, conversation_id)
            await send_message_fn(phone_number, conversation_id, quote_confirm)
            state_quote = True
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
        "presupuesto": "presupuesto", "personalizacion": "personalizacion"
    }
    for src, dst in field_map.items():
        if collected_data.get(src):
            update_fields[dst] = collected_data[src]

    await db.leads.update_one({"phone_number": phone_number}, {"$set": update_fields})
