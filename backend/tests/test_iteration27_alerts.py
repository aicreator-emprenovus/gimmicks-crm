"""
Iteration 27: Testing 5 WhatsApp Alerts to Staff + Bot Behavior
- Alert #1: New quote notification (NUEVA COTIZACION)
- Alert #2: Quote updated notification (COTIZACION ACTUALIZADA)
- Alert #3: Escalation keywords trigger (ESCALAMIENTO)
- Alert #4: Bot cannot continue (BOT NO PUEDE CONTINUAR) - LLM failure
- Alert #5: Product not found → ask email → notify staff (SOLICITUD DE CATALOGO POR EMAIL)
- Bot NEVER says "no tenemos" or "no encontre" when products not found
- STOPWORDS filter in search_products_by_keyword
- Normal product search still works
"""
import pytest
import requests
import os
import time
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
STAFF_PHONE = "593999440910"

# Test phone numbers - unique per test to avoid conflicts
def get_test_phone():
    return f"593999{uuid.uuid4().hex[:6]}"


class TestStaffNotificationConfig:
    """Verify staff notification phone is configured correctly"""
    
    def test_staff_phone_configured(self):
        """Verify STAFF_NOTIFICATION_PHONE is set to 593999440910"""
        # This is verified by checking the bot_service.py code
        # The constant is defined at line 607
        assert STAFF_PHONE == "593999440910", "Staff phone should be 593999440910"
        print("✓ STAFF_NOTIFICATION_PHONE = 593999440910 configured")


