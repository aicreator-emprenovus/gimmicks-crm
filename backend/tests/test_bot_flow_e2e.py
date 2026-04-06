"""
E2E test for the WhatsApp bot conversation flow.
Simulates a full customer journey: greeting -> name -> products -> codes -> quantities -> data -> quote
"""
import asyncio
import time
from pymongo import MongoClient
import requests
import json

API_URL = "https://catalog-pdf-fix.preview.emergentagent.com"
TEST_PHONE = "593999888777"

client = MongoClient("mongodb://localhost:27017")
db = client["gimmicks_crm"]


def clean_test_data():
    db.conversation_states.delete_many({"phone_number": TEST_PHONE})
    db.conversations.delete_many({"phone_number": TEST_PHONE})
    db.messages.delete_many({"phone_number": TEST_PHONE})
    db.leads.delete_many({"phone_number": TEST_PHONE})
    db.quotes_v2.delete_many({"phone_number": TEST_PHONE})
    db.clients.delete_many({"phone": TEST_PHONE})
    print("=== Test data cleaned ===\n")


def send_message(text):
    """Simulate a WhatsApp webhook message"""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "test",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "test"},
                    "messages": [{
                        "from": TEST_PHONE,
                        "id": f"test_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": text}
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    resp = requests.post(f"{API_URL}/api/webhook/whatsapp", json=payload)
    return resp.status_code


def get_bot_responses(since_count=0):
    """Get bot messages from DB"""
    conv = db.conversations.find_one({"phone_number": TEST_PHONE}, {"_id": 0, "id": 1})
    if not conv:
        return []
    msgs = list(db.messages.find(
        {"conversation_id": conv["id"], "sender": {"$in": ["business", "bot"]}},
        {"_id": 0, "content": 1, "timestamp": 1}
    ).sort("timestamp", 1))
    return msgs[since_count:]


def get_conversation_state():
    """Get current conversation state"""
    state = db.conversation_states.find_one({"phone_number": TEST_PHONE}, {"_id": 0})
    return state


def check_quote():
    """Check if a quote was created"""
    quote = db.quotes_v2.find_one(
        {"phone_number": TEST_PHONE, "status": "pending", "is_deleted": False},
        {"_id": 0}
    )
    return quote


def run_step(step_name, user_msg, expected_checks, wait_time=8):
    """Run a conversation step and verify"""
    print(f"\n{'='*60}")
    print(f"PASO: {step_name}")
    print(f"USUARIO: {user_msg}")
    
    # Count current bot messages
    conv = db.conversations.find_one({"phone_number": TEST_PHONE}, {"_id": 0, "id": 1})
    prev_count = 0
    if conv:
        prev_count = db.messages.count_documents(
            {"conversation_id": conv["id"], "sender": {"$in": ["business", "bot"]}}
        )
    
    status = send_message(user_msg)
    print(f"  Webhook status: {status}")
    
    # Wait for bot to process (LLM call takes time)
    print(f"  Esperando {wait_time}s para respuesta del bot...")
    time.sleep(wait_time)
    
    # Get new bot responses
    new_msgs = get_bot_responses(prev_count)
    print(f"  BOT respondió ({len(new_msgs)} mensajes):")
    for msg in new_msgs:
        text = msg.get("content", {}).get("text", "")
        print(f"    >> {text[:200]}")
    
    # Get state
    state = get_conversation_state()
    collected = state.get("collected_data", {}) if state else {}
    print(f"  Datos recopilados: {json.dumps(collected, ensure_ascii=False, indent=2)}")
    
    # Run checks
    results = {}
    for check_name, check_fn in expected_checks.items():
        passed = check_fn(new_msgs, state, collected)
        results[check_name] = passed
        status_icon = "PASS" if passed else "FAIL"
        print(f"  [{status_icon}] {check_name}")
    
    return results, new_msgs, state


def main():
    clean_test_data()
    
    all_results = {}
    
    # STEP 1: Greeting
    results, msgs, state = run_step(
        "1 - Saludo inicial",
        "Hola buenas tardes",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Bot se presenta como Ana": lambda m, s, c: any("ana" in msg.get("content",{}).get("text","").lower() or "gimmicks" in msg.get("content",{}).get("text","").lower() for msg in m),
            "Bot pregunta nombre o en qué ayudar": lambda m, s, c: len(m) > 0,
        }
    )
    all_results.update(results)
    
    # STEP 2: User gives name + product interest
    results, msgs, state = run_step(
        "2 - Nombre + interés en producto",
        "Me llamo Carlos Mendez, necesito cotizar jarros",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Nombre extraído": lambda m, s, c: bool(c.get("nombre")),
            "Bot NO re-pregunta nombre": lambda m, s, c: not any("nombre" in msg.get("content",{}).get("text","").lower() and "compart" in msg.get("content",{}).get("text","").lower() for msg in m),
        }
    )
    all_results.update(results)
    
    # STEP 3: Check catalog was sent (link should appear)
    results, msgs, state = run_step(
        "3 - Verificar catálogo",
        "sí, muéstrame opciones de jarros",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Catálogo o link enviado": lambda m, s, c: any("catalog" in msg.get("content",{}).get("text","").lower() or "código" in msg.get("content",{}).get("text","").lower() or "catálogo" in msg.get("content",{}).get("text","").lower() for msg in m),
            "Sin texto redundante largo": lambda m, s, c: all(len(msg.get("content",{}).get("text","")) < 800 for msg in m),
        },
        wait_time=10
    )
    all_results.update(results)
    
    # STEP 4: User provides product codes
    results, msgs, state = run_step(
        "4 - Usuario comparte códigos",
        "Me interesan JARPOR00391 y JARPOR00250",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Códigos extraídos": lambda m, s, c: bool(c.get("codigos_producto")),
            "Bot pregunta cantidades": lambda m, s, c: any("cuánt" in msg.get("content",{}).get("text","").lower() or "unidad" in msg.get("content",{}).get("text","").lower() or "cantidad" in msg.get("content",{}).get("text","").lower() for msg in m),
            "NO hay cotización aún": lambda m, s, c: check_quote() is None,
        }
    )
    all_results.update(results)
    
    # STEP 5: User provides quantities
    results, msgs, state = run_step(
        "5 - Usuario da cantidades",
        "200 de cada uno",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Cantidades extraídas": lambda m, s, c: bool(c.get("cantidad") or c.get("cantidades_por_producto")),
            "NO hay cotización aún": lambda m, s, c: check_quote() is None,
        }
    )
    all_results.update(results)
    
    # STEP 6: Bot should ask for personalization, then email, then company - one at a time
    results, msgs, state = run_step(
        "6 - Bot pide personalización",
        "Serigrafía",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Personalización extraída": lambda m, s, c: bool(c.get("personalizacion")),
            "NO hay cotización aún": lambda m, s, c: check_quote() is None,
        }
    )
    all_results.update(results)
    
    # STEP 7: User provides email 
    results, msgs, state = run_step(
        "7 - Usuario da correo",
        "carlos.mendez@empresa.com",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Correo extraído": lambda m, s, c: bool(c.get("correo")),
            "NO hay cotización aún (falta empresa)": lambda m, s, c: check_quote() is None,
        }
    )
    all_results.update(results)
    
    # STEP 8: User provides company name - THIS should trigger quote
    results, msgs, state = run_step(
        "8 - Usuario da empresa (debería generar cotización)",
        "Grupo Industrial ABC",
        {
            "Bot responde": lambda m, s, c: len(m) > 0,
            "Empresa extraída": lambda m, s, c: bool(c.get("empresa")),
            "Cotización GENERADA": lambda m, s, c: check_quote() is not None,
            "Mensaje de confirmación de cotización": lambda m, s, c: any("cotización" in msg.get("content",{}).get("text","").lower() or "registrada" in msg.get("content",{}).get("text","").lower() for msg in m),
        },
        wait_time=12
    )
    all_results.update(results)
    
    # FINAL SUMMARY
    print(f"\n{'='*60}")
    print("RESUMEN FINAL")
    print(f"{'='*60}")
    
    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)
    
    for name, result in all_results.items():
        icon = "PASS" if result else "FAIL"
        print(f"  [{icon}] {name}")
    
    print(f"\nResultado: {passed}/{total} verificaciones pasaron")
    
    # Final state check
    final_state = get_conversation_state()
    if final_state:
        print(f"\nDatos finales recopilados:")
        cd = final_state.get("collected_data", {})
        print(f"  nombre: {cd.get('nombre')}")
        print(f"  codigos: {cd.get('codigos_producto')}")
        print(f"  cantidad: {cd.get('cantidad') or cd.get('cantidades_por_producto')}")
        print(f"  personalizacion: {cd.get('personalizacion')}")
        print(f"  correo: {cd.get('correo')}")
        print(f"  empresa: {cd.get('empresa')}")
        print(f"  quote_generated: {final_state.get('quote_generated')}")
    
    quote = check_quote()
    if quote:
        print(f"\nCotización generada:")
        print(f"  Número: {quote.get('quote_number')}")
        print(f"  Cliente: {quote.get('client_name')}")
        print(f"  Items: {len(quote.get('items', []))}")
        print(f"  Total: ${quote.get('total', 0):.2f}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
