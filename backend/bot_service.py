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

SYSTEM_PROMPT = """Eres Ana, asesora comercial de Gimmicks Marketing Services, empresa ecuatoriana de productos promocionales.

COMO HABLAR:
- Como persona real: natural, calida, directa
- Mensajes cortos (maximo 300 caracteres)
- NO uses emojis nunca
- NO markdown, NO listas, NO formato robot
- Tutea al cliente
- UNA sola pregunta o accion por mensaje, no bombardees con varias solicitudes a la vez
- ORTOGRAFIA IMPECABLE: usa tildes correctamente (qué, cuántos, cuál, información, personalización, cotización, etc.). Escribe en español perfecto siempre.

FLUJO SIMPLE DE CONVERSACION:

PASO 1 - ANALIZAR EL PRIMER MENSAJE:
- Si el cliente pide/menciona un tipo de producto (termos, jarros, gorras, camisetas, etc.) -> responde con algo breve y pon catalog_search con la palabra clave. El sistema enviara el link automaticamente.
- Si el cliente tiene otra consulta (precios, envios, personalizacion, tiempos, etc.) -> responde su duda de forma util y luego guia hacia que te cuente que producto necesita.
- Si el cliente saluda -> saludalo y pregunta en que le puedes ayudar.

PASO 2 - DESPUES DEL CATALOGO:
Espera a que el cliente revise y comparta codigos. Si comparte codigos, extrae en extracted_data.codigos_producto.

PASO 3 - RECOPILAR DATOS UNO A UNO:
Una vez que tengas codigos o producto claro, pide los datos que falten DE UNO EN UNO en este orden:
1. Primero: cantidad
2. Luego: tipo de personalizacion
3. Luego: correo electronico
4. Luego: nombre y empresa (puede ser junto)
5. Por ultimo: ciudad y fecha de entrega

NUNCA pidas varios datos en el mismo mensaje. Solo pide EL SIGUIENTE dato que falta.

PASO 4 - COTIZACION:
Cuando tengas al menos: codigos/producto + cantidad + correo -> marca needs_quote=true

REGLAS:
- Si el cliente da varios datos en un mensaje, extrae todos pero NO pidas mas en ese turno. Solo confirma y pide EL SIGUIENTE que falte.
- Sigue el orden natural de la conversacion, no fuerces temas
- Si el cliente cambia de tema, atiende su duda y luego retoma
- SIEMPRE extrae codigos de producto si los menciona (campo codigos_producto)

CALIFICACION:
- caliente: tiene codigos + cantidad + datos de contacto
- tibio: pidio catalogo o mostro interes concreto
- frio: pregunta general sin intencion de compra

CATALOGO:
Usa catalog_search con palabra clave cuando el cliente pida un tipo de producto.
NO listes productos. El sistema envia un link automatico.

Responde SIEMPRE en JSON valido:
{
  "response": "tu mensaje natural corto",
  "extracted_data": {},
  "catalog_search": null,
  "intent": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|pregunta_general|otra",
  "lead_quality": "tibio",
  "category": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|otra",
  "needs_quote": false,
  "needs_human": false,
  "conversation_summary": "resumen breve"
}"""


def build_catalog_url(keyword: str) -> str:
    """Build public catalog URL for the given product keyword"""
    from urllib.parse import quote
    base_url = os.environ.get("CATALOG_BASE_URL", os.environ.get("FRONTEND_URL", ""))
    if not base_url:
        base_url = os.environ.get("REACT_APP_BACKEND_URL", "").replace("/api", "")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
    return f"{base_url}/catalog?q={quote(keyword)}"


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
            # Brand new conversation
            state = _new_state(phone_number, now)
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
                    # Was completed or no data - start fresh
                    state = _new_state(phone_number, now)
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

        # Build context
        history_text = await get_conversation_history(db, conversation_id, limit=8)

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            if parts:
                collected_summary = "Datos recopilados: " + ", ".join(parts)

        catalogs_sent = state.get("catalog_sent", [])
        catalog_info = f"Catalogos ya enviados: {', '.join(catalogs_sent)}" if catalogs_sent else ""

        # Determine next data to ask - ONE at a time in order
        has_product = bool(collected_data.get("codigos_producto") or collected_data.get("producto"))
        ordered_fields = [
            ("cantidad", "cantidad de unidades"),
            ("personalizacion", "tipo de personalizacion"),
            ("correo", "correo electronico"),
            ("nombre", "nombre"),
            ("empresa", "empresa"),
            ("ciudad", "ciudad de entrega"),
            ("fecha_entrega", "fecha de entrega"),
        ]
        
        next_to_ask = ""
        all_required_done = False
        if has_product:
            for field_key, field_label in ordered_fields:
                if not collected_data.get(field_key):
                    next_to_ask = f"SIGUIENTE dato a pedir (solo este, nada mas): {field_label}"
                    break
            
            has_min = collected_data.get("cantidad") and collected_data.get("correo")
            if has_min and not next_to_ask:
                all_required_done = True
                next_to_ask = "Ya tienes todos los datos necesarios. Marca needs_quote=true."
        
        user_prompt = f"""{catalog_info}

HISTORIAL:
{history_text}

{collected_summary}
{next_to_ask}

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
            await send_message_fn(phone_number, conversation_id, "Disculpa, tuve un inconveniente. Un asesor te contactará pronto.")
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
