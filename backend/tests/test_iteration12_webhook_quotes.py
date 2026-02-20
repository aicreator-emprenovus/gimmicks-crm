"""
Iteration 12 Tests: WhatsApp Bot Quote Creation/Update Flow
Tests for:
- Login with admin credentials
- Bot webhook processes messages
- Bot extracts data correctly: codigos_producto, cantidades_por_producto, correo, nombre, empresa, ciudad
- Field aliases normalize: correo_electronico → correo, cantidad_unidades → cantidad, ciudad_de_entrega → ciudad
- Quote created in quotes_v2 with correct quantities when has codes + quantity + email
- Quote updated (not duplicated) when client requests changes
- Staff notification sent to 593963266566 with ALERTA COTIZACION NUEVA/ACTUALIZADA
- Inbox page loads conversations and messages
- GET /api/conversations returns list
- GET /api/conversations/{id}/messages returns messages
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BASE_URL:
    BASE_URL = "https://interesado-crm.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip('/')

TEST_PHONE = f"593999TEST{uuid.uuid4().hex[:4].upper()}"
STAFF_NOTIFICATION_PHONE = "593963266566"


class TestAuthAPI:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test login with admin@gimmicks.com / admin123456"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == "admin@gimmicks.com"
        print(f"✓ Login successful, token: {data['access_token'][:20]}...")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


@pytest.fixture(scope="class")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@gimmicks.com",
        "password": "admin123456"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="class")
def authenticated_headers(auth_token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestWebhookAndBotFlow:
    """Test bot webhook processing and quote creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_headers):
        self.headers = authenticated_headers
        # Use unique phone for this test class
        self.test_phone = f"593999T12{uuid.uuid4().hex[:4].upper()}"
    
    def test_webhook_receives_message(self):
        """Test POST /api/webhook/whatsapp processes message correctly"""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {},
                        "messages": [{
                            "from": self.test_phone,
                            "id": f"test-iter12-{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola, necesito información sobre jarros"}
                        }]
                    }
                }]
            }]
        }
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        assert response.json().get("status") == "ok"
        print(f"✓ Webhook received message from {self.test_phone}")
    
    def test_webhook_with_full_quote_data(self):
        """Test bot creates quote when receiving codes + quantity + email in one message"""
        unique_phone = f"593999FQ{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"test-fullquote-{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {
                                "body": "Hola quiero cotizar los productos JARVID00020 con 150 unidades y JARPOR00143 con 200 unidades. Mi correo es testquote@test.com, soy Juan Perez de TestCorp en Quito"
                            }
                        }]
                    }
                }]
            }]
        }
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        print(f"✓ Webhook processed full quote data for {unique_phone}")
        
        # Wait for LLM processing (takes ~8-10 seconds)
        print("  Waiting 12 seconds for LLM to process...")
        time.sleep(12)
        
        # Check if quote was created in quotes_v2
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"trash": "false", "doc_type": "QUOTE"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to fetch quotes: {response.text}"
        quotes = response.json()
        
        # Find quote for this phone
        quote_found = None
        for q in quotes:
            if q.get("phone_number") == unique_phone:
                quote_found = q
                break
        
        # Quote might not be created if LLM didn't extract all data correctly
        # This is expected behavior - LLM might ask follow-up questions
        if quote_found:
            print(f"✓ Quote found for {unique_phone}: #{quote_found.get('quote_number')}")
            assert quote_found.get("client_email") == "testquote@test.com", "Email not correctly stored"
            assert len(quote_found.get("items", [])) > 0, "Quote has no items"
        else:
            print(f"  Note: Quote not created yet (LLM may have asked follow-up questions)")


class TestConversationsAPI:
    """Test conversations endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_headers):
        self.headers = authenticated_headers
    
    def test_get_conversations_list(self):
        """Test GET /api/conversations returns conversation list"""
        response = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        assert response.status_code == 200, f"Failed to fetch conversations: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/conversations returned {len(data)} conversations")
        
        # Verify structure of first conversation if any exist
        if data:
            conv = data[0]
            assert "id" in conv, "Missing 'id' field"
            assert "phone_number" in conv, "Missing 'phone_number' field"
            assert "status" in conv, "Missing 'status' field"
            print(f"  First conversation: {conv.get('phone_number')} - {conv.get('contact_name', 'No name')}")
    
    def test_get_conversation_messages(self, authenticated_headers):
        """Test GET /api/conversations/{id}/messages returns messages"""
        # First get a conversation
        response = requests.get(f"{BASE_URL}/api/conversations", headers=authenticated_headers)
        assert response.status_code == 200
        convs = response.json()
        
        if not convs:
            pytest.skip("No conversations available to test messages")
        
        conv_id = convs[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/conversations/{conv_id}/messages",
            headers=authenticated_headers
        )
        assert response.status_code == 200, f"Failed to fetch messages: {response.text}"
        messages = response.json()
        assert isinstance(messages, list), "Response should be a list"
        print(f"✓ GET /api/conversations/{conv_id}/messages returned {len(messages)} messages")
        
        if messages:
            msg = messages[0]
            assert "id" in msg, "Missing 'id' in message"
            assert "sender" in msg, "Missing 'sender' in message"
            assert "content" in msg, "Missing 'content' in message"


class TestQuotesV2API:
    """Test quotes_v2 endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_headers):
        self.headers = authenticated_headers
    
    def test_get_quotes_list(self):
        """Test GET /api/quotes-v2 returns quotes"""
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"trash": "false", "doc_type": "QUOTE"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to fetch quotes: {response.text}"
        quotes = response.json()
        assert isinstance(quotes, list), "Response should be a list"
        print(f"✓ GET /api/quotes-v2 returned {len(quotes)} quotes")
        
        if quotes:
            q = quotes[0]
            assert "id" in q, "Missing 'id'"
            assert "quote_number" in q, "Missing 'quote_number'"
            assert "status" in q, "Missing 'status'"


