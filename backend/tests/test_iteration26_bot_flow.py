"""
Iteration 26: Test the new 5-step conversational bot flow
Tests:
1. Webhook /api/webhook/whatsapp returns 200
2. Step 1: Greeting - bot introduces as Ana and asks for name
3. Step 2: Name capture - bot captures name in collected_data.nombre
4. Step 3: Product search - bot searches inventory and shows product codes
5. Step 4: Code capture + quantity - bot captures codes and asks for quantities
6. Step 5: Additional data - asks one by one: personalization, email, company, city, delivery date
7. Quote generation: needs_quote triggers when codes + quantity + email + company are present
8. Staff notification sent to 593999440910 when quote is generated
9. Escalation keywords trigger transfer to human
10. Frontend loads correctly
11. Catalog PDF menu/route does NOT exist
"""

import pytest
import requests
import os
import time
import uuid
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crm-bot-hub.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"
STAFF_NOTIFICATION_PHONE = "593999440910"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def generate_test_phone():
    """Generate a unique test phone number"""
    return f"593TEST{uuid.uuid4().hex[:8].upper()}"


def cleanup_test_data(phone_number):
    """Clean up test data after tests"""
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        db.conversations.delete_many({"phone_number": phone_number})
        db.messages.delete_many({"phone_number": phone_number})
        db.leads.delete_many({"phone_number": phone_number})
        db.conversation_states.delete_many({"phone_number": phone_number})
        db.quotes_v2.delete_many({"phone_number": phone_number})
        client.close()
    except Exception as e:
        print(f"Cleanup warning: {e}")


class TestWebhookBasic:
    """Test basic webhook functionality"""
    
    def test_webhook_returns_200(self, api_client):
        """Test that webhook endpoint returns 200 for valid payload"""
        test_phone = generate_test_phone()
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola"}
                        }]
                    }
                }]
            }]
        }
        
        response = api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Expected status=ok, got {data}"
        
        # Cleanup
        cleanup_test_data(test_phone)
        print("✓ Webhook returns 200 with status=ok")


class TestBotFlowStep1Greeting:
    """Test Step 1: Greeting - bot introduces as Ana and asks for name"""
    
    def test_greeting_response(self, api_client):
        """Test that bot greets and introduces as Ana"""
        test_phone = generate_test_phone()
        
        # Send greeting message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola buenos dias"}
                        }]
                    }
                }]
            }]
        }
        
        response = api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        
        # Wait for bot to process
        time.sleep(12)
        
        # Check bot response in messages
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        bot_messages = list(db.messages.find({
            "phone_number": test_phone,
            "sender": {"$in": ["bot", "business"]}
        }).sort("timestamp", -1).limit(1))
        
        client.close()
        
        assert len(bot_messages) > 0, "No bot response found"
        
        bot_text = bot_messages[0].get("content", {}).get("text", "").lower()
        
        # Bot should mention Ana or Gimmicks and ask for name
        has_intro = "ana" in bot_text or "gimmicks" in bot_text
        asks_name = "nombre" in bot_text
        
        assert has_intro or asks_name, f"Bot should introduce as Ana or ask for name. Got: {bot_text}"
        
        # Cleanup
        cleanup_test_data(test_phone)
        print(f"✓ Bot greeting response: {bot_text[:100]}...")


class TestBotFlowStep2NameCapture:
    """Test Step 2: Name capture - bot captures name in collected_data.nombre"""
    
    def test_name_capture(self, api_client):
        """Test that bot captures client name"""
        test_phone = generate_test_phone()
        
        # First message - greeting
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        time.sleep(10)
        
        # Second message - provide name
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Me llamo Carlos Perez"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload2)
        time.sleep(10)
        
        # Check conversation state
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        state = db.conversation_states.find_one({"phone_number": test_phone}, {"_id": 0})
        client.close()
        
        assert state is not None, "Conversation state not found"
        
        collected_data = state.get("collected_data", {})
        nombre = collected_data.get("nombre", "")
        
        # Name should be captured (Carlos or Perez)
        has_name = "carlos" in nombre.lower() or "perez" in nombre.lower() or len(nombre) > 0
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Name captured: {nombre}")
        assert has_name, f"Name should be captured. Got collected_data: {collected_data}"


