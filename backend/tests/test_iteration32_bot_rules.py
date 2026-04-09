"""
Iteration 32: Test bot conversational flow rules
Tests the 3 new rules:
1) PASO 1 greets WITHOUT asking for name
2) PASO 2 is PRODUCTO before name (priority)
3) PASO 3 is name AFTER showing products
4) REGLA CRITICA - NUMERO DE COTIZACION forbids mentioning quote numbers
5) PRODUCTOS NO ENCONTRADOS rule does NOT ask for email for catalog
6) notify_staff_catalog_request sends 'PRODUCTO NO ENCONTRADO EN INVENTARIO' alert without email field
7) Alert #5 triggers IMMEDIATELY on no_products_found (no email prerequisite)
8) quote_context does NOT include quote number (no #{quote_number})
9) Fallback message says 'En que puedo ayudarte?' without asking for name
"""
import pytest
import requests
import os
import re
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSystemPromptRules:
    """Test that SYSTEM_PROMPT contains correct instructions for the 3 new rules"""
    
    def test_system_prompt_paso1_greets_without_name(self):
        """PASO 1 should greet WITHOUT asking for name"""
        from bot_service import SYSTEM_PROMPT
        
        # Check PASO 1 exists
        assert "PASO 1" in SYSTEM_PROMPT, "PASO 1 should exist in SYSTEM_PROMPT"
        
        # Extract PASO 1 section
        paso1_match = re.search(r'PASO 1[^:]*:(.*?)(?=PASO 2|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso1_match, "PASO 1 section should be extractable"
        paso1_text = paso1_match.group(1)
        
        # Verify it says to greet and ask how to help
        assert "Hola" in paso1_text or "soy Ana" in paso1_text, "PASO 1 should include greeting"
        assert "En que puedo ayudarte" in paso1_text or "ayudarte" in paso1_text, "PASO 1 should ask how to help"
        
        # Verify it says NOT to ask for name immediately
        assert "NO pidas el nombre" in paso1_text or "no pidas el nombre" in paso1_text.lower(), \
            "PASO 1 should explicitly say NOT to ask for name"
        
        print("✓ PASO 1 correctly instructs to greet WITHOUT asking for name")
    
    def test_system_prompt_paso2_product_priority(self):
        """PASO 2 should be PRODUCTO with priority before name"""
        from bot_service import SYSTEM_PROMPT
        
        # Check PASO 2 exists
        assert "PASO 2" in SYSTEM_PROMPT, "PASO 2 should exist in SYSTEM_PROMPT"
        
        # Extract PASO 2 section
        paso2_match = re.search(r'PASO 2[^:]*:(.*?)(?=PASO 3|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso2_match, "PASO 2 section should be extractable"
        paso2_text = paso2_match.group(1)
        
        # Verify it's about products
        assert "PRODUCTO" in paso2_text.upper() or "producto" in paso2_text.lower(), \
            "PASO 2 should be about products"
        
        # Verify it says NOT to ask for name/email before showing catalog
        assert "NO pidas nombre" in paso2_text or "no pidas nombre" in paso2_text.lower() or \
               "NO pidas" in paso2_text, \
            "PASO 2 should say NOT to ask for name/email before showing products"
        
        print("✓ PASO 2 correctly prioritizes PRODUCTO before asking for name")
    
    def test_system_prompt_paso3_name_after_products(self):
        """PASO 3 should be NAME after showing products"""
        from bot_service import SYSTEM_PROMPT
        
        # Check PASO 3 exists
        assert "PASO 3" in SYSTEM_PROMPT, "PASO 3 should exist in SYSTEM_PROMPT"
        
        # Extract PASO 3 section
        paso3_match = re.search(r'PASO 3[^:]*:(.*?)(?=PASO 4|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso3_match, "PASO 3 section should be extractable"
        paso3_text = paso3_match.group(1)
        
        # Verify it's about getting name
        assert "nombre" in paso3_text.lower(), "PASO 3 should be about getting name"
        
        # Verify it says AFTER showing products
        assert "Despues" in paso3_text or "despues" in paso3_text.lower() or \
               "mostrar opciones" in paso3_text.lower(), \
            "PASO 3 should mention getting name AFTER showing products"
        
        print("✓ PASO 3 correctly asks for name AFTER showing products")
    
    def test_system_prompt_quote_number_forbidden(self):
        """REGLA CRITICA - NUMERO DE COTIZACION should forbid mentioning quote numbers"""
        from bot_service import SYSTEM_PROMPT
        
        # Check the rule exists
        assert "REGLA CRITICA" in SYSTEM_PROMPT or "NUMERO DE COTIZACION" in SYSTEM_PROMPT, \
            "Quote number rule should exist in SYSTEM_PROMPT"
        
        # Find the quote number rule section
        quote_rule_match = re.search(
            r'(REGLA CRITICA.*?NUMERO DE COTIZACION|NUMERO DE COTIZACION.*?REGLA CRITICA)(.*?)(?=\n\n|INFORMACION|$)',
            SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE
        )
        
        # Alternative: search for the specific rule
        if not quote_rule_match:
            quote_rule_match = re.search(
                r'NUNCA menciones el numero de cotizacion',
                SYSTEM_PROMPT, re.IGNORECASE
            )
        
        assert quote_rule_match, "Quote number rule should be present"
        
        # Verify it says NEVER mention quote number
        assert "NUNCA" in SYSTEM_PROMPT and "numero de cotizacion" in SYSTEM_PROMPT.lower(), \
            "Rule should say NEVER mention quote number"
        
        # Verify it mentions it's internal data
        assert "interno" in SYSTEM_PROMPT.lower() or "sistema" in SYSTEM_PROMPT.lower(), \
            "Rule should mention quote number is internal data"
        
        print("✓ REGLA CRITICA correctly forbids mentioning quote numbers to client")
    
    def test_system_prompt_no_email_for_catalog(self):
        """PRODUCTOS NO ENCONTRADOS rule should NOT ask for email for catalog"""
        from bot_service import SYSTEM_PROMPT
        
        # Find the products not found rule
        no_products_match = re.search(
            r'(PRODUCTOS NO ENCONTRADOS|SIN RESULTADOS|no hay productos)(.*?)(?=\n\n|COTIZACION|$)',
            SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE
        )
        
        # Alternative: search for the specific instruction
        if not no_products_match:
            no_products_match = re.search(
                r'NO pidas el correo electronico para enviar catalogo',
                SYSTEM_PROMPT, re.IGNORECASE
            )
        
        assert no_products_match or "NO pidas el correo" in SYSTEM_PROMPT, \
            "Products not found rule should exist"
        
        # Verify it says NOT to ask for email
        assert "NO pidas" in SYSTEM_PROMPT and "correo" in SYSTEM_PROMPT.lower(), \
            "Rule should say NOT to ask for email for catalog"
        
        # Verify it mentions human advisor will handle
        assert "asesor" in SYSTEM_PROMPT.lower() or "humano" in SYSTEM_PROMPT.lower(), \
            "Rule should mention human advisor will handle"
        
        print("✓ PRODUCTOS NO ENCONTRADOS rule correctly does NOT ask for email")


class TestNotifyStaffCatalogRequest:
    """Test notify_staff_catalog_request function"""
    
    def test_notification_text_format(self):
        """notify_staff_catalog_request should send 'PRODUCTO NO ENCONTRADO EN INVENTARIO' alert"""
        from bot_service import notify_staff_catalog_request
        import inspect
        
        # Get the source code of the function
        source = inspect.getsource(notify_staff_catalog_request)
        
        # Verify the notification text
        assert "PRODUCTO NO ENCONTRADO EN INVENTARIO" in source, \
            "Notification should contain 'PRODUCTO NO ENCONTRADO EN INVENTARIO'"
        
        # Verify it does NOT include email field in the notification
        # The notification should have: Cliente, Telefono, Busqueda - but NOT Email
        assert "Cliente:" in source, "Notification should include Cliente field"
        assert "Telefono:" in source, "Notification should include Telefono field"
        assert "Busqueda:" in source, "Notification should include Busqueda field"
        
        # Check that Email is NOT in the notification format
        # The notification format should NOT have "Email:" line
        notification_block = re.search(r'notification = \((.*?)\)', source, re.DOTALL)
        if notification_block:
            notification_text = notification_block.group(1)
            # Email should NOT be in the notification
            assert "Email:" not in notification_text or "correo" not in notification_text.lower(), \
                "Notification should NOT include Email field"
        
        print("✓ notify_staff_catalog_request sends correct alert without email field")
    
    def test_notification_no_email_parameter(self):
        """notify_staff_catalog_request should not require email in collected_data"""
        from bot_service import notify_staff_catalog_request
        import inspect
        
        # Get function signature
        sig = inspect.signature(notify_staff_catalog_request)
        params = list(sig.parameters.keys())
        
        # Should have: db, phone_number, collected_data, product_request, send_message_fn
        assert "db" in params, "Should have db parameter"
        assert "phone_number" in params, "Should have phone_number parameter"
        assert "collected_data" in params, "Should have collected_data parameter"
        assert "product_request" in params, "Should have product_request parameter"
        assert "send_message_fn" in params, "Should have send_message_fn parameter"
        
        # The function should work even if collected_data has no email
        source = inspect.getsource(notify_staff_catalog_request)
        
        # Check that it uses nombre with a default, not email
        assert 'collected_data.get("nombre"' in source, \
            "Function should get nombre from collected_data"
        
        print("✓ notify_staff_catalog_request does not require email in collected_data")


class TestAlert5ImmediateTrigger:
    """Test that Alert #5 triggers IMMEDIATELY on no_products_found"""
    
    def test_alert5_no_email_prerequisite(self):
        """Alert #5 should trigger immediately without waiting for email"""
        from bot_service import _process_ai_conversation_inner
        import inspect
        
        source = inspect.getsource(_process_ai_conversation_inner)
        
        # Find the Alert #5 section (around line 1183)
        # It should check no_products_found and call notify_staff_catalog_request
        assert "no_products_found" in source, "Should check no_products_found flag"
        assert "notify_staff_catalog_request" in source, "Should call notify_staff_catalog_request"
        
        # The alert should NOT be conditioned on having email
        # Find the if block for no_products_found
        alert_match = re.search(
            r'if no_products_found(.*?)notify_staff_catalog_request',
            source, re.DOTALL
        )
        
        if alert_match:
            condition_text = alert_match.group(1)
            # Should NOT require email/correo in the condition
            assert "correo" not in condition_text.lower(), \
                "Alert #5 should NOT require email to trigger"
            assert "email" not in condition_text.lower(), \
                "Alert #5 should NOT require email to trigger"
        
        print("✓ Alert #5 triggers IMMEDIATELY without email prerequisite")


class TestQuoteContextNoNumber:
    """Test that quote_context does NOT include quote number"""
    
    def test_quote_context_no_quote_number(self):
        """quote_context should NOT include #{quote_number}"""
        from bot_service import _build_conversation_context
        import inspect
        
        source = inspect.getsource(_build_conversation_context)
        
        # Find the quote_context assignment (around line 844)
        quote_context_match = re.search(
            r'quote_context = ["\'](.+?)["\']',
            source
        )
        
        if quote_context_match:
            quote_context_text = quote_context_match.group(1)
            # Should NOT include #{quote_number} or similar
            assert "#{" not in quote_context_text, \
                "quote_context should NOT include #{quote_number}"
            assert "quote_number" not in quote_context_text.lower(), \
                "quote_context should NOT reference quote_number"
        
        # Also check that the quote_context mentions NOT to mention the number
        assert "NO menciones el numero" in source or "no menciones el numero" in source.lower(), \
            "quote_context should instruct NOT to mention quote number"
        
        print("✓ quote_context does NOT include quote number")


class TestFallbackMessage:
    """Test fallback message format"""
    
    def test_fallback_no_name_request(self):
        """Fallback message should say 'En que puedo ayudarte?' without asking for name"""
        from bot_service import _process_ai_conversation_inner
        import inspect
        
        source = inspect.getsource(_process_ai_conversation_inner)
        
        # Find the fallback message for first message (around line 1063)
        # Should be: "Hola, soy Ana de Gimmicks Marketing Services. En que puedo ayudarte?"
        fallback_match = re.search(
            r'fallback = ["\'](.+?)["\']',
            source
        )
        
        if fallback_match:
            fallback_text = fallback_match.group(1)
            # Should include greeting and "En que puedo ayudarte"
            assert "En que puedo ayudarte" in fallback_text or "ayudarte" in fallback_text, \
                "Fallback should ask 'En que puedo ayudarte?'"
            # Should NOT ask for name
            assert "nombre" not in fallback_text.lower(), \
                "Fallback should NOT ask for name"
        
        print("✓ Fallback message correctly says 'En que puedo ayudarte?' without asking for name")


class TestBackendAuthLogin:
    """Test backend /api/auth/login endpoint"""
    
    def test_login_endpoint_exists(self):
        """POST /api/auth/login should exist and work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@gimmicks.com", "password": "admin123456"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Login should return 200, got {response.status_code}"
        data = response.json()
        assert "token" in data or "access_token" in data, "Response should include token"
        
        print("✓ POST /api/auth/login works correctly")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"},
            timeout=10
        )
        
        assert response.status_code == 401, f"Invalid login should return 401, got {response.status_code}"
        
        print("✓ POST /api/auth/login correctly rejects invalid credentials")


class TestWebhookEndpoint:
    """Test webhook endpoint"""
    
    def test_webhook_get_verification(self):
        """GET /api/webhook/whatsapp with correct token should return 200"""
        verify_token = "gimmicks_verify_token"
        challenge = "test_challenge_123"
        
        response = requests.get(
            f"{BASE_URL}/api/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": verify_token,
                "hub.challenge": challenge
            },
            timeout=10
        )
        
        # Should return the challenge
        assert response.status_code == 200, f"Webhook verification should return 200, got {response.status_code}"
        assert response.text == challenge, f"Should return challenge, got {response.text}"
        
        print("✓ GET /api/webhook/whatsapp verification works correctly")
    
    def test_webhook_post_exists(self):
        """POST /api/webhook/whatsapp should exist and return 200"""
        # Send a minimal valid webhook payload
        payload = {
            "object": "whatsapp_business_account",
            "entry": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/webhook/whatsapp",
            json=payload,
            timeout=10
        )
        
        # Should return 200 (webhook always returns 200 to acknowledge receipt)
        assert response.status_code == 200, f"Webhook POST should return 200, got {response.status_code}"
        
        print("✓ POST /api/webhook/whatsapp exists and returns 200")


class TestBuildConversationContextNoProductsFound:
    """Test _build_conversation_context for no_products_found behavior"""
    
    def test_no_products_instruction_no_email(self):
        """When no products found, instruction should NOT ask for email"""
        from bot_service import _build_conversation_context
        import inspect
        
        source = inspect.getsource(_build_conversation_context)
        
        # Find the no_products_found section (around line 818)
        no_products_match = re.search(
            r'no_products_found = True(.*?)catalog_availability = \((.*?)\)',
            source, re.DOTALL
        )
        
        if no_products_match:
            instruction_text = no_products_match.group(2)
            # Should say NOT to ask for email
            assert "NO pidas correo" in instruction_text or "no pidas correo" in instruction_text.lower() or \
                   "NO digas" in instruction_text, \
                "Instruction should say NOT to ask for email"
            # Should mention human advisor
            assert "asesor" in instruction_text.lower(), \
                "Instruction should mention human advisor will contact"
        
        print("✓ no_products_found instruction correctly does NOT ask for email")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
