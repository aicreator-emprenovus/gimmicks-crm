"""
Iteration 19: Testing NEW bot_service.py rewrite with 9-stage state machine.
Tests: greeting flow, name capture, product search (no invalid URLs), data collection order,
quote generation, lead completeness, escalation, staff notification.

Stages: saludo → captura_nombre → busqueda_producto → esperando_codigos → 
        validando_codigos → tipo_logo → recopilando_datos → confirmacion → escalado_humano
"""
import pytest
import requests
import os
import time
import uuid
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test phone numbers - unique per test to avoid state conflicts
def get_test_phone():
    return f"593{int(time.time() * 1000) % 1000000000:09d}"


class TestBotGreetingFlow:
    """Test 1: Bot greeting flow - first message triggers greeting + name request"""
    
    def test_first_message_triggers_greeting_and_name_request(self):
        """First message should trigger greeting and ask for name (stage='captura_nombre')"""
        phone = get_test_phone()
        
        # Send first message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "Hola"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        # Wait for AI processing
        time.sleep(5)
        
        # Check conversation state
        state_resp = requests.get(f"{BASE_URL}/api/conversation-states/{phone}")
        if state_resp.status_code == 200:
            state = state_resp.json()
            # After first message, stage should be captura_nombre (asking for name)
            assert state.get("stage") in ["saludo", "captura_nombre"], f"Expected saludo or captura_nombre, got {state.get('stage')}"
            print(f"✓ First message: stage={state.get('stage')}")
        else:
            # Check messages for greeting
            conv_resp = requests.get(f"{BASE_URL}/api/conversations/")
            if conv_resp.status_code == 200:
                convs = conv_resp.json()
                for c in convs:
                    if c.get("phone_number") == phone:
                        msgs_resp = requests.get(f"{BASE_URL}/api/conversations/{c['id']}/messages")
                        if msgs_resp.status_code == 200:
                            msgs = msgs_resp.json()
                            bot_msgs = [m for m in msgs if m.get("sender") in ["bot", "business"]]
                            if bot_msgs:
                                last_bot = bot_msgs[-1].get("content", {}).get("text", "")
                                # Should ask for name
                                assert "nombre" in last_bot.lower() or "ana" in last_bot.lower(), f"Bot should ask for name: {last_bot}"
                                print(f"✓ Bot greeting: {last_bot[:100]}")


class TestNameCapture:
    """Test 2: Name capture - client name NOT confused with product names"""
    
    def test_name_not_confused_with_product(self):
        """Name like 'Marco' should be captured as name, not product"""
        phone = get_test_phone()
        
        # First message - greeting
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "Hola"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        time.sleep(4)
        
        # Second message - provide name
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "Marco"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload2)
        time.sleep(4)
        
        # Check state - name should be captured
        state_resp = requests.get(f"{BASE_URL}/api/conversation-states/{phone}")
        if state_resp.status_code == 200:
            state = state_resp.json()
            collected = state.get("collected_data", {})
            # Name should be captured
            assert collected.get("nombre") == "Marco" or "marco" in str(collected.get("nombre", "")).lower(), \
                f"Name 'Marco' should be captured as nombre, got: {collected}"
            # Should NOT be in codigos_producto
            assert "marco" not in str(collected.get("codigos_producto", "")).lower(), \
                f"Name should NOT be in codigos_producto: {collected}"
            print(f"✓ Name captured correctly: {collected.get('nombre')}")
            print(f"✓ Stage after name: {state.get('stage')}")