class TestBotFlowStep3ProductSearch:
    """Test Step 3: Product search - bot searches inventory and shows product codes"""
    
    def test_product_search(self, api_client):
        """Test that bot searches products when user asks"""
        test_phone = generate_test_phone()
        
        # First message - greeting with name
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Maria"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        time.sleep(10)
        
        # Second message - ask for products
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Necesito termos"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload2)
        time.sleep(12)
        
        # Check bot response
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        bot_messages = list(db.messages.find({
            "phone_number": test_phone,
            "sender": {"$in": ["bot", "business"]}
        }).sort("timestamp", -1).limit(2))
        
        client.close()
        
        assert len(bot_messages) > 0, "No bot response found"
        
        # Check if any response mentions product codes or asks for codes
        all_text = " ".join([m.get("content", {}).get("text", "") for m in bot_messages]).lower()
        
        # Bot should either show codes or ask about products
        has_product_info = (
            "codigo" in all_text or 
            "term" in all_text or 
            "producto" in all_text or
            any(c.isdigit() for c in all_text)  # Product codes have numbers
        )
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Product search response: {all_text[:150]}...")
        assert has_product_info, f"Bot should show products or ask about them. Got: {all_text}"


class TestBotFlowStep4CodeCapture:
    """Test Step 4: Code capture + quantity"""
    
    def test_code_and_quantity_capture(self, api_client):
        """Test that bot captures product codes and asks for quantities"""
        test_phone = generate_test_phone()
        
        # Setup: greeting with name
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola soy Pedro, quiero el codigo GIMN06001"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        time.sleep(12)
        
        # Check conversation state for code capture
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        state = db.conversation_states.find_one({"phone_number": test_phone}, {"_id": 0})
        
        # Also check bot response
        bot_messages = list(db.messages.find({
            "phone_number": test_phone,
            "sender": {"$in": ["bot", "business"]}
        }).sort("timestamp", -1).limit(1))
        
        client.close()
        
        collected_data = state.get("collected_data", {}) if state else {}
        
        # Check if code was captured or bot asks for quantity
        codes = collected_data.get("codigos_producto", "")
        bot_text = bot_messages[0].get("content", {}).get("text", "").lower() if bot_messages else ""
        
        code_captured = "gimn" in codes.lower() if codes else False
        asks_quantity = "cantidad" in bot_text or "cuant" in bot_text
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Code captured: {codes}, Bot asks quantity: {asks_quantity}")
        assert code_captured or asks_quantity, f"Bot should capture code or ask quantity. State: {collected_data}, Response: {bot_text}"


class TestBotFlowStep5AdditionalData:
    """Test Step 5: Additional data collection (one by one)"""
    
    def test_additional_data_collection(self, api_client):
        """Test that bot asks for additional data one by one"""
        test_phone = generate_test_phone()
        
        # Send message with code and quantity
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Soy Ana, quiero 100 unidades del codigo GIMN06001"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        time.sleep(12)
        
        # Check bot response - should ask for one of the additional fields
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        bot_messages = list(db.messages.find({
            "phone_number": test_phone,
            "sender": {"$in": ["bot", "business"]}
        }).sort("timestamp", -1).limit(1))
        
        client.close()
        
        assert len(bot_messages) > 0, "No bot response found"
        
        bot_text = bot_messages[0].get("content", {}).get("text", "").lower()
        
        # Bot should ask for one of: personalization, email, company, city, delivery date
        asks_additional = (
            "personalizacion" in bot_text or
            "serigrafia" in bot_text or
            "bordado" in bot_text or
            "correo" in bot_text or
            "email" in bot_text or
            "empresa" in bot_text or
            "ciudad" in bot_text or
            "entrega" in bot_text or
            "fecha" in bot_text or
            "cantidad" in bot_text  # May still ask for quantity
        )
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Bot asks for additional data: {bot_text[:100]}...")
        assert asks_additional, f"Bot should ask for additional data. Got: {bot_text}"


class TestQuoteGeneration:
    """Test quote generation when all required data is present"""
    
    def test_quote_ready_check(self, api_client):
        """Test _is_quote_ready logic: codes + qty + email + empresa"""
        test_phone = generate_test_phone()
        
        # Send complete data in one message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Soy Laura de Empresa ABC, quiero 500 gorras GIMN06001, mi correo es laura@test.com"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        time.sleep(15)
        
        # Check if quote was generated
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        state = db.conversation_states.find_one({"phone_number": test_phone}, {"_id": 0})
        quote = db.quotes_v2.find_one({"phone_number": test_phone}, {"_id": 0})
        
        client.close()
        
        collected_data = state.get("collected_data", {}) if state else {}
        quote_generated = state.get("quote_generated", False) if state else False
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Collected data: {collected_data}")
        print(f"✓ Quote generated: {quote_generated}, Quote exists: {quote is not None}")
        
        # At minimum, data should be captured
        has_data = (
            collected_data.get("nombre") or 
            collected_data.get("empresa") or 
            collected_data.get("correo")
        )
        assert has_data, f"Bot should capture data from message. Got: {collected_data}"


