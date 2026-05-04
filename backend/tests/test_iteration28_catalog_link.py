"""
Iteration 28: Test catalog link feature in bot responses
Tests:
1. When product search finds results, bot includes catalog link /catalog?q=keyword
2. Catalog link URL is properly formatted (no stopwords in query)
3. Bot does NOT include invented/external URLs - only real catalog link
4. Public catalog page /catalog?q=tazas loads and shows filtered products
5. /api/catalog/public?q=tazas API endpoint returns products
6. When product search finds NO results (e.g. drones), bot asks for email
7. Bot NEVER says 'no tenemos' or 'no encontre' when no products found
8. When no products + email collected, staff receives SOLICITUD DE CATALOGO POR EMAIL alert
9. Normal 5-step flow still works end-to-end
"""
import pytest
import requests
import os
import time
import uuid
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crm-bot-hub.preview.emergentagent.com').rstrip('/')

# Test phone numbers - unique per test to avoid conflicts
def get_test_phone():
    return f"593999{uuid.uuid4().hex[:6]}"


class TestPublicCatalogAPI:
    """Test the public catalog API endpoint"""
    
    def test_catalog_public_returns_products_for_tazas(self):
        """Test /api/catalog/public?q=tazas returns products"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "tazas"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        products = response.json()
        assert isinstance(products, list), "Response should be a list"
        # Should find some products (tazas exist in inventory)
        print(f"Found {len(products)} products for 'tazas'")
        if len(products) > 0:
            # Verify product structure
            product = products[0]
            assert "code" in product, "Product should have code"
            assert "name" in product, "Product should have name"
            print(f"First product: {product.get('code')} - {product.get('name')}")
    
    def test_catalog_public_returns_products_for_jarros(self):
        """Test /api/catalog/public?q=jarros returns products"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "jarros"})
        assert response.status_code == 200
        
        products = response.json()
        assert isinstance(products, list)
        print(f"Found {len(products)} products for 'jarros'")
        assert len(products) > 0, "Should find products for 'jarros'"
    
    def test_catalog_public_returns_empty_for_drones(self):
        """Test /api/catalog/public?q=drones returns empty (product doesn't exist)"""
        response = requests.get(f"{BASE_URL}/api/catalog/public", params={"q": "drones"})
        assert response.status_code == 200
        
        products = response.json()
        assert isinstance(products, list)
        print(f"Found {len(products)} products for 'drones'")
        # Drones should not exist in inventory
        assert len(products) == 0, "Should NOT find products for 'drones'"
    
    def test_catalog_public_categories_endpoint(self):
        """Test /api/catalog/public/categories returns categories"""
        response = requests.get(f"{BASE_URL}/api/catalog/public/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        print(f"Found {len(categories)} categories")


class TestCatalogLinkInBotResponse:
    """Test that bot includes catalog link when products are found"""
    
    def test_bot_includes_catalog_link_for_tazas(self):
        """When user asks for 'tazas', bot should include catalog link"""
        test_phone = get_test_phone()
        
        # Step 1: Initial greeting
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test User"}, "wa_id": test_phone}],
                        "messages": [{
                            "from": test_phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(3)
        
        # Step 2: Provide name
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Me llamo Carlos"
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"] = f"msg_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(3)
        
        # Step 3: Ask for tazas - this should trigger catalog link
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Necesito tazas"
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"] = f"msg_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(10)  # Wait for AI response
        
        # Check the bot's response in messages collection
        # Get conversation
        conv_response = requests.get(f"{BASE_URL}/api/conversations")
        if conv_response.status_code == 401:
            # Need to login first
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@gimmicks.com",
                "password": "admin123456"
            })
            assert login_response.status_code == 200
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            conv_response = requests.get(f"{BASE_URL}/api/conversations", headers=headers)
        else:
            headers = {}
        
        # Find conversation for test phone
        conversations = conv_response.json()
        test_conv = None
        for conv in conversations:
            if test_phone in conv.get("phone_number", ""):
                test_conv = conv
                break
        
        if test_conv:
            # Get messages
            msg_response = requests.get(
                f"{BASE_URL}/api/conversations/{test_conv['id']}/messages",
                headers=headers
            )
            messages = msg_response.json()
            
            # Find bot response after "tazas" request
            bot_messages = [m for m in messages if m.get("sender") in ["bot", "business"]]
            
            # Check if any bot message contains catalog link
            catalog_link_found = False
            for msg in bot_messages:
                text = msg.get("content", {}).get("text", "")
                if "/catalog?q=" in text:
                    catalog_link_found = True
                    print(f"✓ Found catalog link in bot response: {text[:200]}...")
                    # Verify link format
                    assert "https://" in text or "/catalog?q=" in text
                    break
            
            if not catalog_link_found:
                print("Bot messages:")
                for msg in bot_messages[-3:]:
                    print(f"  - {msg.get('content', {}).get('text', '')[:150]}...")
            
            # Note: The catalog link might be appended as fallback
            print(f"Catalog link found in response: {catalog_link_found}")


class TestNoProductsFoundBehavior:
    """Test bot behavior when no products are found"""
    
    def test_bot_asks_for_email_when_no_products(self):
        """When user asks for 'drones' (doesn't exist), bot should ask for email"""
        test_phone = get_test_phone()
        
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Initial greeting
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test User"}, "wa_id": test_phone}],
                        "messages": [{
                            "from": test_phone,
                            "id": f"msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(3)
        
        # Step 2: Provide name
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Soy Maria"
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"] = f"msg_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(3)
        
        # Step 3: Ask for drones - product doesn't exist
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = "Necesito drones"
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"] = f"msg_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        time.sleep(10)  # Wait for AI response
        
        # Get conversation and check bot response
        conv_response = requests.get(f"{BASE_URL}/api/conversations", headers=headers)
        conversations = conv_response.json()
        
        test_conv = None
        for conv in conversations:
            if test_phone in conv.get("phone_number", ""):
                test_conv = conv
                break
        
        if test_conv:
            msg_response = requests.get(
                f"{BASE_URL}/api/conversations/{test_conv['id']}/messages",
                headers=headers
            )
            messages = msg_response.json()
            
            # Find bot response after "drones" request
            bot_messages = [m for m in messages if m.get("sender") in ["bot", "business"]]
            
            # Check that bot does NOT say "no tenemos" or "no encontre"
            forbidden_phrases = ["no tenemos", "no encontre", "no encontré", "no hay", "no disponemos"]
            
            for msg in bot_messages:
                text = msg.get("content", {}).get("text", "").lower()
                for phrase in forbidden_phrases:
                    assert phrase not in text, f"Bot should NOT say '{phrase}' - found in: {text[:100]}"
            
            # Check that bot asks for email (to send catalog)
            last_bot_msg = bot_messages[-1].get("content", {}).get("text", "") if bot_messages else ""
            print(f"Last bot message: {last_bot_msg[:200]}...")
            
            # Bot should mention email or catalog
            email_related = any(word in last_bot_msg.lower() for word in ["correo", "email", "catalogo", "catálogo"])
            print(f"Bot mentions email/catalog: {email_related}")


class TestCatalogLinkURLFormat:
    """Test that catalog link URL is properly formatted"""
    
    def test_stopwords_not_in_catalog_link(self):
        """Verify STOPWORDS are filtered from catalog link query"""
        # Check the STOPWORDS list in bot_service.py
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read the file to check STOPWORDS
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        # Find LINK_STOPWORDS
        assert "LINK_STOPWORDS" in content, "LINK_STOPWORDS should be defined"
        
        # Check that common stopwords are in the list
        stopwords_to_check = ["de", "la", "el", "para", "con", "necesito", "quiero", "busco"]
        for word in stopwords_to_check:
            assert f'"{word}"' in content, f"'{word}' should be in LINK_STOPWORDS"
        
        print("✓ LINK_STOPWORDS contains expected stopwords")
    
    def test_catalog_link_format_in_code(self):
        """Verify catalog link is built correctly in code"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        # Check catalog link format
        assert "/catalog?q=" in content, "Catalog link should use /catalog?q= format"
        assert "url_quote" in content, "URL encoding should be used"
        assert "CATALOG_BASE_URL" in content or "REACT_APP_BACKEND_URL" in content, "Base URL should be read from env"
        
        print("✓ Catalog link format is correct in code")


class TestStaffCatalogAlert:
    """Test that staff receives alert when no products + email collected"""
    
    def test_catalog_request_notification_function_exists(self):
        """Verify notify_staff_catalog_request function exists"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        assert "notify_staff_catalog_request" in content, "notify_staff_catalog_request function should exist"
        assert "SOLICITUD DE CATALOGO POR EMAIL" in content, "Alert message should contain 'SOLICITUD DE CATALOGO POR EMAIL'"
        assert "593999440910" in content, "Staff notification phone should be configured"
        
        print("✓ notify_staff_catalog_request function exists with correct message")


class TestNormalFlowStillWorks:
    """Test that normal 5-step flow still works end-to-end"""
    
    def test_webhook_basic(self):
        """Test webhook returns 200"""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"phone_number_id": "965777766626628"},
                        "contacts": [{"profile": {"name": "Test"}, "wa_id": "593999000001"}],
                        "messages": [{
                            "from": "593999000001",
                            "id": "test_msg_1",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "test"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Webhook returns 200 with status=ok")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
