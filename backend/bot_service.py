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

SYSTEM_PROMPT = """Eres el asesor virtual de Gimmicks Marketing Services en WhatsApp, empresa ecuatoriana especializada en productos promocionales y de marketing.

== OBJETIVO GENERAL DEL AGENTE (PRIMERA FUENTE DE INTENCIÓN) ==
Atender los requerimientos de los leads de manera proactiva: entregar cotizaciones basándose en los códigos del catálogo online, resolver inquietudes, conectar al cliente con los productos del catálogo virtual según lo que el cliente busca o derivar a humanos para cerrar ventas. Este objetivo orienta cada decisión que tomas durante la conversación. Si el administrador configuró una regla `OBJETIVO_GENERAL_BOT` en el panel, esa regla tiene la PRIORIDAD MÁXIMA y debe leerse como complemento/refuerzo de este bloque.

== IDENTIDAD Y TONO ==
- Personalidad: amigable, proactivo, ágil, profesional, cercano.
- Hablas como persona real, nunca como un robot. Frases cortas y naturales.
- Máximo 1 emoji por mensaje (y solo si aporta calidez).

== ORTOGRAFÍA (REGLA CRÍTICA, NO NEGOCIABLE) ==
TODAS tus respuestas deben usar tildes correctamente en español. Ejemplos OBLIGATORIOS:
- ¿Cómo? ¿Qué? ¿Cuándo? ¿Cuánto? ¿Cuál? ¿Cuáles? ¿Dónde? ¿Quién?
- Cotización, información, atención, dirección, personalización, opción, cantidad, está, día, también, además, después, así, ahí, aquí, sé, té, sí, más.
- Tú (pronombre, con tilde). Tu (posesivo, sin tilde).
- Apertura de pregunta SIEMPRE con ¿ y cierre con ?  (Ejemplo: "¿Quieres con logotipo a uno o varios colores?").
- Apertura de exclamación SIEMPRE con ¡ y cierre con !  cuando aplique.
NUNCA escribas palabras sin tilde si la requieren. Nunca digas "que" cuando es "qué", "como" cuando es "cómo", "informacion" cuando es "información", etc. La ortografía perfecta es OBLIGATORIA en CADA mensaje.

== REGLAS DE FORMATO (OBLIGATORIAS) ==
1. UN SOLO MENSAJE por respuesta. Nunca envíes dos bloques separados.
2. Máximo 5 líneas por mensaje. Corto y directo.
3. Responde SOLO lo que el cliente preguntó. No agregues temas que no se pidieron.
4. NO anticipes pasos. Espera la respuesta del cliente antes de avanzar.
5. Si el cliente saluda con un simple "hola", respóndele amablemente tratándolo por su nombre (si lo conoces) y pregúntale en qué lo puedes ayudar. Ejemplo: "Hola [nombre], ¿en qué te puedo ayudar?". No vuelvas a saludar si ya lo hiciste.
6. Lee con atención lo que el cliente escribió antes de responder. Calidad sobre velocidad.

== ENTENDIMIENTO DEL CLIENTE ==
7. Si en el contexto ya hay datos del cliente (nombre, ciudad, dirección, email, identificación, cantidad, etc.), úsalos en silencio. NUNCA pidas un dato que ya está registrado.
8. Si el cliente dice "ya te lo di" o similar, discúlpate brevemente en una línea y continúa.
9. Si el cliente da datos por adelantado, guárdalos en extracted_data y continúa el flujo sin repetirlos.

== EXTRACCIÓN DE DATOS (técnica obligatoria del sistema) ==
SIEMPRE extrae TODOS los datos que el cliente proporcione, sin importar el paso. Guárdalos en extracted_data:
- nombre (nombre y apellido)
- empresa
- codigos_producto (lista acumulada separada por comas)
- cantidades_por_producto (formato "CODIGO:cantidad, CODIGO:cantidad")
- cantidad (cantidad general si aplica a todos)
- correo
- ciudad
- producto (genérico si no hay código)
- caracteristicas_logotipo (texto: "1 color", "2 colores", "varios colores", "sin logotipo", etc.)

Si el cliente pide QUITAR un código, devuelve la lista sin ese código. NUNCA repitas una recopilación de datos; solo extráelos en silencio y pregunta por lo que falte.

== CARACTERÍSTICAS DEL LOGOTIPO (REGLA OBLIGATORIA) ==
Cuando ya conoces el o los productos que el cliente desea (ya tienes codigos_producto o producto genérico definido), pregunta UNA SOLA VEZ:
"¿Quieres con logotipo a uno o varios colores?"
- Guarda la respuesta literal del cliente en extracted_data.caracteristicas_logotipo (ej. "1 color", "2 colores", "varios colores", "sin logotipo").
- NO repitas esta pregunta si ya está registrado el dato.
- Esta pregunta es OBLIGATORIA antes de pedir cualquier dato personal (correo, empresa, etc.).

REGLA ABSOLUTA — UNA SOLA PREGUNTA SOBRE PERSONALIZACIÓN:
La ÚNICA pregunta sobre personalización que el bot hace en TODA la conversación es "¿Quieres con logotipo a uno o varios colores?". Una vez recibida la respuesta (o si el cliente dice "sin logotipo"):
- PROHIBIDO preguntar por tipo de impresión, técnica de aplicación, método, ubicación del logo, tamaño del logo, posición, color del producto, color del logo (más allá de "uno o varios"), material, acabado, presentación o cualquier detalle adicional de personalización.
- PROHIBIDO mencionar palabras como: serigrafía, sublimación, bordado, grabado láser, UV, tampografía, vinil, transfer, foil, termofijado, full color, pad printing, hot stamping, ni siquiera para confirmar.
- Si el cliente menciona por su cuenta uno de estos términos, GUÁRDALO en extracted_data.caracteristicas_logotipo, agradécelo en una línea ("Perfecto, lo registramos") y NO preguntes nada más sobre personalización.
- Después del logo (uno/varios colores) y la cantidad, el siguiente paso SIEMPRE es pedir el correo (luego empresa) y cerrar cotización. Nada de personalización adicional.

== BÚSQUEDA DE INVENTARIO (catalog_search) — REGLAS ESTRICTAS ==
SOLO USA catalog_search cuando el cliente mencione EXPLÍCITAMENTE un TIPO de producto concreto (termos, gorras, tazas, esferos, mugs, mochilas, jarros, agendas, llaveros, libretas, cuadernos, bolígrafos, camisetas, polos, gorros, paraguas, morrales, lapiceros, tomatodos, y cualquier otro producto del catálogo). Debes reconocer cuándo el cliente está pidiendo un producto que necesita el catálogo y cuándo está hablando de otra cosa (cantidades, precios, datos personales) y NO necesita acceder al catálogo. Además, NO actives catalog_search cuando tu mensaje anterior era una pregunta abierta de seguimiento.

NUNCA pongas valor en catalog_search en estos casos (deja catalog_search=null):
- Cuando el cliente está RESPONDIENDO una pregunta tuya (ej. respuestas como "un color", "varios colores", "100", "1000", "1, 2", "primero 100 segundo 50", "sí", "no", "ok").
- Cuando el cliente envía cantidades (números) o códigos.
- Cuando el cliente da datos personales (nombre, email, empresa, ciudad).
- Cuando el cliente solo confirma o agradece.

Cuando SÍ corresponda usar catalog_search:
- Pon el término en catalog_search (ejemplo: "termos").
- El sistema te devolverá un link real. Formato EXACTO: https://cotizador.gimmicks.com.ec/catalog?q=producto (donde "producto" se reemplaza por el término que busca el cliente).
- Copia esa URL EXACTA en tu respuesta. PROHIBIDO escribir [LINK], [link], placeholders o URLs inventadas.
- Ejemplo de respuesta: "Claro, aquí tienes opciones: https://cotizador.gimmicks.com.ec/catalog?q=termos. Revísalos y me compartes los códigos que te interesan."
- NUNCA menciones códigos de productos si aún no enviaste el link del catálogo.

== REGLAS ANTI-ALUCINACIÓN (CRÍTICAS) ==
10. Solo responde con información que tengas explícitamente en este prompt o en el contexto. Si NO sabes algo con certeza, responde: "No tengo esa información por el momento. ¿Te puedo ayudar en algo más?"
11. NUNCA inventes precios, productos, colores, materiales, presentaciones, beneficios, ingredientes, tiempos de entrega ni características. Si el dato no está aquí, no existe.
12. NUNCA ofrezcas opciones inventadas. Si preguntas por cantidad y el cliente no la dio, pregunta abierto: "¿Cuántas unidades deseas?" SIN sugerir números como "1, 2 o 10". Si el cliente ya dijo una cantidad, úsala tal cual.
13. NUNCA envíes un link sin que el cliente haya mencionado un producto específico o tipo de artículo.
14. Si el cliente pregunta por un producto que NO encuentras en el catálogo del sistema: responde "Permíteme revisar a detalle" y marca needs_human=true.

== FLUJO COMERCIAL (lógica natural, sin anticipar) ==
15. NUNCA menciones formas de pago (transferencia, depósito, tarjeta, efectivo, etc.). Si el cliente pregunta por pagos, presupuestos o cantidades al por mayor: responde "En un momento te atendemos con el detalle" y marca needs_human=true.
16. NO pidas dirección, datos de facturación, identificación ni dirección de envío.
17. NUNCA pidas email con la excusa de "enviarte el catálogo completo". El link ya se envía en el chat cuando aplica.
18. NUNCA ofrezcas productos que no consten en el catálogo del sistema por iniciativa propia. Si no entiendes el requerimiento del cliente o te pregunta por algo que no está: marca needs_human=true.

== DERIVACIÓN A AGENTE HUMANO (needs_human=true) ==
Marca needs_human=true cuando:
- El cliente pregunta por un producto específico que no está en el catálogo.
- Pregunta por formas de pago, presupuestos a gran escala o precios especiales.
- Pide el catálogo completo / todos los productos (el sistema lo detecta automáticamente).
- No entiendes el requerimiento del cliente con certeza.
- El cliente muestra molestia o pide hablar con un humano.

Cuando marques needs_human=true, tu respuesta visible al cliente debe ser amable y breve: "Permíteme revisar eso y en un momento te atendemos." Sin mencionar que transfieres ni decir "voy a derivar la conversación".

== COTIZACIÓN (needs_quote=true) ==
La ÚNICA pregunta sobre características/personalización que el bot hace en TODA la conversación es la del logotipo (uno o varios colores, ya cubierta arriba). NO preguntes JAMÁS por tipo de personalización (serigrafía, bordado, UV, láser, sublimación, grabado, vinil, tampografía, transfer, etc.). Eso lo decide el agente humano después de la cotización inicial.

Marca needs_quote=true SOLO cuando tengas TODOS estos datos:
- códigos de producto + cantidades + correo + empresa
Los cuatro datos son obligatorios.

Cuando estén los cuatro datos, en una SOLA respuesta:
- Confirma con un mensaje de cierre EXACTO: "Gracias [nombre], tu cotización ha sido registrada y será enviada a [correo]. Nuestro equipo se pondrá en contacto contigo para los siguientes pasos."
- Marca needs_quote=true.
- NO sigas pidiendo más datos después de ese mensaje. Esa es la respuesta FINAL del bot en este flujo.
- NUNCA menciones al cliente el número de la cotización (ej. #4700); es dato interno.

Si el cliente cambia productos o cantidades después de una cotización existente, marca needs_quote=true de nuevo y envía un cierre adaptado a la NUEVA cotización (misma plantilla, reemplazando [nombre] y [correo]).

== TONO Y CIERRE ==
- Trata al cliente por su nombre cuando lo conozcas.
- No repitas información que ya diste.
- Si el cliente pierde interés, NO insistas. Puedes decir: "Quedo atento si necesitas algo más." o una variante breve equivalente.

== REGLA FINAL ==
Si en algún momento dudas, NO improvises. Es preferible decir "En un momento atiendo tu requerimiento" y marcar needs_human=true, antes que inventar.

== RECORDATORIO CRÍTICO DE TILDES (LO MÁS IMPORTANTE) ==
ANTES de enviar el JSON final, RELEE el campo "response" palabra por palabra y verifica que TODAS las palabras del español que requieren tilde la lleven. Lista de palabras frecuentes que SIEMPRE llevan tilde en este chat:
cómo, qué, cuándo, cuánto, cuántos, cuántas, cuál, cuáles, dónde, quién, por qué, está, están, estás, también, después, además, así, ahí, aquí, sí (afirmación), más, sólo, según, número, código, códigos, día, días, página, página, fácil, rápido, último, próximo, mínimo, máximo, físico, único, público, médico, técnico, eléctrico, atención, información, cotización, dirección, opción, personalización, producción, presentación, instrucción, situación, conversación, condición, decisión, función, sección, evolución, solución, relación, identificación, verificación, confirmación, generación, automático, característica, tú (pronombre), él (pronombre), mí (pronombre), té (bebida), sé (verbo saber), envíame, dígame, dirígete, podría, podrías, gustaría, debería, sería, haría, tendría.

Las preguntas SIEMPRE abren con ¿ y cierran con ?. Las exclamaciones con ¡ y !. Si tu campo "response" tiene aunque sea UNA palabra sin tilde donde corresponde, la respuesta entera será considerada inválida.

== FORMATO DE SALIDA (OBLIGATORIO) ==
Responde SIEMPRE en JSON válido, sin texto adicional fuera del JSON:
{
  "response": "tu mensaje corto (3-4 líneas máximo, un solo bloque, CON TILDES CORRECTAS)",
  "extracted_data": {},
  "catalog_search": null,
  "intent": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|pregunta_general|otra",
  "lead_quality": "tibio",
  "category": "cotizacion_directa|solicitud_catalogo|consulta_ideas|pedido_estacional|otra",
  "needs_quote": false,
  "needs_human": false,
  "conversation_summary": "resumen breve en 1-2 líneas"
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


# ===== Spanish accent safety net =====
# Maps common UNAMBIGUOUS words missing accents to their correct form.
# Only includes words that ALWAYS carry an accent regardless of context.
# Ambiguous words (esta/está, como/cómo, que/qué, mas/más, si/sí, tu/tú, el/él,
# se/sé, te/té, mi/mí) are NOT included to avoid false positives.
_ACCENT_FIXES = {
    # Common adverbs / conjunctions always with tilde
    "tambien": "también", "despues": "después", "ademas": "además",
    "asi": "así", "ahi": "ahí", "aqui": "aquí", "alli": "allí",
    "estan": "están",  # only plural form is unambiguous
    "facil": "fácil", "faciles": "fáciles",
    "rapido": "rápido", "rapida": "rápida",
    "rapidos": "rápidos", "rapidas": "rápidas",
    "ultimo": "último", "ultima": "última",
    "ultimos": "últimos", "ultimas": "últimas",
    "proximo": "próximo", "proxima": "próxima",
    "proximos": "próximos", "proximas": "próximas",
    "minimo": "mínimo", "maximo": "máximo",
    "minima": "mínima", "maxima": "máxima",
    "fisico": "físico", "fisica": "física",
    "unico": "único", "unica": "única",
    "unicos": "únicos", "unicas": "únicas",
    "publico": "público", "publica": "pública",
    "tecnico": "técnico", "tecnica": "técnica",
    "electrico": "eléctrico", "electrica": "eléctrica",
    "electronico": "electrónico", "electronica": "electrónica",
    # -ción words (always with tilde)
    "atencion": "atención", "informacion": "información", "cotizacion": "cotización",
    "direccion": "dirección", "opcion": "opción", "situacion": "situación",
    "condicion": "condición", "decision": "decisión", "funcion": "función",
    "seccion": "sección", "presentacion": "presentación", "conversacion": "conversación",
    "instruccion": "instrucción", "identificacion": "identificación",
    "verificacion": "verificación", "confirmacion": "confirmación",
    "generacion": "generación", "personalizacion": "personalización",
    "produccion": "producción", "solucion": "solución", "relacion": "relación",
    "evolucion": "evolución", "comunicacion": "comunicación",
    "promocion": "promoción", "seleccion": "selección",
    "descripcion": "descripción", "instalacion": "instalación",
    "exportacion": "exportación", "importacion": "importación",
    "facturacion": "facturación", "fabricacion": "fabricación",
    # Common nouns and verbs in chat (unambiguous)
    "codigo": "código", "codigos": "códigos",
    "numero": "número", "numeros": "números",
    "dia": "día", "dias": "días",
    "pagina": "página", "paginas": "páginas",
    "telefono": "teléfono", "telefonos": "teléfonos",
    "envianos": "envíanos", "enviame": "envíame", "envielo": "envíelo",
    "digame": "dígame", "dirigete": "dirígete",
    "podria": "podría", "podrias": "podrías",
    "podriamos": "podríamos", "podrian": "podrían",
    "gustaria": "gustaría", "deberia": "debería", "seria": "sería",
    "haria": "haría", "tendria": "tendría", "vendria": "vendría",
    "automatico": "automático", "automatica": "automática",
    "caracteristica": "característica", "caracteristicas": "características",
    "metodo": "método", "metodos": "métodos",
    "compania": "compañía", "companias": "compañías",
}

# Pre-build replacement regex patterns once (case-insensitive whole-word)
_ACCENT_PATTERNS = [
    (re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v)
    for k, v in _ACCENT_FIXES.items()
]

# Interrogative words that only carry tilde inside question marks ¿ ?
_INTERROGATIVE_FIXES = {
    "como": "cómo", "que": "qué",
    "cuando": "cuándo", "cuanto": "cuánto",
    "cuantos": "cuántos", "cuantas": "cuántas",
    "cual": "cuál", "cuales": "cuáles",
    "donde": "dónde", "adonde": "adónde",
    "quien": "quién", "quienes": "quiénes",
    "porque": "por qué",  # only inside ¿?
}

_INTERROGATIVE_PATTERNS = [
    (re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v)
    for k, v in _INTERROGATIVE_FIXES.items()
]


def _preserve_case(original: str, replacement: str) -> str:
    """Preserve the casing pattern of original when applying replacement."""
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def _fix_in_questions(text: str) -> str:
    """Apply interrogative-word fixes only inside ¿ ... ? segments."""
    def fix_segment(match: re.Match) -> str:
        segment = match.group(0)
        for pattern, replacement in _INTERROGATIVE_PATTERNS:
            segment = pattern.sub(
                lambda m: _preserve_case(m.group(0), replacement), segment
            )
        return segment

    # Match content between ¿ and the next ? (greedy minimal)
    return re.sub(r'¿[^?]*\?', fix_segment, text)


def fix_spanish_accents(text: str) -> str:
    """Safety net: ensure common unambiguous Spanish words carry the correct accent.
    Preserves URLs (URLs are skipped because the regex \\b doesn't break in them).
    Interrogative words only get tildes inside ¿...? blocks."""
    if not text:
        return text
    result = text
    # Apply unambiguous fixes everywhere
    for pattern, replacement in _ACCENT_PATTERNS:
        result = pattern.sub(
            lambda m: _preserve_case(m.group(0), replacement), result
        )
    # Apply interrogative fixes only inside questions
    result = _fix_in_questions(result)
    return result


# ===== Forbidden personalization terms safety net =====
# After the bot asks "¿logo a uno o varios colores?" it must NEVER ask about
# any other type of personalization. If the LLM disobeys, this safety net
# strips the offending sentence and substitutes a safe follow-up.
_FORBIDDEN_PERSONALIZATION_REGEX = re.compile(
    r"\b("
    r"serigraf[íi]a|sublimaci[óo]n|bordad[oa]s?|grabad[oa]s?|"
    r"tampograf[íi]a|pad\s*printing|hot\s*stamping|"
    r"vinil(?:o|os)?|transfer|termofijad[oa]s?|"
    r"l[áa]ser|impresi[óo]n\s+uv|uv\s+printing|full\s*color|"
    r"tipo\s+de\s+personalizaci[óo]n|tipo\s+de\s+impresi[óo]n|"
    r"m[ée]todo\s+de\s+impresi[óo]n|t[ée]cnica\s+de\s+impresi[óo]n|"
    r"t[ée]cnica\s+de\s+personalizaci[óo]n|t[ée]cnica\s+de\s+aplicaci[óo]n"
    r")\b",
    re.IGNORECASE,
)


def strip_forbidden_personalization(text: str, missing_fields: Optional[List[str]] = None) -> str:
    """Remove sentences that mention forbidden personalization techniques.
    URLs are preserved as-is (forbidden terms inside URL query strings are ignored).
    If the entire response was about that, replace with a safe follow-up
    based on what's still missing (correo, empresa, cantidad)."""
    if not text:
        return text

    # Mask URLs so the regex doesn't match query strings like ?q=bordado
    url_re = re.compile(r'https?://\S+')
    urls: List[str] = []

    def _mask(match: re.Match) -> str:
        urls.append(match.group(0))
        return f"___URL_{len(urls) - 1}___"

    masked = url_re.sub(_mask, text)

    if not _FORBIDDEN_PERSONALIZATION_REGEX.search(masked):
        return text  # nothing forbidden in actual prose

    # Split into sentences keeping delimiters; drop any sentence with a forbidden term
    parts = re.split(r'([.!?\n]+)', masked)
    cleaned_parts: List[str] = []
    for i in range(0, len(parts), 2):
        sentence = parts[i]
        delimiter = parts[i + 1] if i + 1 < len(parts) else ""
        if not _FORBIDDEN_PERSONALIZATION_REGEX.search(sentence):
            cleaned_parts.append(sentence + delimiter)
    cleaned = "".join(cleaned_parts).strip()
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

    # Restore URL placeholders
    for idx, url in enumerate(urls):
        cleaned = cleaned.replace(f"___URL_{idx}___", url)

    # If we removed everything (or almost), substitute a safe follow-up
    if len(cleaned) < 10:
        missing = missing_fields or []
        if "correo" in missing:
            cleaned = "Para continuar con tu cotización, ¿me compartes tu correo electrónico?"
        elif "empresa" in missing:
            cleaned = "Para finalizar tu cotización, ¿cuál es el nombre de tu empresa?"
        elif "cantidad" in missing or "cantidades_por_producto" in missing:
            cleaned = "Para continuar, ¿cuántas unidades necesitas?"
        else:
            cleaned = "Perfecto, registramos tu requerimiento. Un asesor te contactará en breve."

    logger.info(f"Stripped forbidden personalization terms from response. Original len={len(text)}, cleaned len={len(cleaned)}")
    return cleaned


async def search_products_by_keyword(db: AsyncIOMotorDatabase, keyword: str, limit: int = 8) -> List[Dict]:
    """Search products by keyword in name, description, or categories."""
    if not keyword:
        return []
    STOPWORDS = {
        "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
        "para", "por", "con", "sin", "que", "como", "pero", "mas", "muy",
        "ese", "esa", "esos", "esas", "este", "esta", "estos", "estas",
        "al", "en", "es", "son", "ser", "hay", "ya", "yo", "tu", "su",
        "tus", "sus", "nuestro", "nuestra", "nuestros", "nuestras",
        "me", "te", "se", "le", "lo", "mi", "nos", "les", "hola", "buenas",
        "necesito", "quiero", "busco", "tengo", "puede", "puedo", "favor",
        # Generic terms that match too many products if used as keywords
        "producto", "productos", "articulo", "articulos", "item", "items",
        "catalogo", "catalogos", "opciones", "opcion", "lista", "listado",
        "todo", "todos", "toda", "todas", "ver", "mostrar", "muestrame",
        "envia", "envie", "enviar", "muestra", "ofrecen", "ofreces",
        "tienen", "tienes", "vende", "venden", "vendes",
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

    models = [("openai", "gpt-4o"), ("openai", "gpt-5.2")]
    for provider, model_name in models:
        try:
            session_id = f"gimmicks-{uuid.uuid4().hex[:12]}"
            chat = LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg)
            chat.with_model(provider, model_name)
            # Hard timeout so a hung LLM request never silently kills a reply
            response_text = await asyncio.wait_for(
                chat.send_message(UserMessage(text=user_msg)),
                timeout=25.0,
            )

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

    # Logotipo characteristic — applied to every item in the quote
    caracteristicas_logo = (collected_data.get("caracteristicas_logotipo") or "").strip()
    item_characteristics: List[str] = []
    if caracteristicas_logo:
        low = caracteristicas_logo.lower()
        if "sin" in low and "logo" in low:
            label = "Sin logotipo"
        elif any(k in low for k in ["varios", "muchos", "multi", "varias"]):
            label = "Logotipo a varios colores"
        elif any(d in low for d in ["1 color", "un color", "monocrom", "uno"]):
            label = "Logotipo a 1 color"
        else:
            label = f"Logotipo: {caracteristicas_logo}"
        item_characteristics = [label]

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
                "selected_characteristics": list(item_characteristics),
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
                "selected_characteristics": list(item_characteristics),
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

# Human agent that takes over conversations when:
#   - Customer asks for full catalog / all products
#   - A new quote is created or an existing one is modified
HUMAN_AGENT_PHONE = "593999440910"

# Patterns that indicate the customer wants the FULL catalog (handed off to agent)
FULL_CATALOG_PATTERNS = [
    'catalogo completo', 'catálogo completo',
    'catalogo entero', 'catálogo entero',
    'catalogo total', 'catálogo total',
    'todo el catalogo', 'todo el catálogo',
    'todo el inventario', 'todos sus productos',
    'todos tus productos', 'todos los productos',
    'lista completa', 'lista entera',
    'inventario completo', 'inventario entero',
    'mostrar todo', 'ver todo el',
    'envia el catalogo', 'envíame el catálogo',
    'enviame el catalogo', 'mandame el catalogo', 'mándame el catálogo',
    'todo lo que tienen', 'todo lo que ofrecen', 'todo lo que venden',
]


def detect_full_catalog_request(message_text: str) -> bool:
    """Return True if the customer is asking for the full catalog / all products."""
    msg = (message_text or "").lower().strip()
    if not msg:
        return False
    for pattern in FULL_CATALOG_PATTERNS:
        if pattern in msg:
            return True
    return False


async def _send_to_human_agent(notification_text: str, template_params: list, db: AsyncIOMotorDatabase):
    """Send a notification to the human agent (HUMAN_AGENT_PHONE).

    Tries a normal text message first; if Meta refuses due to the 24h
    re-engagement window, falls back to a Meta-approved template.

    template_params is a list of strings used to fill the template variables
    (in order) when the fallback is needed.
    """
    from server import send_whatsapp_message, send_whatsapp_template
    try:
        await send_whatsapp_message(HUMAN_AGENT_PHONE, notification_text)
        logger.info(f"Human agent notified (text): {HUMAN_AGENT_PHONE}")
        return True
    except Exception as send_err:
        error_str = str(send_err).lower()
        if "131047" in error_str or "131026" in error_str or "24 hour" in error_str or "re-engagement" in error_str:
            logger.info(f"24h window expired for agent {HUMAN_AGENT_PHONE}, using template fallback")
            try:
                await send_whatsapp_template(
                    HUMAN_AGENT_PHONE,
                    "alerta_agente_humano",
                    "es",
                    template_params,
                )
                logger.info(f"Human agent notified (template): {HUMAN_AGENT_PHONE}")
                return True
            except Exception as tmpl_err:
                logger.error(f"Template send to agent failed: {tmpl_err}")
                return False
        logger.error(f"Failed to notify human agent: {send_err}")
        return False


async def notify_agent_full_catalog(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict):
    """Notify the human agent that a customer wants the full catalog."""
    client_name = (collected_data or {}).get("nombre", "Cliente sin nombre")
    notification = (
        f"CLIENTE PIDIO CATALOGO COMPLETO\n\n"
        f"Cliente: {client_name}\n"
        f"Telefono: {phone_number}\n\n"
        f"Enviar catalogo completo manualmente. Conversacion en CRM."
    )
    await _send_to_human_agent(
        notification,
        [
            "Cliente pidio catalogo completo",
            f"{client_name} ({phone_number})",
            "Enviar catalogo completo manualmente",
        ],
        db,
    )


async def notify_agent_quote_event(db: AsyncIOMotorDatabase, phone_number: str, collected_data: Dict, is_update: bool, quote_number: str = ""):
    """Notify the human agent when a quote is created or modified."""
    action = "COTIZACION ACTUALIZADA" if is_update else "NUEVA COTIZACION"
    client_name = (collected_data or {}).get("nombre", "Cliente sin nombre")
    empresa = (collected_data or {}).get("empresa", "")
    correo = (collected_data or {}).get("correo", "")
    detalle_lines = []
    if quote_number:
        detalle_lines.append(f"Numero: {quote_number}")
    if empresa:
        detalle_lines.append(f"Empresa: {empresa}")
    if correo:
        detalle_lines.append(f"Email: {correo}")
    detalle = " | ".join(detalle_lines) if detalle_lines else "Revisar en CRM"

    notification = (
        f"{action}\n\n"
        f"Cliente: {client_name}\n"
        f"Telefono: {phone_number}\n"
        f"{detalle}\n\n"
        f"Revisar y atender en CRM."
    )
    await _send_to_human_agent(
        notification,
        [
            action,
            f"{client_name} ({phone_number})",
            detalle,
        ],
        db,
    )


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
    """Send immediate WhatsApp alert to staff when product search returns no results.
    Falls back to template message if 24h window has expired."""
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
        
        try:
            await send_message_fn(STAFF_NOTIFICATION_PHONE, staff_conv_id, notification)
        except Exception as send_err:
            # If regular message fails (24h window), try template
            error_str = str(send_err).lower()
            if "131047" in error_str or "131026" in error_str or "24 hour" in error_str or "re-engagement" in error_str:
                logger.info(f"24h window expired for staff {STAFF_NOTIFICATION_PHONE}, using template")
                from server import send_whatsapp_template
                await send_whatsapp_template(
                    STAFF_NOTIFICATION_PHONE,
                    "alerta_producto_no_encontrado",
                    "es",
                    [client_name, phone_number, product_request]
                )
            else:
                raise
        
        logger.info(f"Staff notified about missing product for {phone_number}")
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

    # Detect vague queries that mention "product" generically without naming a specific type
    VAGUE_PATTERNS = [
        'un producto', 'producto que', 'productos que', 'algo que',
        'vi en', 'fanpage', 'facebook', 'instagram', 'redes sociales',
        'publicacion', 'publicidad', 'anuncio', 'post',
        'quiero saber si tienen', 'tienen algo', 'que productos tienen',
        'que opciones', 'que hay', 'que tienen disponible',
        # Generic catalog/products requests without specifying a type
        'sus productos', 'tus productos', 'los productos', 'todos los productos',
        'ver productos', 'mostrar productos', 'ver opciones', 'ver todo',
        'su catalogo', 'tu catalogo', 'el catalogo', 'mi catalogo',
        'que tienen', 'que vende', 'que venden', 'que ofrecen',
        'que ofreces', 'que ofrece', 'todo lo que tienen',
        'ver lo que tienen', 'mostrar todo', 'ver el catalogo',
    ]
    is_vague_query = any(p in msg_lower for p in VAGUE_PATTERNS) and not any(
        kw in msg_lower for kw in [
            'jarro', 'termo', 'gorra', 'esfero', 'boligrafo', 'taza', 'mug',
            'camiseta', 'camisa', 'mochila', 'bolso', 'libreta', 'agenda',
            'llavero', 'tomatodo', 'botella', 'vaso', 'copa', 'plato',
            'parlante', 'audifono', 'usb', 'power bank', 'cargador',
            'mouse pad', 'mousepad', 'delantal', 'paraguas', 'sombrilla',
        ]
    )

    no_products_found = False
    catalog_link = ""

    # Product keywords that indicate the customer is asking about a product type.
    # If any of these appear in the message we MUST run the catalog search even
    # if the previous bot message ended with "?".
    PRODUCT_KEYWORDS = {
        'jarro', 'jarros', 'termo', 'termos', 'gorra', 'gorras',
        'esfero', 'esferos', 'boligrafo', 'boligrafos', 'lapicero', 'lapiceros',
        'taza', 'tazas', 'mug', 'mugs', 'camiseta', 'camisetas', 'camisa', 'camisas',
        'polo', 'polos', 'chaqueta', 'chaquetas', 'gorro', 'gorros', 'visera', 'viseras',
        'mochila', 'mochilas', 'bolso', 'bolsos', 'maleta', 'maletas',
        'libreta', 'libretas', 'agenda', 'agendas',
        'cuaderno', 'cuadernos', 'cartuchera', 'cartucheras',
        'llavero', 'llaveros', 'tomatodo', 'tomatodos', 'botella', 'botellas',
        'vaso', 'vasos', 'copa', 'copas', 'plato', 'platos',
        'parlante', 'parlantes', 'audifono', 'audifonos', 'auricular', 'auriculares',
        'usb', 'usbs', 'powerbank', 'cargador', 'cargadores',
        'mousepad', 'delantal', 'delantales', 'paraguas', 'sombrilla', 'sombrillas',
        'gafas', 'lentes', 'reloj', 'relojes', 'pulsera', 'pulseras',
        'memoria', 'memorias',
    }
    msg_lower_words = {w.strip(",.;:!?¿¡()\"'") for w in msg_lower.split()}
    msg_lower_words.discard("")
    has_product_keyword = bool(msg_lower_words & PRODUCT_KEYWORDS)

    # Detect if the user is REPLYING to a previous bot question (e.g. "un color",
    # "serigrafia", "100", "200 primero 50 segundo"). In that case, do NOT run
    # the inventory search — those answers are not product searches.
    is_answer_to_question = False
    try:
        last_bot_msg = await db.messages.find_one(
            {"conversation_id": conversation_id, "sender": {"$in": ["bot", "business"]}},
            {"_id": 0, "content": 1},
            sort=[("timestamp", -1)],
        )
        last_bot_text = ""
        if last_bot_msg:
            c = last_bot_msg.get("content")
            last_bot_text = (c.get("text", "") if isinstance(c, dict) else str(c or "")).strip()
        # Only treat short messages as "answers" when they don't mention a
        # product keyword. Otherwise messages like "quiero cuadernos" after the
        # bot greeting were being skipped, and the catalog link never sent.
        if (
            last_bot_text
            and "?" in last_bot_text
            and len(message_text.strip().split()) <= 6
            and not has_product_keyword
        ):
            is_answer_to_question = True
    except Exception:
        pass

    # Common short-answer markers that should never trigger a catalog search
    SHORT_ANSWER_TOKENS = {
        "si", "sí", "no", "ok", "okay", "vale", "perfecto", "claro",
        "uno", "dos", "tres", "varios", "varias", "muchos", "todos",
        "color", "colores", "1", "2", "3", "4", "5",
        "serigrafia", "serigrafía", "bordado", "uv", "laser", "láser",
        "sublimacion", "sublimación", "grabado",
    }
    msg_tokens = set(t.lower().strip(",.;:!?¿¡") for t in message_text.split())
    if msg_tokens and msg_tokens.issubset(SHORT_ANSWER_TOKENS) and not has_product_keyword:
        is_answer_to_question = True

    should_search = (
        not is_data_input
        and not has_code_pattern
        and not is_greeting
        and not is_vague_query
        and not is_answer_to_question
    )
    # Hard guarantee: if the message contains a product keyword (e.g. "tienen jarros?"),
    # we ALWAYS run the catalog search. Other heuristics must never block it.
    if has_product_keyword and not is_data_input and not has_code_pattern:
        should_search = True

    if should_search:
        products_found = await search_products_by_keyword(db, message_text.strip(), limit=8)

        # ALWAYS build the catalog link when we run a search, even if the DB
        # returned 0 hits. Otherwise the bot ends up sending a message with the
        # URL stripped out (because the regex below removes URLs when
        # catalog_link is empty), and the customer never receives a link.
        base_url = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
        if not base_url:
            base_url = os.environ.get("CATALOG_BASE_URL", "").rstrip("/")
        if not base_url:
            try:
                fe_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", ".env")
                with open(fe_env) as f:
                    for line in f:
                        if line.startswith("REACT_APP_BACKEND_URL="):
                            base_url = line.split("=", 1)[1].strip().rstrip("/")
                            break
            except Exception:
                pass
        # Final fallback: hardcoded production domain so the catalog link is
        # NEVER empty (otherwise the URL the AI drafts gets stripped and the
        # customer receives a message with the URL missing).
        if not base_url:
            base_url = "https://cotizador.gimmicks.com.ec"
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
            # Generic terms that should not become a literal catalog filter
            "sus", "tus", "su", "tu", "nuestro", "nuestra",
            "producto", "productos", "articulo", "articulos",
            "catalogo", "catalogos", "lista", "listado",
            "todo", "todos", "toda", "todas", "mostrar", "muestrame",
            "ofrecen", "ofreces", "vende", "venden", "vendes",
        }
        clean_terms = [
            w.strip(",.;:!?¿¡()\"'")
            for w in message_text.strip().split()
        ]
        clean_terms = [w for w in clean_terms if w.lower() not in LINK_STOPWORDS and len(w) > 2]
        search_term = " ".join(clean_terms) if clean_terms else message_text.strip()
        catalog_link = f"{base_url}/catalog?q={url_quote(search_term)}" if base_url else ""

        if products_found:
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
            if catalog_link:
                # Even when the DB has no exact match, send the general catalog
                # link so the customer can browse manually. Do NOT promise a
                # human will send the catalog later — the link IS the catalog.
                catalog_availability = (
                    "SIN COINCIDENCIA EXACTA EN INVENTARIO, PERO EL CLIENTE PUEDE REVISAR EL CATALOGO COMPLETO.\n"
                    f"LINK DEL CATALOGO (OBLIGATORIO ENVIAR): {catalog_link}\n"
                    "INSTRUCCION: Es OBLIGATORIO incluir este link EXACTO en tu respuesta. "
                    f"Ejemplo: 'Aqui tienes nuestro catalogo para que revises las opciones: {catalog_link}. "
                    "Si encuentras algo de tu interes, comparteme los codigos.'. "
                    "PROHIBIDO decir 'un agente te enviara el catalogo'. PROHIBIDO decir 'no tenemos'. "
                    "Un asesor sera notificado en paralelo para apoyar."
                )
            else:
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

        # NOTE: webhook duplicate-delivery dedup is handled upstream via
        # whatsapp_message_id (process_incoming_message). The previous 8-second
        # bot-cooldown was dropping legitimate fast follow-up messages from real
        # users, so it has been removed. Each incoming user message gets a reply.

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

        # If transferred to human, reactivate when client sends a new message
        # (client is initiating a new conversation)
        if state.get("transferred_to_human"):
            transfer_reason = state.get("transfer_reason", "unknown")
            logger.info(
                f"Reactivating transferred conversation for {phone_number} "
                f"(was transferred for: {transfer_reason})"
            )
            state["transferred_to_human"] = False
            state["transfer_timestamp"] = None
            state["transfer_reason"] = None
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "transferred_to_human": False,
                    "transfer_timestamp": None,
                    "transfer_reason": None,
                }}
            )

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

        # ===== FULL CATALOG REQUEST → IMMEDIATE HANDOFF TO HUMAN AGENT =====
        # If the customer asks for the entire catalog, the bot acknowledges
        # politely and silently transfers the conversation to the human agent.
        if detect_full_catalog_request(message_text) and not state.get("transferred_to_human"):
            nombre = collected_data.get("nombre", "")
            saludo = f"{nombre}, l" if nombre else "L"
            ack_msg = (
                f"{saludo}isto. En un momento te envío lo solicitado."
            )
            await send_message_fn(phone_number, conversation_id, ack_msg, needs_review=True)
            message_sent = True
            try:
                await notify_agent_full_catalog(db, phone_number, collected_data)
            except Exception as e:
                logger.error(f"notify_agent_full_catalog failed: {e}")
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "transferred_to_human": True,
                    "transfer_reason": "catalogo_completo",
                    "transfer_timestamp": now.isoformat(),
                    "message_count": msg_count,
                    "last_interaction": now.isoformat(),
                }}
            )
            await update_lead_from_ai(db, phone_number, collected_data, "tibio", "catalogo", "cliente_potencial")
            return

        # ===== PRE-AI ESCALATION DETECTION =====
        escalation_reason = detect_escalation(message_text)
        if escalation_reason:
            if not state.get("transferred_to_human"):
                nombre = collected_data.get("nombre", "")
                saludo = f"{nombre}, e" if nombre else "E"

                escalation_msg = (
                    f"{saludo}ntendido, no te hago más preguntas. "
                    f"Dejo tu solicitud lista para revisión por un asesor. "
                    f"Te contactamos enseguida."
                )
                await send_message_fn(phone_number, conversation_id, escalation_msg, needs_review=True)
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

        # ===== LOAD AUTOMATION RULES FROM DATABASE =====
        # OBJETIVO_GENERAL_BOT is treated specially: if present, it's injected FIRST
        # at the very top of the context with maximum priority (first source of intent).
        automation_rules_text = ""
        objetivo_general_text = ""
        try:
            active_rules = await db.automation_rules.find(
                {"is_active": True}, {"_id": 0, "name": 1, "action_value": 1, "trigger_type": 1}
            ).to_list(50)
            if active_rules:
                rules_lines = []
                for rule in active_rules:
                    # Extract OBJETIVO_GENERAL_BOT separately and inject it at the top.
                    rule_name = str(rule.get("name") or "").strip()
                    if rule_name.upper() == "OBJETIVO_GENERAL_BOT":
                        objetivo_general_text = (
                            "=== OBJETIVO GENERAL DEL BOT (PRIORIDAD MÁXIMA - PRIMERA FUENTE DE INTENCIÓN) ===\n"
                            "Esta directriz fue configurada por el administrador en el panel y tiene "
                            "PRIORIDAD sobre cualquier otra regla o instrucción. Cada decisión conversacional "
                            "del bot debe alinearse con este objetivo:\n"
                            f"{rule['action_value']}\n\n"
                        )
                        continue
                    rules_lines.append(f"- {rule['name']}: {rule['action_value']}")
                if rules_lines:
                    automation_rules_text = "=== REGLAS DE AUTOMATIZACION DEL SISTEMA (OBLIGATORIAS - PRIORIDAD MAXIMA) ===\nEstas reglas fueron configuradas por el administrador y tienen PRIORIDAD sobre cualquier otra instruccion. DEBES seguirlas al pie de la letra, sin excepciones:\n" + "\n".join(rules_lines)
        except Exception as e:
            logger.warning(f"Could not load automation rules: {e}")

        # ===== BUILD USER PROMPT (new template) =====
        user_prompt = f"""{objetivo_general_text}INSTRUCCIÓN: Revisa TODO el historial y los datos recopilados. NO pidas nada que ya se haya proporcionado. Haz UNA sola pregunta por mensaje. Tu respuesta debe ser UN solo mensaje coherente.
IMPORTANTE: En extracted_data.codigos_producto siempre devuelve la lista COMPLETA ACUMULADA de códigos (no solo los nuevos).
Si el sistema te proporciona un LINK DEL CATÁLOGO (URL real con https://), es OBLIGATORIO copiar esa URL EXACTA en tu respuesta. PROHIBIDO escribir [LINK] o [link] o cualquier placeholder. Usa la URL completa.
NUNCA menciones códigos de productos si no has incluido el link del catálogo en tu respuesta. Los códigos solo se presentan junto con o después del link.
NUNCA digas "un agente te enviará el catálogo" si el sistema ENCONTRÓ productos. La frase "agente enviará catálogo" SOLO se usa cuando el sistema dice "SIN RESULTADOS EN INVENTARIO".
Si el cliente saluda, responde SOLO con un saludo y "¿en qué puedo ayudarte hoy?". NO pidas códigos, NO menciones cotizaciones pendientes.
PROHIBIDO repetir o parafrasear tu mensaje anterior. Si ya confirmaste algo, avanza directamente al siguiente paso.
PROHIBIDO pedir el nombre si ya lo tienes en los datos recopilados. Dirígete al cliente por su nombre.
Pide UN SOLO dato por mensaje. No combines preguntas.
Lee siempre el historial completo. Si el cliente ya había conversado antes, retoma desde donde quedó.

REGLA DE ORTOGRAFÍA (NO NEGOCIABLE): Tu respuesta DEBE usar tildes correctas en español. Palabras como "cómo", "qué", "está", "también", "después", "información", "cotización", "atención", "más", "sí", "tú", "él", "días", "fácil", "rápido", "por qué", "aquí", "ahí", "así" SIEMPRE llevan tilde cuando corresponde. Las preguntas se abren con ¿ y se cierran con ?. NO escribas en mayúsculas sin tildes ni omitas tildes en ningún caso. Si tu respuesta tiene una sola palabra mal escrita o sin tilde, será rechazada.

{catalog_info}
{catalog_availability}
{quote_context}

{automation_rules_text}

=== HISTORIAL COMPLETO DE LA CONVERSACIÓN ===
{history_text}

=== DATOS YA RECOPILADOS (PROHIBIDO volver a pedir estos) ===
{collected_summary if collected_summary else "Ninguno aún"}

=== DATOS QUE AÚN FALTAN ===
{missing_fields}

{next_to_ask}

MENSAJE ACTUAL DEL CLIENTE: {message_text}"""

        # ===== CALL AI =====
        ai_result = await call_llm(SYSTEM_PROMPT, user_prompt, phone_number)

        if ai_result is None:
            if msg_count <= 1:
                fallback = "Hola, soy Ana de Gimmicks Marketing Services. ¿En qué puedo ayudarte?"
            else:
                fallback = "Disculpa, tuve un problema. ¿Podrías repetir tu mensaje?"
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
            # Replace [LINK] / [link] / (link) placeholders with actual catalog URL
            if response_text and catalog_link:
                response_text = re.sub(r'\[LINK\]|\[link\]|\[Link\]|\(LINK\)|\(link\)|\{LINK\}|\{link\}', catalog_link, response_text)

            # Remove any external/invented URLs (keep only our catalog link).
            # If catalog_link is empty (rare edge case), only strip URLs that
            # are clearly NOT pointing to our domain — preserve any *.gimmicks.com.ec
            # link the AI drafted as a last-resort safety net.
            if response_text:
                if catalog_link:
                    # Temporarily replace our link to preserve it
                    placeholder = "___CATALOG_LINK___"
                    response_text = response_text.replace(catalog_link, placeholder)
                    response_text = re.sub(r'https?://\S+', '', response_text)
                    response_text = response_text.replace(placeholder, catalog_link)
                else:
                    # Strip URLs except those pointing to gimmicks.com.ec
                    response_text = re.sub(
                        r'https?://(?!\S*gimmicks\.com\.ec)\S+', '', response_text
                    )
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

            # Strip any forbidden personalization terms the LLM may have leaked
            still_missing = []
            if not collected_data.get("correo"):
                still_missing.append("correo")
            if not collected_data.get("empresa"):
                still_missing.append("empresa")
            if not (collected_data.get("cantidades_por_producto") or collected_data.get("cantidad")):
                still_missing.append("cantidad")
            response_text = strip_forbidden_personalization(response_text, still_missing)

            await send_message_fn(phone_number, conversation_id, fix_spanish_accents(response_text), needs_review=needs_human)
            message_sent = True

        # ===== GENERATE QUOTE IF READY =====
        if will_generate_quote:
            existing_quote = await db.quotes_v2.find_one(
                {"phone_number": phone_number, "status": "pending", "is_deleted": False},
                {"_id": 0, "items": 1, "client_name": 1, "quote_number": 1}
            )
            await upsert_quote(db, phone_number, collected_data, conversation_id)
            state_quote = True

            await notify_staff_new_quote(db, phone_number, collected_data, existing_quote is not None, send_message_fn)
            # Also notify the human agent so they can take over
            try:
                await notify_agent_quote_event(
                    db, phone_number, collected_data,
                    is_update=existing_quote is not None,
                    quote_number=(existing_quote or {}).get("quote_number", ""),
                )
            except Exception as e:
                logger.error(f"notify_agent_quote_event failed: {e}")
            # Hand off the conversation to the human agent for follow-up
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "transferred_to_human": True,
                    "transfer_reason": "cotizacion_generada",
                    "transfer_timestamp": now.isoformat(),
                }}
            )

            correo = collected_data.get("correo", "tu correo")
            nombre = collected_data.get("nombre", "")
            confirm_msg = (
                f"Gracias{' ' + nombre if nombre else ''}, tu cotización ha sido registrada "
                f"y será enviada a {correo}. Nuestro equipo se pondrá en contacto contigo para los siguientes pasos."
            )
            await send_message_fn(phone_number, conversation_id, confirm_msg, needs_review=True)
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
            await send_escalation_summary(db, phone_number, collected_data, "El bot detectó que se necesita revisión humana", send_message_fn)
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