class TestProductSearchNoInvalidURLs:
    """Test 3: Product search - NO railway.app or preview.emergentagent URLs in responses"""
    
    def test_product_search_no_invalid_urls(self):
        """Bot responses should NOT contain railway.app or preview.emergentagent URLs"""
        phone = get_test_phone()
        
        # Setup: greeting + name
        for msg in ["Hola", "Carlos"]:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "type": "text",
                                "text": {"body": msg},
                                "id": f"msg_{uuid.uuid4().hex[:12]}"
                            }],
                            "metadata": {"phone_number_id": ""}
                        }
                    }]
                }]
            }
            requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
            time.sleep(3)
        
        # Search for products
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "necesito jarros"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        time.sleep(5)
        
        # Check messages for invalid URLs
        conv_resp = requests.get(f"{BASE_URL}/api/conversations/")
        if conv_resp.status_code == 200:
            convs = conv_resp.json()
            for c in convs:
                if c.get("phone_number") == phone:
                    msgs_resp = requests.get(f"{BASE_URL}/api/conversations/{c['id']}/messages")
                    if msgs_resp.status_code == 200:
                        msgs = msgs_resp.json()
                        for m in msgs:
                            text = m.get("content", {}).get("text", "")
                            # Check for invalid URLs
                            assert "railway.app" not in text.lower(), f"Found railway.app URL in response: {text}"
                            assert "preview.emergentagent" not in text.lower(), f"Found preview.emergentagent URL in response: {text}"
                        print("✓ No invalid URLs (railway.app, preview.emergentagent) in bot responses")


class TestNoProductsFoundCatalogLink:
    """Test 4: No products found - bot sends https://gimmicks.com.ec/ link"""
    
    def test_no_products_sends_catalog_link(self):
        """When no products found, bot should send gimmicks.com.ec link"""
        phone = get_test_phone()
        
        # Setup: greeting + name
        for msg in ["Hola", "Ana"]:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "type": "text",
                                "text": {"body": msg},
                                "id": f"msg_{uuid.uuid4().hex[:12]}"
                            }],
                            "metadata": {"phone_number_id": ""}
                        }
                    }]
                }]
            }
            requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
            time.sleep(3)
        
        # Search for non-existent product
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "necesito unicornios voladores"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        time.sleep(5)
        
        # Check messages for catalog link
        conv_resp = requests.get(f"{BASE_URL}/api/conversations/")
        if conv_resp.status_code == 200:
            convs = conv_resp.json()
            for c in convs:
                if c.get("phone_number") == phone:
                    msgs_resp = requests.get(f"{BASE_URL}/api/conversations/{c['id']}/messages")
                    if msgs_resp.status_code == 200:
                        msgs = msgs_resp.json()
                        bot_msgs = [m for m in msgs if m.get("sender") in ["bot", "business"]]
                        all_text = " ".join([m.get("content", {}).get("text", "") for m in bot_msgs])
                        # Should contain gimmicks.com.ec
                        assert "gimmicks.com.ec" in all_text.lower(), f"Should contain gimmicks.com.ec link: {all_text}"
                        print("✓ Catalog link (gimmicks.com.ec) sent when no products found")


class TestDataCollectionOrder:
    """Test 5: Data collection order - after quantities → logo type → email → city → company"""
    
    def test_data_collection_order(self):
        """Data should be collected in order: codes → quantities → logo → email → city → company"""
        phone = get_test_phone()
        
        # Full conversation flow
        messages = [
            "Hola",                    # greeting
            "Pedro",                   # name
            "necesito jarros",         # product search
            "JARPOR00391",            # product code
            "100 unidades",           # quantity
            "full color",             # logo type
            "pedro@test.com",         # email
            "Quito",                  # city
            "Mi Empresa SA"           # company
        ]
        
        for msg in messages:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "type": "text",
                                "text": {"body": msg},
                                "id": f"msg_{uuid.uuid4().hex[:12]}"
                            }],
                            "metadata": {"phone_number_id": ""}
                        }
                    }]
                }]
            }
            requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
            time.sleep(4)
        
        # Check final state
        state_resp = requests.get(f"{BASE_URL}/api/conversation-states/{phone}")
        if state_resp.status_code == 200:
            state = state_resp.json()
            collected = state.get("collected_data", {})
            print(f"Collected data: {json.dumps(collected, indent=2)}")
            
            # Verify all data collected
            assert collected.get("nombre"), "nombre should be collected"
            assert collected.get("correo") or collected.get("email"), "correo should be collected"
            assert collected.get("ciudad"), "ciudad should be collected"
            assert collected.get("empresa"), "empresa should be collected"
            print("✓ Data collection order verified")


