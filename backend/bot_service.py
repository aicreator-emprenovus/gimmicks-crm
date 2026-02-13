"""
AI-powered conversational bot for Gimmicks CRM.
Uses LLM to understand natural language, extract lead data, and manage sales conversations.
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

SYSTEM_PROMPT = """Eres el asistente de ventas de Gimmicks Marketing Services, una empresa ecuatoriana especializada en productos promocionales y publicitarios.

Tu objetivo es atender clientes de forma natural e inteligente por WhatsApp.

REGLAS DE FORMATO:
- Responde SOLO en espanol
- NO uses formato markdown (ni **, ni ##, ni ``` ni listas con -)
- Usa texto plano para WhatsApp
- Maximo 500 caracteres por respuesta
- Se amigable, profesional y conciso

REGLAS DE CONVERSACION:
1. Entiende la intencion del cliente desde su primer mensaje
2. Recopila datos del lead de forma NATURAL durante la conversacion. Los campos son:
   nombre, empresa, ciudad, correo, producto (que necesita), cantidad, fecha_entrega, presupuesto, personalizacion
3. NO hagas preguntas tipo formulario rigido. Si el cliente da varios datos a la vez, extrae todos
4. Si el cliente pregunta por productos, responde con lo que sabes del catalogo
5. IMPORTANTE: Solo marca needs_quote=true cuando tengas AL MENOS: nombre + empresa + correo + producto + cantidad. Si faltan datos, pregunta de forma natural
6. Si el cliente quiere hablar con una persona, marca needs_human=true
7. Si el cliente saluda, presentate brevemente y pregunta en que puedes ayudar
8. Cuando el cliente da informacion parcial (ej: solo dice que quiere tazas), reconoce lo que dijo y pregunta por los datos que faltan

CALIFICACION DEL LEAD:
- caliente: urgencia alta, presupuesto definido, cantidad clara, producto especifico, empresa real
- tibio: interesado pero explorando, sin urgencia clara, algunos datos
- frio: pregunta general, sin intencion clara de compra, solo curiosidad

CATEGORIAS:
- cotizacion_directa: Quiere precio/cotizacion de algo especifico
- solicitud_catalogo: Quiere ver productos disponibles
- consulta_ideas: Busca sugerencias para un evento o necesidad
- pedido_estacional: Productos para temporada o fecha especifica
- otra: Cualquier otra consulta

Responde SIEMPRE en formato JSON valido (sin comentarios):
{
  "response": "tu mensaje para el cliente",
  "extracted_data": {},
  "intent": "cotizacion_directa",
  "lead_quality": "tibio",
  "category": "cotizacion_directa",
  "needs_quote": false,
  "needs_human": false,
  "conversation_summary": "resumen breve"
}"""


def format_price_ecuador(price: float) -> str:
    return f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def get_products_context(db: AsyncIOMotorDatabase, query: str = "") -> str:
    """Get product catalog context for the AI"""
    search_query = {}
    if query:
        search_query = {"$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"category_1": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]}

    products = await db.products.find(search_query, {"_id": 0}).limit(20).to_list(20)

    if not products and query:
        products = await db.products.find({}, {"_id": 0}).limit(15).to_list(15)

    if not products:
        return "No hay productos cargados en el catalogo actualmente."

    lines = []
    for p in products:
        price_str = format_price_ecuador(p["price"]) if p.get("price") else "Consultar"
        lines.append(f"- {p['name']}: {p.get('description', '')[:80]} | Precio: {price_str}")
    return "\n".join(lines)


async def get_conversation_history(db: AsyncIOMotorDatabase, conversation_id: str, limit: int = 10) -> List[Dict]:
    """Get recent messages for context"""
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0, "sender": 1, "content": 1, "timestamp": 1}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    messages.reverse()
    return messages


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

    user_message = UserMessage(text=user_msg)
    response_text = await chat.send_message(user_message)

    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        return json.loads(json_match.group())

    return {
        "response": response_text,
        "extracted_data": {},
        "intent": "otra",
        "lead_quality": "frio",
        "category": "otra",
        "needs_quote": False,
        "needs_human": False,
        "conversation_summary": ""
    }


async def generate_quote_from_data(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict) -> str:
    """Generate a quote message from collected lead data"""
    product_need = collected_data.get("producto", "").lower()

    products = await db.products.find({
        "$or": [
            {"name": {"$regex": product_need, "$options": "i"}},
            {"category_1": {"$regex": product_need, "$options": "i"}},
            {"description": {"$regex": product_need, "$options": "i"}}
        ]
    }, {"_id": 0}).limit(5).to_list(5)

    if not products:
        products = await db.products.find({}, {"_id": 0}).limit(3).to_list(3)

    if not products:
        return "Gracias por tu interes. No encontramos productos en nuestro catalogo actual. Un asesor te contactara con opciones personalizadas."

    cantidad_str = collected_data.get("cantidad", "")
    try:
        cantidad = int(re.search(r'\d+', str(cantidad_str)).group()) if cantidad_str else None
    except Exception:
        cantidad = None

    quantities = [cantidad] if cantidad else [50, 100, 300]

    lines = ["COTIZACION GIMMICKS\n"]
    lines.append(f"Cliente: {collected_data.get('nombre', 'N/A')}")
    lines.append(f"Empresa: {collected_data.get('empresa', 'N/A')}")
    lines.append(f"Ciudad: {collected_data.get('ciudad', 'N/A')}\n")

    total_general = 0
    quote_items = []

    for product in products[:3]:
        product_name = product.get("name", "Producto")
        base_price = product.get("price", 0) or 5.00

        lines.append(product_name)
        if product.get("description"):
            lines.append(f"  {product['description'][:80]}")

        for qty in quantities:
            if qty >= 300:
                unit_price = base_price * 0.85
            elif qty >= 100:
                unit_price = base_price * 0.90
            else:
                unit_price = base_price

            subtotal = unit_price * qty
            total_general += subtotal
            lines.append(f"  {qty} unidades: {format_price_ecuador(unit_price)} c/u = {format_price_ecuador(subtotal)}")

            quote_items.append({
                "product_id": product.get("id", ""),
                "product_name": product_name,
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal
            })

        lines.append("")

    if collected_data.get("personalizacion") and collected_data["personalizacion"].lower() not in ["no", "ninguna", "n/a"]:
        lines.append(f"Personalizacion: {collected_data['personalizacion']}")
        lines.append("Nota: El precio puede variar segun complejidad del diseno.\n")

    fecha = collected_data.get("fecha_entrega", "")
    if any(w in str(fecha).lower() for w in ["urgente", "pronto", "rapido", "express", "hoy", "manana"]):
        delivery = "3-5 dias habiles (servicio express)"
    else:
        delivery = "7-10 dias habiles"

    lines.append(f"Tiempo de entrega: {delivery}")
    lines.append("\nPrecios incluyen IVA")
    lines.append("Cotizacion valida por 15 dias")

    conv = await db.conversations.find_one({"phone_number": phone_number}, {"_id": 0, "id": 1})
    quote_doc = {
        "id": str(uuid.uuid4()),
        "conversation_id": conv["id"] if conv else "",
        "phone_number": phone_number,
        "client_name": collected_data.get("nombre"),
        "client_empresa": collected_data.get("empresa"),
        "items": quote_items,
        "total": total_general,
        "delivery_time": delivery,
        "personalization": collected_data.get("personalizacion"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.quotes.insert_one(quote_doc)

    return "\n".join(lines)


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

        # Already transferred to human — don't respond
        if state.get("transferred_to_human"):
            return

        collected_data = state.get("collected_data", {})
        msg_count = state.get("message_count", 0) + 1

        # Build context for the AI
        history = await get_conversation_history(db, conversation_id, limit=8)
        history_text = ""
        for msg in history:
            role = "Cliente" if msg["sender"] == "user" else "Gimmicks"
            text = msg.get("content", {}).get("text", "")
            if text:
                history_text += f"{role}: {text}\n"

        products_context = await get_products_context(db, collected_data.get("producto", ""))

        collected_summary = ""
        if collected_data:
            parts = [f"{k}: {v}" for k, v in collected_data.items() if v]
            collected_summary = "Datos recopilados hasta ahora: " + ", ".join(parts)

        user_prompt = f"""CATALOGO DE PRODUCTOS:
{products_context}

HISTORIAL DE CONVERSACION:
{history_text}

{collected_summary}

MENSAJE ACTUAL DEL CLIENTE: {message_text}

Analiza el mensaje, extrae datos nuevos y responde de forma natural."""

        # Call LLM
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt)

        response_text = ai_result.get("response", "Gracias por tu mensaje. Un asesor te contactara pronto.")
        extracted = ai_result.get("extracted_data", {})
        lead_quality = ai_result.get("lead_quality", state.get("lead_quality", "frio"))
        category = ai_result.get("category", state.get("category"))
        needs_quote = ai_result.get("needs_quote", False)
        needs_human = ai_result.get("needs_human", False)

        # Merge extracted data into collected_data
        for key, value in extracted.items():
            if value and str(value).strip() and str(value).lower() not in ["null", "none", "n/a", ""]:
                collected_data[key] = str(value).strip()

        # Update conversation state
        state_update = {
            "collected_data": collected_data,
            "lead_quality": lead_quality,
            "category": category,
            "message_count": msg_count,
            "last_interaction": now.isoformat()
        }

        # Send bot response
        await send_message_fn(phone_number, conversation_id, response_text)

        # Handle quote generation
        if needs_quote and not state.get("quote_generated"):
            quote_msg = await generate_quote_from_data(db, phone_number, collected_data)
            await send_message_fn(phone_number, conversation_id, quote_msg)
            state_update["quote_generated"] = True

            # After quote, transfer to human
            transfer_msg = (
                "He recopilado toda tu informacion.\n\n"
                "Ana Maria, nuestra asesora comercial, se pondra en contacto contigo "
                "muy pronto para finalizar los detalles.\n\n"
                "Gracias por preferirnos!"
            )
            await send_message_fn(phone_number, conversation_id, transfer_msg)
            state_update["transferred_to_human"] = True
            needs_human = True

        # Handle human transfer
        if needs_human and not state.get("transferred_to_human"):
            if not state_update.get("transferred_to_human"):
                transfer_msg = (
                    "Voy a transferir tu caso a Ana Maria, nuestra asesora comercial.\n"
                    "Ella te contactara muy pronto. Gracias!"
                )
                await send_message_fn(phone_number, conversation_id, transfer_msg)
                state_update["transferred_to_human"] = True

        await db.conversation_states.update_one(
            {"phone_number": phone_number},
            {"$set": state_update}
        )

        # Update lead with AI-extracted data
        await update_lead_from_ai(db, phone_number, conversation_id, collected_data, lead_quality, category, needs_human or (needs_quote and state_update.get("transferred_to_human")))

    except Exception as e:
        logger.error(f"Error in AI conversation for {phone_number}: {e}", exc_info=True)
        try:
            await send_message_fn(
                phone_number, conversation_id,
                "Disculpa, tuve un problema procesando tu mensaje. Un asesor te contactara pronto."
            )
        except Exception:
            pass


async def update_lead_from_ai(
    db: AsyncIOMotorDatabase,
    phone_number: str,
    conversation_id: str,
    collected_data: Dict,
    lead_quality: str,
    category: Optional[str],
    is_complete: bool
):
    """Update lead record with AI-extracted data"""
    now = datetime.now(timezone.utc)

    lead = await db.leads.find_one({"phone_number": phone_number}, {"_id": 0})
    if not lead:
        return

    update_fields = {
        "updated_at": now.isoformat(),
        "last_message_at": now.isoformat()
    }

    # Map quality to classification
    quality_map = {"caliente": "caliente", "tibio": "tibio", "frio": "frio"}
    if lead_quality in quality_map:
        update_fields["classification"] = quality_map[lead_quality]

    if category:
        update_fields["ai_category"] = category

    # Update name from collected data
    if collected_data.get("nombre"):
        update_fields["name"] = collected_data["nombre"]
        # Also update conversation contact_name
        await db.conversations.update_one(
            {"phone_number": phone_number},
            {"$set": {"contact_name": collected_data["nombre"]}}
        )

    # Store additional lead data
    field_map = {
        "empresa": "empresa",
        "ciudad": "ciudad",
        "correo": "correo",
        "producto": "producto_interes",
        "cantidad": "cantidad_estimada",
        "fecha_entrega": "fecha_entrega",
        "presupuesto": "presupuesto",
        "personalizacion": "personalizacion"
    }

    for src_field, dst_field in field_map.items():
        if collected_data.get(src_field):
            update_fields[dst_field] = collected_data[src_field]

    # If conversation is complete, mark as qualified
    if is_complete:
        update_fields["funnel_stage"] = "pedido"

    await db.leads.update_one({"phone_number": phone_number}, {"$set": update_fields})
