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

SYSTEM_PROMPT = """Eres un asesor comercial de Gimmicks Marketing Services. Tu nombre es Ana, asistente virtual.
Gimmicks es una empresa ecuatoriana especializada en productos promocionales y publicitarios.

PERSONALIDAD:
- Hablas como persona real: calido, amigable, profesional
- Mensajes CORTOS y claros (maximo 400 caracteres)
- Maximo 1 emoji por mensaje (opcional, no obligatorio)
- NO uses formato markdown (ni *, ni #, ni listas con -)
- NUNCA parezcas robot ni uses frases genericas de chatbot
- Tutea al cliente

OBJETIVO COMERCIAL:
Tu meta es SIEMPRE guiar al cliente hacia una accion comercial:
catalogo -> codigos de producto -> datos para cotizar -> cotizacion -> pedido

Aunque el cliente pregunte temas generales (horarios, envios, pagos, personalizacion, facturacion, etc.), 
responde su pregunta y luego redirige con frases naturales como:
"Si quieres te comparto el catalogo para que elijas"
"Que productos te interesan? Te paso opciones"
"Para cuantas unidades lo necesitas?"

FLUJO DE VENTA:
1. Cliente escribe -> entender que necesita
2. Si pide producto o categoria -> buscar en catalogo y mostrar opciones con CODIGOS
3. Pedir al cliente que elija codigos: "Revisalo y dime los codigos que te gusten para cotizarlos"
4. Si no sabe elegir, recomienda 3 opciones destacadas
5. Cuando tenga codigos -> pedir datos para cotizar:
   - cantidad por producto
   - ciudad de entrega
   - fecha limite
   - tipo de personalizacion (serigrafia, bordado, UV, laser, etc.)
   - si necesita diseno
   - correo electronico (obligatorio)
   - nombre de empresa
6. Con todos los datos -> marcar needs_quote=true

CATALOGO:
Cuando muestres productos del catalogo, SIEMPRE incluye el CODIGO del producto.
Formato: "Codigo: XXXXX - Nombre del producto"
Maximo 5 productos por mensaje.

DATOS A RECOPILAR:
nombre, empresa, ciudad, correo, codigos_producto (lista de codigos seleccionados), 
cantidad, fecha_entrega, personalizacion, necesita_diseno

IMPORTANTE sobre needs_quote:
Solo marca needs_quote=true cuando tengas AL MENOS:
- correo + codigos_producto (o producto claro) + cantidad
Si falta algo, pregunta de forma natural.

CALIFICACION DEL LEAD:
- caliente: tiene codigos, cantidad, fecha, presupuesto, urgencia
- tibio: interesado, pidio catalogo, esta eligiendo
- frio: pregunta general, sin intencion clara

Responde SIEMPRE en JSON valido:
{
  "response": "tu mensaje natural para el cliente",
  "extracted_data": {},
  "catalog_search": null,
  "intent": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|pregunta_general|otra",
  "lead_quality": "tibio",
  "category": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|otra",
  "needs_quote": false,
  "needs_human": false,
  "conversation_summary": "resumen breve"
}

El campo catalog_search: pon una palabra clave si el cliente pide ver productos de una categoria.
Ejemplo: si pide "termos" -> catalog_search: "termo". Si pide "gorras" -> catalog_search: "gorra".
Si no pide catalogo, deja null."""


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
    """Validate product codes and return matching products"""
    found = []
    for code in codes:
        code_clean = code.strip().upper()
        product = await db.products.find_one(
            {"code": {"$regex": f"^{re.escape(code_clean)}", "$options": "i"}},
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
        desc = p.get("description", "")
        desc_short = f" - {desc[:60]}" if desc else ""
        lines.append(f"{i}. Codigo: {code}")
        lines.append(f"   {name}{desc_short}")
        lines.append("")

    lines.append("Revisalo y dime los codigos que te gusten para cotizarlos.")
    return "\n".join(lines)


async def get_conversation_history(db: AsyncIOMotorDatabase, conversation_id: str, limit: int = 10) -> str:
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


async def call_llm(system_msg: str, user_msg: str) -> Dict:
    """Call LLM and parse JSON response"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise Exception("EMERGENT_LLM_KEY not configured")

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


async def create_pending_quote(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, conversation_id: str) -> str:
    """Create a pending quote for admin review. Returns confirmation message."""
    now = datetime.now(timezone.utc)

    # Find products by codes or keyword
    codes_raw = collected_data.get("codigos_producto", "")
    product_items = []

    if codes_raw:
        code_list = [c.strip() for c in str(codes_raw).replace(",", " ").split() if c.strip()]
        products = await validate_product_codes(db, code_list)
        for p in products:
            product_items.append({
                "product_id": p.get("id", ""),
                "code": p.get("code", ""),
                "product_name": p.get("name", ""),
                "description": p.get("description", "")[:100],
                "price": p.get("price", 0),
            })

    # Fallback: search by product keyword
    if not product_items and collected_data.get("producto"):
        products = await search_products_by_keyword(db, collected_data["producto"], limit=3)
        for p in products:
            product_items.append({
                "product_id": p.get("id", ""),
                "code": p.get("code", ""),
                "product_name": p.get("name", ""),
                "description": p.get("description", "")[:100],
                "price": p.get("price", 0),
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
        f"Listo! Tu solicitud de cotizacion para {product_names} ha sido registrada.\n\n"
        f"Nuestro equipo la revisara y te la enviaremos a {collected_data.get('correo', 'tu correo')} muy pronto.\n\n"
        f"Cualquier duda adicional me escribes por aqui."
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
            state = {
                "phone_number": phone_number,
                "collected_data": {},
                "lead_quality": "frio",
                "category": None,
                "catalog_sent": [],
                "quote_generated": False,
                "transferred_to_human": False,
                "message_count": 0,
                "last_interaction": now.isoformat()
            }
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": state},
                upsert=True
            )

        # If transferred, don't auto-respond
        if state.get("transferred_to_human"):
            return

        # If was marked as "perdido" but client responds, reactivate
        lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
        if lead and lead.get("funnel_stage") == "perdido":
            await db.leads.update_one(
                {"phone_number": phone_number},
                {"$set": {"funnel_stage": "lead", "status": "active", "updated_at": now.isoformat()}}
            )
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {"transferred_to_human": False, "quote_generated": False}}
            )
            state["transferred_to_human"] = False
            state["quote_generated"] = False

        collected_data = state.get("collected_data", {})
        msg_count = state.get("message_count", 0) + 1

        # Build context
        history_text = await get_conversation_history(db, conversation_id, limit=8)

        # Get a small product sample for AI context
        sample_products = await db.products.find({}, {"_id": 0, "code": 1, "name": 1}).limit(10).to_list(10)
        sample_text = "\n".join([f"- {p['code']}: {p['name']}" for p in sample_products])

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            if parts:
                collected_summary = "Datos recopilados: " + ", ".join(parts)

        catalogs_sent = state.get("catalog_sent", [])
        catalog_info = f"Catalogos ya enviados: {', '.join(catalogs_sent)}" if catalogs_sent else "No se ha enviado catalogo aun."

        required = ["correo", "cantidad"]
        needs_product = not collected_data.get("codigos_producto") and not collected_data.get("producto")
        missing = [f for f in required if not collected_data.get(f)]
        if needs_product:
            missing.insert(0, "producto o codigos")

        missing_str = f"Datos que FALTAN: {', '.join(missing)}." if missing else "Tienes todos los datos. Puedes marcar needs_quote=true."

        user_prompt = f"""EJEMPLOS DE PRODUCTOS EN CATALOGO:
{sample_text}

{catalog_info}

HISTORIAL:
{history_text}

{collected_summary}
{missing_str}

MENSAJE DEL CLIENTE: {message_text}"""

        # Call AI
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt)

        response_text = ai_result.get("response", "Gracias por escribirnos! Como puedo ayudarte?")
        extracted = ai_result.get("extracted_data", {})
        catalog_search = ai_result.get("catalog_search")
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)

        # Merge extracted data
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                collected_data[key] = str(value).strip()

        # Send bot response
        await send_message_fn(phone_number, conversation_id, response_text)

        # Handle catalog search
        if catalog_search and catalog_search not in catalogs_sent:
            products = await search_products_by_keyword(db, catalog_search, limit=8)
            if products:
                catalog_msg = await format_catalog_message(products, catalog_search)
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
            transfer_msg = "Voy a pasar tu caso a Ana Maria, nuestra asesora. Ella te contactara pronto!"
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
            await send_message_fn(phone_number, conversation_id, "Disculpa, tuve un inconveniente. Un asesor te contactara pronto.")
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