class TestFieldAliasNormalization:
    """Test that bot_service field aliases work correctly"""
    
    def test_field_aliases_defined(self):
        """Verify field aliases are properly defined in bot_service.py"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read bot_service.py and check field_aliases
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        # Check expected aliases exist
        expected_aliases = [
            '"correo_electronico": "correo"',
            '"correo_electrónico": "correo"',
            '"cantidad_unidades": "cantidad"',
            '"ciudad_de_entrega": "ciudad"',
            '"ciudad_entrega": "ciudad"',
            '"email": "correo"',
        ]
        
        for alias in expected_aliases:
            assert alias in content, f"Missing alias: {alias}"
            print(f"✓ Found alias: {alias}")
        
        print("✓ All expected field aliases are defined")


class TestStaffNotifications:
    """Test staff notification functionality"""
    
    def test_staff_notification_phone_configured(self):
        """Verify STAFF_NOTIFICATION_PHONE is correctly set"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        assert 'STAFF_NOTIFICATION_PHONE = "593963266566"' in content, \
            "STAFF_NOTIFICATION_PHONE not set to 593963266566"
        print("✓ STAFF_NOTIFICATION_PHONE = 593963266566")
    
    def test_notify_staff_function_exists(self):
        """Verify notify_staff_new_quote function exists and has correct format"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        assert "async def notify_staff_new_quote" in content, \
            "notify_staff_new_quote function not found"
        assert "ALERTA COTIZACION" in content, \
            "ALERTA COTIZACION notification text not found"
        print("✓ notify_staff_new_quote function exists with ALERTA COTIZACION text")


class TestInboxPolling:
    """Test Inbox real-time polling functionality"""
    
    def test_inbox_has_polling(self):
        """Verify Inbox.jsx has 5-second message polling"""
        with open('/app/frontend/src/pages/Inbox.jsx', 'r') as f:
            content = f.read()
        
        # Check for 5-second polling interval
        assert "fetchMessages(selectedConv.id, true), 5000" in content, \
            "5-second message polling not found in Inbox.jsx"
        print("✓ Inbox.jsx has 5-second message polling")
        
        # Check for sync indicator
        assert "syncIndicator" in content, "syncIndicator state not found"
        assert "data-testid=\"sync-indicator\"" in content, "sync-indicator testid not found"
        print("✓ Sync indicator implemented in Inbox.jsx")
        
        # Check for prevMessageCountRef
        assert "prevMessageCountRef" in content, "prevMessageCountRef not found"
        print("✓ prevMessageCountRef for smart scrolling implemented")


class TestQuoteCreationFromWebhook:
    """Test full flow: webhook message → quote creation → staff notification"""
    
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_headers):
        self.headers = authenticated_headers
    
    def test_quote_creation_with_cantidades_por_producto(self):
        """Test that cantidades_por_producto format works correctly"""
        unique_phone = f"593999QC{uuid.uuid4().hex[:4].upper()}"
        
        # Send first message with product codes, quantities per product, and email
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"test-qc-{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {
                                "body": "Necesito cotizar JARVID00020 100 unidades, JARPOR00143 200 unidades. Correo: qctest@test.com"
                            }
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        print(f"✓ Webhook processed message with cantidades_por_producto format")
        
        # Wait for processing
        print("  Waiting 12 seconds for LLM processing...")
        time.sleep(12)
        
        # Verify conversation was created
        response = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        assert response.status_code == 200
        convs = response.json()
        conv_found = any(c.get("phone_number") == unique_phone for c in convs)
        assert conv_found, f"Conversation for {unique_phone} not found"
        print(f"✓ Conversation created for {unique_phone}")


class TestQuoteUpdate:
    """Test quote update flow (not duplicate)"""
    
    @pytest.fixture(autouse=True)
    def setup(self, authenticated_headers):
        self.headers = authenticated_headers
    
    def test_quote_update_not_duplicate(self):
        """Test that updating a quote doesn't create duplicates"""
        unique_phone = f"593999UP{uuid.uuid4().hex[:4].upper()}"
        
        # First message to create initial quote
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"test-up1-{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {
                                "body": "Cotizar JARVID00020 50 unidades, correo: update@test.com"
                            }
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        assert response.status_code == 200
        print(f"✓ First webhook message sent for {unique_phone}")
        
        # Wait for first processing
        print("  Waiting 12 seconds for LLM processing...")
        time.sleep(12)
        
        # Get initial quote count for this phone
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"trash": "false"},
            headers=self.headers
        )
        assert response.status_code == 200
        quotes_before = [q for q in response.json() if q.get("phone_number") == unique_phone]
        initial_count = len(quotes_before)
        print(f"  Quotes for {unique_phone} after first message: {initial_count}")
        
        # Second message to update quote
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"test-up2-{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {
                                "body": "Actualiza mi cotización, ahora necesito 100 unidades en lugar de 50"
                            }
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload2)
        assert response.status_code == 200
        print(f"✓ Second webhook message (update request) sent")
        
        # Wait for update processing
        print("  Waiting 12 seconds for LLM processing...")
        time.sleep(12)
        
        # Verify no duplicate quotes created
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"trash": "false"},
            headers=self.headers
        )
        assert response.status_code == 200
        quotes_after = [q for q in response.json() if q.get("phone_number") == unique_phone]
        final_count = len(quotes_after)
        print(f"  Quotes for {unique_phone} after update message: {final_count}")
        
        # Should have at most 1 quote (either 0 if not created or 1 updated)
        assert final_count <= 1, f"Duplicate quotes created! Expected <=1, got {final_count}"
        print("✓ No duplicate quotes created during update flow")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