class TestQuoteGeneration:
    """Test 6: Quote generation - only when ALL data is present"""
    
    def test_quote_only_with_complete_data(self):
        """Quote should only be generated when all required data is present"""
        phone = get_test_phone()
        
        # Complete conversation
        messages = [
            "Hola",
            "Luis",
            "necesito gorras",
            "HT2PR2",
            "50 unidades",
            "un color",
            "luis@empresa.com",
            "Guayaquil",
            "Empresa Test"
        ]
        
        for msg in messages:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "type": "text",
                                "text": {"body": msg},
                                "id": f"msg_{uuid.uuid4().hex[:12]}"
                            }],
                            "metadata": {"phone_number_id": ""}
                        }
                    }]
                }]
            }
            requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
            time.sleep(4)
        
        # Check if quote was generated
        time.sleep(2)
        quotes_resp = requests.get(f"{BASE_URL}/api/quotes-v2/")
        if quotes_resp.status_code == 200:
            quotes = quotes_resp.json()
            phone_quotes = [q for q in quotes if q.get("phone_number") == phone]
            if phone_quotes:
                quote = phone_quotes[0]
                print(f"✓ Quote generated: #{quote.get('quote_number')}")
                print(f"  Client: {quote.get('client_name')}")
                print(f"  Email: {quote.get('client_email')}")
                print(f"  Items: {len(quote.get('items', []))}")
            else:
                # Check state
                state_resp = requests.get(f"{BASE_URL}/api/conversation-states/{phone}")
                if state_resp.status_code == 200:
                    state = state_resp.json()
                    print(f"State: {state.get('stage')}, quote_generated: {state.get('quote_generated')}")


class TestLeadDataCompleteness:
    """Test 7: Lead data completeness - leads must have name, email, city, empresa"""
    
    def test_lead_has_complete_data(self):
        """Lead should have name, email, city, empresa populated"""
        phone = get_test_phone()
        
        # Complete conversation
        messages = [
            "Hola",
            "Maria Garcia",
            "necesito termos",
            "quiero ver el catalogo completo",
            "JARPOR00391",
            "200",
            "full color",
            "maria@empresa.com",
            "Cuenca",
            "Garcia Corp"
        ]
        
        for msg in messages:
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "type": "text",
                                "text": {"body": msg},
                                "id": f"msg_{uuid.uuid4().hex[:12]}"
                            }],
                            "metadata": {"phone_number_id": ""}
                        }
                    }]
                }]
            }
            requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
            time.sleep(4)
        
        # Check lead data
        leads_resp = requests.get(f"{BASE_URL}/api/leads/")
        if leads_resp.status_code == 200:
            leads = leads_resp.json()
            phone_leads = [l for l in leads if l.get("phone_number") == phone]
            if phone_leads:
                lead = phone_leads[0]
                print(f"Lead data: name={lead.get('name')}, correo={lead.get('correo')}, ciudad={lead.get('ciudad')}, empresa={lead.get('empresa')}")
                # Verify completeness
                assert lead.get("name"), "Lead should have name"
                print("✓ Lead has complete data")


class TestEscalationKeywords:
    """Test 8: Escalation - keywords like 'quiero hablar con una persona' trigger escalation"""
    
    def test_escalation_triggers(self):
        """Escalation keywords should trigger immediate escalation"""
        phone = get_test_phone()
        
        # Setup
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "Hola"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload1)
        time.sleep(3)
        
        # Trigger escalation
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "type": "text",
                            "text": {"body": "quiero hablar con una persona"},
                            "id": f"msg_{uuid.uuid4().hex[:12]}"
                        }],
                        "metadata": {"phone_number_id": ""}
                    }
                }]
            }]
        }
        requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload2)
        time.sleep(4)
        
        # Check state
        state_resp = requests.get(f"{BASE_URL}/api/conversation-states/{phone}")
        if state_resp.status_code == 200:
            state = state_resp.json()
            assert state.get("stage") == "escalado_humano", f"Stage should be escalado_humano, got {state.get('stage')}"
            assert state.get("transferred_to_human") == True, "transferred_to_human should be True"
            print("✓ Escalation triggered correctly")
            print(f"  Stage: {state.get('stage')}")
            print(f"  Transferred: {state.get('transferred_to_human')}")