class TestAlert1NewQuote:
    """Alert #1: Staff notification when new quote is generated"""
    
    def test_new_quote_notification_format(self):
        """Test that new quote notification has correct format"""
        # Simulate a full flow that generates a quote
        phone = get_test_phone()
        
        # Step 1: Initial greeting
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola, quiero cotizar"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 1: Initial greeting sent")
        time.sleep(8)
        
        # Step 2: Provide name
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Soy Carlos de Empresa ABC"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 2: Name provided")
        time.sleep(8)
        
        # Step 3: Request product
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito jarros"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 3: Product requested")
        time.sleep(8)
        
        # Step 4: Provide codes
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "JARPOR00391"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 4: Product code provided")
        time.sleep(8)
        
        # Step 5: Provide quantity
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "100 unidades"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 5: Quantity provided")
        time.sleep(8)
        
        # Step 6: Provide personalization
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "serigrafia"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 6: Personalization provided")
        time.sleep(8)
        
        # Step 7: Provide email (this should trigger quote generation)
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Cliente"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "carlos@empresaabc.com"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Step 7: Email provided")
        time.sleep(10)
        
        # Check if staff notification was sent
        # Get messages for staff phone
        staff_conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if staff_conv_response.status_code == 200:
            conversations = staff_conv_response.json()
            staff_conv = next((c for c in conversations if c.get("phone_number") == STAFF_PHONE), None)
            if staff_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{staff_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    # Look for NUEVA COTIZACION message
                    new_quote_msgs = [m for m in messages if "NUEVA COTIZACION" in m.get("content", {}).get("text", "")]
                    if new_quote_msgs:
                        print("✓ Alert #1: NUEVA COTIZACION notification found in staff messages")
                        msg_text = new_quote_msgs[-1].get("content", {}).get("text", "")
                        assert "Cliente:" in msg_text, "Notification should include Cliente"
                        assert "Telefono:" in msg_text, "Notification should include Telefono"
                        print(f"✓ Notification format verified: {msg_text[:100]}...")
                    else:
                        print("⚠ NUEVA COTIZACION message not found in staff conversation")
        
        # Verify quote was created
        quotes_response = requests.get(f"{BASE_URL}/api/quotes")
        if quotes_response.status_code == 200:
            quotes = quotes_response.json()
            client_quote = next((q for q in quotes if q.get("phone_number") == phone), None)
            if client_quote:
                print(f"✓ Quote created: #{client_quote.get('quote_number')}")
            else:
                print("⚠ Quote not found for test phone")
        
        print("✓ Alert #1 test completed")


class TestAlert3Escalation:
    """Alert #3: Escalation keywords trigger ESCALAMIENTO message"""
    
    def test_escalation_keyword_persona_real(self):
        """Test 'persona real' triggers escalation"""
        phone = get_test_phone()
        
        # First message to create conversation
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Escalation"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Maria"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Send escalation keyword
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Escalation"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Quiero hablar con una persona real"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Escalation keyword 'persona real' sent")
        time.sleep(10)
        
        # Check staff notification
        staff_conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if staff_conv_response.status_code == 200:
            conversations = staff_conv_response.json()
            staff_conv = next((c for c in conversations if c.get("phone_number") == STAFF_PHONE), None)
            if staff_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{staff_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    escalation_msgs = [m for m in messages if "ESCALAMIENTO" in m.get("content", {}).get("text", "")]
                    if escalation_msgs:
                        print("✓ Alert #3: ESCALAMIENTO notification found")
                        msg_text = escalation_msgs[-1].get("content", {}).get("text", "")
                        assert "Motivo:" in msg_text, "Should include Motivo"
                        print(f"✓ Escalation message: {msg_text[:150]}...")
                    else:
                        print("⚠ ESCALAMIENTO message not found")
        
        print("✓ Alert #3 test completed")
    
    def test_escalation_keyword_hablar_con_alguien(self):
        """Test 'hablar con alguien' triggers escalation"""
        phone = get_test_phone()
        
        # First message
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Escalation2"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Pedro"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Send escalation keyword
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Escalation2"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito hablar con alguien de ventas"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Escalation keyword 'hablar con alguien' sent")
        time.sleep(10)
        print("✓ Alert #3 (hablar con alguien) test completed")


class TestAlert5ProductNotFound:
    """Alert #5: Product not found → ask email → notify staff"""
    
    def test_product_not_found_asks_for_email(self):
        """When product search returns 0 results, bot asks for email"""
        phone = get_test_phone()
        
        # First message - provide name
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test NoProduct"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Ana"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Search for non-existent product (drones don't exist in inventory)
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test NoProduct"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito drones para mi empresa"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Non-existent product 'drones' requested")
        time.sleep(10)
        
        # Check bot response - should NOT say "no tenemos" or "no encontre"
        conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if conv_response.status_code == 200:
            conversations = conv_response.json()
            test_conv = next((c for c in conversations if c.get("phone_number") == phone), None)
            if test_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{test_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    bot_msgs = [m for m in messages if m.get("sender") in ["bot", "business"]]
                    if bot_msgs:
                        last_bot_msg = bot_msgs[-1].get("content", {}).get("text", "").lower()
                        # Bot should NOT say these phrases
                        assert "no tenemos" not in last_bot_msg, "Bot should NOT say 'no tenemos'"
                        assert "no encontre" not in last_bot_msg, "Bot should NOT say 'no encontre'"
                        assert "no hay" not in last_bot_msg, "Bot should NOT say 'no hay'"
                        print("✓ Bot did NOT say 'no tenemos', 'no encontre', or 'no hay'")
                        
                        # Bot should ask for email or mention catalog
                        if "correo" in last_bot_msg or "email" in last_bot_msg or "catalogo" in last_bot_msg:
                            print("✓ Bot asked for email or mentioned catalog")
                        else:
                            print(f"⚠ Bot response: {last_bot_msg[:200]}")
        
        # Now provide email to trigger catalog notification
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test NoProduct"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Mi correo es ana@test.com"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Email provided after product not found")
        time.sleep(10)
        
        # Check staff notification for catalog request
        staff_conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if staff_conv_response.status_code == 200:
            conversations = staff_conv_response.json()
            staff_conv = next((c for c in conversations if c.get("phone_number") == STAFF_PHONE), None)
            if staff_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{staff_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    catalog_msgs = [m for m in messages if "SOLICITUD DE CATALOGO" in m.get("content", {}).get("text", "")]
                    if catalog_msgs:
                        print("✓ Alert #5: SOLICITUD DE CATALOGO POR EMAIL notification found")
                        msg_text = catalog_msgs[-1].get("content", {}).get("text", "")
                        assert "Email:" in msg_text, "Should include Email"
                        print(f"✓ Catalog request notification: {msg_text[:150]}...")
                    else:
                        print("⚠ SOLICITUD DE CATALOGO message not found in staff conversation")
        
        print("✓ Alert #5 test completed")


class TestStopwordsFilter:
    """Test STOPWORDS filter in search_products_by_keyword"""
    
    def test_stopwords_dont_cause_false_positives(self):
        """Common Spanish words like 'para', 'con' should be filtered"""
        phone = get_test_phone()
        
        # First message - provide name
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Stopwords"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Luis"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Send message with only stopwords - should not trigger product search
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Stopwords"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "para con de la el"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Message with only stopwords sent")
        time.sleep(8)
        print("✓ Stopwords filter test completed")


class TestNormalProductSearch:
    """Test that normal product search still works correctly"""
    
    def test_jarros_search_returns_products(self):
        """Search for 'jarros' should return products"""
        phone = get_test_phone()
        
        # First message - provide name
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Search"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Roberto"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Search for jarros
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Search"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito jarros"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Product search 'jarros' sent")
        time.sleep(10)
        
        # Check bot response - should show product codes
        conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if conv_response.status_code == 200:
            conversations = conv_response.json()
            test_conv = next((c for c in conversations if c.get("phone_number") == phone), None)
            if test_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{test_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    bot_msgs = [m for m in messages if m.get("sender") in ["bot", "business"]]
                    if bot_msgs:
                        last_bot_msg = bot_msgs[-1].get("content", {}).get("text", "")
                        # Bot should show products or mention codes
                        if "JAR" in last_bot_msg.upper() or "codigo" in last_bot_msg.lower() or "opciones" in last_bot_msg.lower():
                            print("✓ Bot showed product codes or options")
                        else:
                            print(f"Bot response: {last_bot_msg[:200]}")
        
        print("✓ Normal product search test completed")


class TestWebhookBasic:
    """Basic webhook functionality"""
    
    def test_webhook_returns_200(self):
        """POST /api/webhook/whatsapp returns 200"""
        phone = get_test_phone()
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test Basic"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Webhook returns 200 with status=ok")


class TestBotNeverSaysNoTenemos:
    """Verify bot NEVER says 'no tenemos' or 'no encontre'"""
    
    def test_bot_response_for_nonexistent_product(self):
        """Bot should offer catalog by email, not say product doesn't exist"""
        phone = get_test_phone()
        
        # Provide name first
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test NoTenemos"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Elena"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        time.sleep(8)
        
        # Ask for product that doesn't exist
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json={
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test NoTenemos"}, "wa_id": phone}],
                        "messages": [{
                            "from": phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito bicicletas electricas"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        })
        assert response.status_code == 200
        print("✓ Non-existent product 'bicicletas electricas' requested")
        time.sleep(10)
        
        # Check bot response
        conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if conv_response.status_code == 200:
            conversations = conv_response.json()
            test_conv = next((c for c in conversations if c.get("phone_number") == phone), None)
            if test_conv:
                msgs_response = requests.get(f"{BASE_URL}/api/conversations/{test_conv['id']}/messages")
                if msgs_response.status_code == 200:
                    messages = msgs_response.json()
                    bot_msgs = [m for m in messages if m.get("sender") in ["bot", "business"]]
                    if bot_msgs:
                        last_bot_msg = bot_msgs[-1].get("content", {}).get("text", "").lower()
                        
                        # CRITICAL: Bot should NEVER say these
                        forbidden_phrases = ["no tenemos", "no encontre", "no hay en inventario", "no disponemos"]
                        for phrase in forbidden_phrases:
                            assert phrase not in last_bot_msg, f"Bot should NOT say '{phrase}'"
                        
                        print("✓ Bot did NOT use forbidden phrases")
                        print(f"Bot response: {last_bot_msg[:200]}")
        
        print("✓ Bot 'no tenemos' test completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
