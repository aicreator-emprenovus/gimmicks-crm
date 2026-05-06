"""
Iteration 24: Catalog URL in Bot Response Tests

Tests the fix where the bot shares the catalog PDF URL directly in the text message
instead of attempting to attach a document via WhatsApp API.

Features tested:
1. POST /api/webhook/whatsapp - When user asks for 'catalogo completo', bot response contains catalog PDF URL
2. POST /api/webhook/whatsapp - Bot should NOT attempt to attach document (no send_document_fn calls)
3. POST /api/webhook/whatsapp - Bot response should NOT contain 'gimmicks.com.ec' URL
4. GET /api/catalog/pdf - Should return 200 with PDF content
5. POST /api/webhook/whatsapp - Normal product search should NOT include catalog URL in response
6. Verify catalog_config exists in MongoDB with a valid filename
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://webhook-routing-2.preview.emergentagent.com').rstrip('/')
WHATSAPP_PHONE_NUMBER_ID = "965777766626628"


class TestCatalogConfig:
    """Test catalog configuration in MongoDB"""
    
    def test_catalog_pdf_endpoint_returns_200(self):
        """GET /api/catalog/pdf should return 200 with PDF content"""
        response = requests.get(f"{BASE_URL}/api/catalog/pdf", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), \
            f"Expected PDF content-type, got {response.headers.get('Content-Type')}"
        assert len(response.content) > 1000, "PDF content seems too small"
        print(f"✓ GET /api/catalog/pdf returns 200 with PDF ({len(response.content)} bytes)")
    
    def test_catalog_info_endpoint(self):
        """GET /api/catalog/info should return catalog metadata (requires auth)"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        
        # Get catalog info
        response = requests.get(
            f"{BASE_URL}/api/catalog/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("has_catalog") == True, "Expected has_catalog=True"
        assert data.get("original_name"), "Expected original_name in response"
        print(f"✓ GET /api/catalog/info returns has_catalog=True, original_name={data.get('original_name')}")


class TestWebhookCatalogRequest:
    """Test webhook behavior when user requests catalog"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Generate unique test phone number for each test"""
        self.test_phone = f"593999{uuid.uuid4().hex[:6]}"
        yield
        # Cleanup is handled by the test itself
    
    def _send_webhook_message(self, phone_number: str, message_text: str):
        """Helper to send a webhook message simulating WhatsApp"""
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test_entry",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551234567",
                            "phone_number_id": WHATSAPP_PHONE_NUMBER_ID
                        },
                        "contacts": [{
                            "profile": {"name": "Test User"},
                            "wa_id": phone_number
                        }],
                        "messages": [{
                            "from": phone_number,
                            "id": f"wamid.{uuid.uuid4().hex}",
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": message_text}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/webhook/whatsapp",
            json=webhook_payload,
            timeout=30
        )
        return response
    
    def _get_bot_response(self, phone_number: str, wait_seconds: int = 12):
        """Helper to get the bot's response from messages collection"""
        # Login to get auth token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = login_response.json().get("access_token")
        
        # Wait for bot to process (GPT-5.2 takes ~8-10 seconds)
        time.sleep(wait_seconds)
        
        # Get conversations to find the one for this phone
        conv_response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers={"Authorization": f"Bearer {token}"}
        )
        conversations = conv_response.json()
        
        # Find conversation for this phone number
        conv = None
        for c in conversations:
            if c.get("phone_number") == phone_number:
                conv = c
                break
        
        if not conv:
            return None, None
        
        # Get messages for this conversation
        msg_response = requests.get(
            f"{BASE_URL}/api/conversations/{conv['id']}/messages",
            headers={"Authorization": f"Bearer {token}"}
        )
        messages = msg_response.json()
        
        # Find the bot's response (sender != 'user')
        bot_messages = [m for m in messages if m.get("sender") in ("bot", "business")]
        
        return bot_messages, conv
    
    def _cleanup_test_data(self, phone_number: str):
        """Clean up test conversation and lead"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = login_response.json().get("access_token")
        
        # Get and delete conversation
        conv_response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers={"Authorization": f"Bearer {token}"}
        )
        for conv in conv_response.json():
            if conv.get("phone_number") == phone_number:
                requests.delete(
                    f"{BASE_URL}/api/conversations/{conv['id']}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                break
        
        # Get and delete lead
        leads_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        for lead in leads_response.json():
            if lead.get("phone_number") == phone_number:
                requests.delete(
                    f"{BASE_URL}/api/leads/{lead['id']}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                break
    
    def test_catalog_completo_request_contains_url(self):
        """When user asks for 'catalogo completo', bot response should contain catalog PDF URL"""
        test_phone = f"593999{uuid.uuid4().hex[:6]}"
        
        try:
            # First message - greeting
            response = self._send_webhook_message(test_phone, "Hola")
            assert response.status_code == 200, f"Webhook failed: {response.text}"
            
            # Wait for bot to respond
            time.sleep(10)
            
            # Second message - provide name
            response = self._send_webhook_message(test_phone, "Juan Test")
            assert response.status_code == 200
            
            # Wait for bot to respond
            time.sleep(10)
            
            # Third message - request full catalog
            response = self._send_webhook_message(test_phone, "quiero ver el catalogo completo")
            assert response.status_code == 200
            
            # Wait longer for catalog request processing
            bot_messages, conv = self._get_bot_response(test_phone, wait_seconds=15)
            
            assert bot_messages, f"No bot messages found for {test_phone}"
            
            # Get the last bot message (response to catalog request)
            last_bot_msg = bot_messages[-1]
            response_text = last_bot_msg.get("content", {}).get("text", "")
            
            print(f"Bot response to 'catalogo completo': {response_text[:200]}...")
            
            # Check that response contains the catalog PDF URL
            expected_url_pattern = "/api/catalog/pdf"
            assert expected_url_pattern in response_text, \
                f"Expected catalog URL ({expected_url_pattern}) in response, got: {response_text}"
            
            # Check that response does NOT contain gimmicks.com.ec
            assert "gimmicks.com.ec" not in response_text.lower(), \
                f"Response should NOT contain gimmicks.com.ec, got: {response_text}"
            
            print(f"✓ Bot response contains catalog URL ending in /api/catalog/pdf")
            print(f"✓ Bot response does NOT contain gimmicks.com.ec")
            
        finally:
            self._cleanup_test_data(test_phone)
    
    def test_webhook_returns_ok_status(self):
        """POST /api/webhook/whatsapp should return status ok"""
        test_phone = f"593999{uuid.uuid4().hex[:6]}"
        
        try:
            response = self._send_webhook_message(test_phone, "Hola")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert data.get("status") == "ok", f"Expected status=ok, got {data}"
            print(f"✓ POST /api/webhook/whatsapp returns status=ok")
        finally:
            # Wait a bit then cleanup
            time.sleep(5)
            self._cleanup_test_data(test_phone)
    
    def test_normal_product_search_no_catalog_url(self):
        """Normal product search should NOT include catalog URL in response"""
        test_phone = f"593999{uuid.uuid4().hex[:6]}"
        
        try:
            # First message - greeting
            response = self._send_webhook_message(test_phone, "Hola")
            assert response.status_code == 200
            time.sleep(10)
            
            # Second message - provide name
            response = self._send_webhook_message(test_phone, "Maria Test")
            assert response.status_code == 200
            time.sleep(10)
            
            # Third message - search for a common product (gorras)
            response = self._send_webhook_message(test_phone, "necesito gorras")
            assert response.status_code == 200
            
            # Wait for bot to respond
            bot_messages, conv = self._get_bot_response(test_phone, wait_seconds=15)
            
            assert bot_messages, f"No bot messages found for {test_phone}"
            
            # Get the last bot message
            last_bot_msg = bot_messages[-1]
            response_text = last_bot_msg.get("content", {}).get("text", "")
            
            print(f"Bot response to 'necesito gorras': {response_text[:200]}...")
            
            # If products were found, response should NOT contain catalog URL
            # (catalog URL is only added when no products found OR explicit catalog request)
            if "GORRA" in response_text.upper() or "codigo" in response_text.lower():
                # Products were found - should NOT have catalog URL
                assert "/api/catalog/pdf" not in response_text, \
                    f"Product search response should NOT contain catalog URL when products found: {response_text}"
                print(f"✓ Normal product search (with results) does NOT include catalog URL")
            else:
                # No products found - catalog URL is acceptable
                print(f"✓ No products found for 'gorras', catalog URL may be included (acceptable)")
            
        finally:
            self._cleanup_test_data(test_phone)


class TestBotCodeVerification:
    """Verify bot code doesn't use document attachment"""
    
    def test_bot_service_no_send_document_call(self):
        """Verify bot_service.py doesn't call send_document_fn for catalog"""
        import subprocess
        
        # Check if send_document or send_whatsapp_document is called in bot_service.py
        result = subprocess.run(
            ["grep", "-n", "send_document", "/app/backend/bot_service.py"],
            capture_output=True,
            text=True
        )
        
        # Should not find any send_document calls
        if result.stdout.strip():
            # If found, check it's not actually being called (might be commented or in a different context)
            lines = result.stdout.strip().split('\n')
            active_calls = [l for l in lines if not l.strip().startswith('#')]
            assert len(active_calls) == 0, \
                f"Found send_document calls in bot_service.py: {active_calls}"
        
        print(f"✓ bot_service.py does NOT call send_document_fn")
    
    def test_bot_service_uses_url_append(self):
        """Verify bot_service.py appends URL to text instead of document attachment"""
        import subprocess
        
        # Check for URL append logic
        result = subprocess.run(
            ["grep", "-n", "catalog_pdf_url_to_append", "/app/backend/bot_service.py"],
            capture_output=True,
            text=True
        )
        
        assert result.stdout.strip(), "Expected catalog_pdf_url_to_append logic in bot_service.py"
        print(f"✓ bot_service.py uses URL append logic (catalog_pdf_url_to_append)")
    
    def test_system_prompt_forbids_external_urls(self):
        """Verify system prompt forbids mentioning gimmicks.com.ec"""
        import subprocess
        
        # Check system prompt for prohibition
        result = subprocess.run(
            ["grep", "-n", "gimmicks.com.ec", "/app/backend/bot_service.py"],
            capture_output=True,
            text=True
        )
        
        assert result.stdout.strip(), "Expected gimmicks.com.ec mention in bot_service.py"
        
        # Verify it's in a prohibition context
        assert "NUNCA" in result.stdout or "NO" in result.stdout or "inventes" in result.stdout.lower(), \
            f"Expected prohibition context for gimmicks.com.ec: {result.stdout}"
        
        print(f"✓ System prompt forbids mentioning gimmicks.com.ec")
    
    def test_get_catalog_pdf_url_function_exists(self):
        """Verify get_catalog_pdf_url helper function exists and uses env vars"""
        import subprocess
        
        # Check for function definition
        result = subprocess.run(
            ["grep", "-n", "async def get_catalog_pdf_url", "/app/backend/bot_service.py"],
            capture_output=True,
            text=True
        )
        
        assert result.stdout.strip(), "Expected get_catalog_pdf_url function in bot_service.py"
        
        # Check it uses CATALOG_BASE_URL
        result2 = subprocess.run(
            ["grep", "-n", "CATALOG_BASE_URL", "/app/backend/bot_service.py"],
            capture_output=True,
            text=True
        )
        
        assert result2.stdout.strip(), "Expected CATALOG_BASE_URL usage in get_catalog_pdf_url"
        
        print(f"✓ get_catalog_pdf_url function exists and uses CATALOG_BASE_URL env var")


class TestCatalogURLFormat:
    """Test the format of catalog URL in responses"""
    
    def test_catalog_url_is_valid(self):
        """Verify the catalog URL format is correct"""
        # The URL should be BASE_URL + /api/catalog/pdf
        expected_url = f"{BASE_URL}/api/catalog/pdf"
        
        # Verify the URL is accessible
        response = requests.get(expected_url, timeout=30)
        assert response.status_code == 200, f"Catalog URL {expected_url} returned {response.status_code}"
        
        print(f"✓ Catalog URL format is valid: {expected_url}")
    
    def test_catalog_url_in_env(self):
        """Verify CATALOG_BASE_URL is set in backend .env"""
        import subprocess
        
        result = subprocess.run(
            ["grep", "CATALOG_BASE_URL", "/app/backend/.env"],
            capture_output=True,
            text=True
        )
        
        assert result.stdout.strip(), "Expected CATALOG_BASE_URL in backend .env"
        assert "preview.emergentagent.com" in result.stdout or "localhost" in result.stdout, \
            f"CATALOG_BASE_URL should point to valid domain: {result.stdout}"
        
        print(f"✓ CATALOG_BASE_URL is set in backend .env")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