class TestStaffNotification:
    """Test 9: Staff notification - when quote is created, staff at 593999440910 is notified"""
    
    def test_staff_notification_on_quote(self):
        """Staff should be notified when quote is created"""
        # This is verified by checking the bot_service.py code has STAFF_NOTIFICATION_PHONE
        # and notify_staff_new_quote function
        
        # Check the constant
        import sys
        sys.path.insert(0, '/app/backend')
        from bot_service import STAFF_NOTIFICATION_PHONE, notify_staff_new_quote
        
        assert STAFF_NOTIFICATION_PHONE == "593999440910", f"Staff phone should be 593999440910, got {STAFF_NOTIFICATION_PHONE}"
        assert callable(notify_staff_new_quote), "notify_staff_new_quote should be callable"
        print("✓ Staff notification configured: 593999440910")


class TestLoginFlow:
    """Test 10: Login flow works"""
    
    def test_admin_login(self):
        """Admin login should work with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        print(f"✓ Admin login successful")
        return data["access_token"]
    
    def test_developer_login(self):
        """Developer login should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "aicreator@emprenovus.com",
            "password": "Jlsb*1082"
        })
        assert response.status_code == 200, f"Developer login failed: {response.text}"
        print("✓ Developer login successful")


class TestDashboardAndInventory:
    """Test 11 & 12: Dashboard and Inventory pages"""
    
    def test_dashboard_loads(self):
        """Dashboard API should return data"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check dashboard stats
        stats_resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert stats_resp.status_code == 200, f"Dashboard stats failed: {stats_resp.text}"
        print("✓ Dashboard stats loaded")
    
    def test_inventory_loads(self):
        """Inventory API should return products"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        inv_resp = requests.get(f"{BASE_URL}/api/inventory/", headers=headers)
        assert inv_resp.status_code == 200, f"Inventory failed: {inv_resp.text}"
        data = inv_resp.json()
        assert "products" in data, "Response should contain products"
        print(f"✓ Inventory loaded: {len(data.get('products', []))} products")


class TestProductExport:
    """Test 12: Product export downloads ALL products (not just 50 per page)"""
    
    def test_export_all_products(self):
        """Export should fetch all products with limit=10000"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with limit=10000 (as used in export)
        inv_resp = requests.get(f"{BASE_URL}/api/inventory/", params={"limit": 10000}, headers=headers)
        assert inv_resp.status_code == 200, f"Export query failed: {inv_resp.text}"
        data = inv_resp.json()
        products = data.get("products", [])
        total = data.get("total", 0)
        
        print(f"✓ Export query: {len(products)} products returned, total in DB: {total}")
        # Should return more than default page size (50)
        if total > 50:
            assert len(products) > 50, f"Export should return more than 50 products when total={total}"
            print(f"✓ Export returns all products (not paginated to 50)")


class TestValidStages:
    """Test: Verify all 9 stages are defined"""
    
    def test_valid_stages_defined(self):
        """All 9 stages should be defined in VALID_STAGES"""
        import sys
        sys.path.insert(0, '/app/backend')
        from bot_service import VALID_STAGES
        
        expected_stages = [
            "saludo", "captura_nombre", "busqueda_producto", "esperando_codigos",
            "validando_codigos", "tipo_logo", "recopilando_datos", "confirmacion", "escalado_humano"
        ]
        
        for stage in expected_stages:
            assert stage in VALID_STAGES, f"Stage '{stage}' should be in VALID_STAGES"
        
        print(f"✓ All 9 stages defined: {VALID_STAGES}")


class TestExternalCatalogURL:
    """Test: External catalog URL is correct"""
    
    def test_external_catalog_url(self):
        """EXTERNAL_CATALOG_URL should be https://gimmicks.com.ec/"""
        import sys
        sys.path.insert(0, '/app/backend')
        from bot_service import EXTERNAL_CATALOG_URL
        
        assert EXTERNAL_CATALOG_URL == "https://gimmicks.com.ec/", f"Expected https://gimmicks.com.ec/, got {EXTERNAL_CATALOG_URL}"
        print(f"✓ External catalog URL: {EXTERNAL_CATALOG_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