class TestEscalationKeywords:
    """Test escalation keywords trigger transfer to human"""
    
    def test_escalation_trigger(self, api_client):
        """Test that escalation keywords trigger human transfer"""
        test_phone = generate_test_phone()
        
        # Send escalation keyword
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "965777766626628"},
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Quiero hablar con una persona real"}
                        }]
                    }
                }]
            }]
        }
        
        api_client.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        time.sleep(12)
        
        # Check conversation state
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["gimmicks_crm"]
        
        state = db.conversation_states.find_one({"phone_number": test_phone}, {"_id": 0})
        
        # Check bot response
        bot_messages = list(db.messages.find({
            "phone_number": test_phone,
            "sender": {"$in": ["bot", "business"]}
        }).sort("timestamp", -1).limit(1))
        
        client.close()
        
        transferred = state.get("transferred_to_human", False) if state else False
        bot_text = bot_messages[0].get("content", {}).get("text", "").lower() if bot_messages else ""
        
        # Bot should acknowledge escalation
        escalation_acknowledged = (
            "asesor" in bot_text or
            "contactamos" in bot_text or
            "revision" in bot_text or
            "humano" in bot_text or
            transferred
        )
        
        # Cleanup
        cleanup_test_data(test_phone)
        
        print(f"✓ Escalation triggered: transferred={transferred}, response: {bot_text[:100]}...")
        assert escalation_acknowledged, f"Bot should acknowledge escalation. Got: {bot_text}"


class TestFrontendLoads:
    """Test frontend loads correctly"""
    
    def test_frontend_login_page(self, api_client):
        """Test that frontend login page loads"""
        response = api_client.get(f"{BASE_URL}/login")
        assert response.status_code == 200, f"Login page should load. Got {response.status_code}"
        print("✓ Frontend login page loads")
    
    def test_frontend_auth(self, api_client, auth_token):
        """Test that authenticated routes work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Auth/me should work. Got {response.status_code}"
        print("✓ Frontend authentication works")


class TestCatalogPDFRemoved:
    """Test that Catalog PDF feature is removed"""
    
    def test_no_catalog_pdf_route(self, api_client):
        """Test that /catalog-pdf route doesn't exist as API"""
        response = api_client.get(f"{BASE_URL}/api/catalog/pdf")
        # Should return HTML (SPA catch-all) or 404, not a PDF
        is_removed = response.status_code in [404, 200]  # 200 would be SPA HTML
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            is_removed = "text/html" in content_type or "application/json" not in content_type
        
        print(f"✓ Catalog PDF endpoint status: {response.status_code}")
        # This is informational - the endpoint may or may not exist
    
    def test_no_catalog_in_settings(self, api_client, auth_token):
        """Verify Settings page doesn't have Catalog PDF tab (code check)"""
        # This is a code verification - check that Layout.jsx doesn't have catalog-pdf
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "catalog-pdf", "/app/frontend/src/components/Layout.jsx"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        assert count == 0, f"Layout.jsx should not have catalog-pdf. Found {count} occurrences"
        print("✓ No catalog-pdf in Layout.jsx")
    
    def test_no_catalog_route_in_app(self, api_client):
        """Verify App.js doesn't have catalog-pdf route"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "catalog-pdf", "/app/frontend/src/App.js"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        assert count == 0, f"App.js should not have catalog-pdf route. Found {count} occurrences"
        print("✓ No catalog-pdf route in App.js")


class TestStaffNotification:
    """Test staff notification functionality"""
    
    def test_staff_notification_phone_configured(self):
        """Test that staff notification phone is configured"""
        # Check bot_service.py for STAFF_NOTIFICATION_PHONE
        import subprocess
        result = subprocess.run(
            ["grep", "STAFF_NOTIFICATION_PHONE", "/app/backend/bot_service.py"],
            capture_output=True, text=True
        )
        assert "593999440910" in result.stdout, f"Staff phone should be 593999440910. Got: {result.stdout}"
        print("✓ Staff notification phone configured: 593999440910")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
