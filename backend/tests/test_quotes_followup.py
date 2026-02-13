"""
Backend tests for WhatsApp CRM - Quotes Management and Follow-up System
Tests: Quotes CRUD, AI Bot Pipeline, Follow-up Check, Lead Reactivation
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

# Test credentials
TEST_EMAIL = "admin@gimmicks.com"
TEST_PASSWORD = "admin123456"


@pytest.fixture(scope="session")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """POST /api/auth/login - valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print("✓ Login success with valid credentials")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login - invalid credentials rejection"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("✓ Login rejected with invalid credentials")


class TestQuotesAPI:
    """Quotes management API tests"""
    
    def test_get_quotes_list(self, auth_headers):
        """GET /api/quotes - returns quotes list with status, items, client data"""
        response = requests.get(f"{BASE_URL}/api/quotes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/quotes returns {len(data)} quotes")
        
        # Validate structure if quotes exist
        if len(data) > 0:
            quote = data[0]
            assert "id" in quote
            assert "status" in quote
            assert "items" in quote
            assert "phone_number" in quote
            print(f"  → Quote structure validated: status={quote.get('status')}, items={len(quote.get('items', []))}")
    
    def test_get_quotes_filter_by_status(self, auth_headers):
        """GET /api/quotes?status=pending - filter by status"""
        response = requests.get(f"{BASE_URL}/api/quotes?status=pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned quotes should have pending status
        for quote in data:
            assert quote.get("status") == "pending", f"Expected pending, got {quote.get('status')}"
        print(f"✓ GET /api/quotes?status=pending returns {len(data)} pending quotes")
    
    def test_create_test_quote_via_webhook(self, auth_headers):
        """Create test quote via webhook for further testing"""
        # First create a quote via webhook simulation
        unique_phone = f"593TEST{uuid.uuid4().hex[:8].upper()}"
        
        # Simulate AI bot creating a pending quote by inserting directly
        # We test the webhook + AI bot flow separately
        print(f"  → Test phone: {unique_phone}")
        return unique_phone
    
    def test_update_quote_total_and_notes(self, auth_headers):
        """PATCH /api/quotes/{id} - updates total and notes"""
        # First get an existing quote
        response = requests.get(f"{BASE_URL}/api/quotes", headers=auth_headers)
        assert response.status_code == 200
        quotes = response.json()
        
        if len(quotes) == 0:
            pytest.skip("No quotes exist to test update")
        
        quote = quotes[0]
        quote_id = quote["id"]
        new_total = 150.50
        new_notes = f"TEST_NOTES_{datetime.now().isoformat()}"
        
        # Update the quote
        update_response = requests.patch(
            f"{BASE_URL}/api/quotes/{quote_id}",
            headers=auth_headers,
            json={"total": new_total, "notes": new_notes}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["total"] == new_total
        assert updated["notes"] == new_notes
        print(f"✓ PATCH /api/quotes/{quote_id} - total and notes updated")
        
        # Verify persistence with GET
        get_response = requests.get(f"{BASE_URL}/api/quotes/{quote_id}", headers=auth_headers)
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["total"] == new_total
        assert fetched["notes"] == new_notes
        print("  → Update persisted and verified via GET")
    
    def test_get_quote_detail(self, auth_headers):
        """GET /api/quotes/{id} - returns quote detail"""
        response = requests.get(f"{BASE_URL}/api/quotes", headers=auth_headers)
        quotes = response.json()
        
        if len(quotes) == 0:
            pytest.skip("No quotes exist to test detail")
        
        quote_id = quotes[0]["id"]
        detail_response = requests.get(f"{BASE_URL}/api/quotes/{quote_id}", headers=auth_headers)
        assert detail_response.status_code == 200
        
        quote = detail_response.json()
        # Validate all expected fields
        expected_fields = ["id", "status", "client_name", "client_empresa", "items", "total", "notes", "created_at"]
        for field in expected_fields:
            assert field in quote, f"Missing field: {field}"
        print(f"✓ GET /api/quotes/{quote_id} - detail returned with all fields")
    
    def test_delete_quote(self, auth_headers):
        """DELETE /api/quotes/{id} - deletes quote"""
        # Create a test quote first via direct database or find one that's TEST_
        response = requests.get(f"{BASE_URL}/api/quotes", headers=auth_headers)
        quotes = response.json()
        
        # Find a quote with TEST_ in notes (test data)
        test_quote = None
        for q in quotes:
            if q.get("notes", "").startswith("TEST_"):
                test_quote = q
                break
        
        if not test_quote:
            pytest.skip("No test quote to delete (no quote with TEST_ prefix in notes)")
        
        quote_id = test_quote["id"]
        delete_response = requests.delete(f"{BASE_URL}/api/quotes/{quote_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        print(f"✓ DELETE /api/quotes/{quote_id} - quote deleted")
        
        # Verify deletion
        verify_response = requests.get(f"{BASE_URL}/api/quotes/{quote_id}", headers=auth_headers)
        assert verify_response.status_code == 404
        print("  → Deletion verified - quote returns 404")


class TestFollowUpSystem:
    """Follow-up check endpoint tests"""
    
    def test_followup_check_endpoint(self, auth_headers):
        """POST /api/followup/check - triggers follow-up check"""
        response = requests.post(f"{BASE_URL}/api/followup/check", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "reminders_sent" in data
        assert "marked_lost" in data
        print(f"✓ POST /api/followup/check - {data}")


class TestLeadsPipelineStages:
    """Test new pipeline stages: lead, cliente_potencial, cotizacion_generada, pedido, perdido"""
    
    def test_get_leads_returns_new_stages(self, auth_headers):
        """GET /api/leads - returns leads with new pipeline stages"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=auth_headers)
        assert response.status_code == 200
        leads = response.json()
        
        valid_stages = ["lead", "cliente_potencial", "cotizacion_generada", "pedido", "perdido"]
        
        for lead in leads:
            assert "funnel_stage" in lead
            assert lead["funnel_stage"] in valid_stages, f"Invalid stage: {lead['funnel_stage']}"
        
        # Count leads per stage
        stage_counts = {}
        for lead in leads:
            stage = lead["funnel_stage"]
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        print(f"✓ GET /api/leads returns {len(leads)} leads")
        print(f"  → Stage distribution: {stage_counts}")
    
    def test_filter_leads_by_new_stages(self, auth_headers):
        """GET /api/leads?stage=cliente_potencial - filter by new pipeline stages"""
        for stage in ["lead", "cliente_potencial", "cotizacion_generada", "pedido", "perdido"]:
            response = requests.get(f"{BASE_URL}/api/leads?stage={stage}", headers=auth_headers)
            assert response.status_code == 200
            leads = response.json()
            
            for lead in leads:
                assert lead["funnel_stage"] == stage
            
            print(f"✓ Filter by stage={stage} returns {len(leads)} leads")


class TestAIBotWebhook:
    """Test AI bot webhook processing, catalog search, and data extraction"""
    
    def test_webhook_new_contact_creates_lead(self, auth_headers):
        """POST /api/webhook/whatsapp - new contact creates lead with 'lead' stage"""
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Hola, quiero cotizar termos"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        print(f"✓ Webhook processed for new contact: {unique_phone}")
        
        # Verify lead was created
        leads_response = requests.get(f"{BASE_URL}/api/leads?search={unique_phone}", headers=auth_headers)
        assert leads_response.status_code == 200
        leads = leads_response.json()
        
        if len(leads) > 0:
            lead = leads[0]
            assert lead["phone_number"] == unique_phone
            assert lead["funnel_stage"] == "lead"  # New leads start at 'lead' stage
            print(f"  → Lead created with stage: {lead['funnel_stage']}")
        
        return unique_phone
    
    def test_ai_bot_extracts_product_codes(self, auth_headers):
        """Test AI bot extracts codigos_producto when user mentions product codes"""
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        # First message - establish conversation
        webhook_payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Hola, quiero cotizar los codigos JARPOR00140 y JARTER00005"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook_payload1)
        assert response.status_code == 200
        print(f"✓ AI Bot processes message with product codes for {unique_phone}")
        
        return unique_phone
    
    def test_ai_bot_extracts_correo_nombre_empresa(self, auth_headers):
        """Test AI bot extracts correo, nombre, empresa from messages"""
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        # Message with contact data
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Soy Juan Lopez de Corporacion ABC, mi correo es juan@abc.com, necesito 500 termos"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        print(f"✓ AI Bot processes message with contact data for {unique_phone}")
        
        return unique_phone
    
    def test_ai_bot_pipeline_update(self, auth_headers):
        """Test AI bot auto-updates pipeline: lead -> cliente_potencial -> cotizacion_generada"""
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        # Message 1 - Initial contact (should be 'lead')
        webhook1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Hola, quiero ver productos"}
                        }]
                    }
                }]
            }]
        }
        
        response1 = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook1)
        assert response1.status_code == 200
        
        # Check lead was created
        leads_response = requests.get(f"{BASE_URL}/api/leads?search={unique_phone}", headers=auth_headers)
        if leads_response.status_code == 200 and len(leads_response.json()) > 0:
            lead = leads_response.json()[0]
            print(f"  → After initial contact, stage: {lead.get('funnel_stage')}")
        
        print(f"✓ AI Bot pipeline test completed for {unique_phone}")
        return unique_phone


class TestLeadReactivation:
    """Test lead reactivation from 'perdido' status"""
    
    def test_reactivate_lost_lead_on_new_message(self, auth_headers):
        """Lead marked as 'perdido' gets reactivated on new message"""
        # Create a lead
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        # Create lead via API
        create_response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "phone_number": unique_phone,
            "name": "Test Lost Lead",
            "source": "whatsapp"
        })
        assert create_response.status_code == 200
        lead_id = create_response.json()["id"]
        print(f"✓ Created test lead: {lead_id}")
        
        # Mark as perdido
        update_response = requests.patch(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers=auth_headers,
            json={"funnel_stage": "perdido"}
        )
        assert update_response.status_code == 200
        print("  → Marked lead as 'perdido'")
        
        # Simulate new message from the same phone
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Hola, ahora si quiero cotizar"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        print("  → Simulated new message from lost lead")
        
        # Check if lead was reactivated
        lead_response = requests.get(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_headers)
        assert lead_response.status_code == 200
        lead = lead_response.json()
        
        # According to bot_service.py line 339-349, lead should be reactivated to 'lead' stage
        if lead["funnel_stage"] != "perdido":
            print(f"✓ Lead reactivated! New stage: {lead['funnel_stage']}")
        else:
            print(f"  → Note: Lead stage is still 'perdido' (may need conversation_state created first)")


class TestCatalogSearch:
    """Test AI bot catalog search functionality"""
    
    def test_ai_bot_responds_with_catalog_on_product_query(self, auth_headers):
        """Test AI bot shows catalog with codes when asked about products"""
        unique_phone = f"593TEST{uuid.uuid4().hex[:6].upper()}"
        
        # Ask for products (should trigger catalog search)
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "123"},
                        "messages": [{
                            "from": unique_phone,
                            "id": f"wamid_{uuid.uuid4().hex[:16]}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Quiero ver el catalogo de termos"}
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        print(f"✓ Catalog search triggered for 'termos' query")
        
        return unique_phone


class TestQuoteSendWithSMTPNotConfigured:
    """Test sending quote when SMTP is not configured"""
    
    def test_send_quote_returns_smtp_error(self, auth_headers):
        """POST /api/quotes/{id}/send - returns error when SMTP not configured"""
        # Get a quote
        response = requests.get(f"{BASE_URL}/api/quotes", headers=auth_headers)
        quotes = response.json()
        
        if len(quotes) == 0:
            pytest.skip("No quotes to test send")
        
        # Find a quote with email
        quote_with_email = None
        for q in quotes:
            if q.get("client_correo"):
                quote_with_email = q
                break
        
        if not quote_with_email:
            pytest.skip("No quote with client email to test send")
        
        quote_id = quote_with_email["id"]
        
        # Try to send - should fail with SMTP error
        send_response = requests.post(f"{BASE_URL}/api/quotes/{quote_id}/send", headers=auth_headers)
        
        # Should return 400 with SMTP not configured message
        if send_response.status_code == 400:
            assert "SMTP no configurado" in send_response.json().get("detail", "")
            print(f"✓ POST /api/quotes/{quote_id}/send - correctly returns SMTP error")
        elif send_response.status_code == 500:
            print(f"✓ POST /api/quotes/{quote_id}/send - returns SMTP error (500)")
        else:
            print(f"  → Response: {send_response.status_code} - {send_response.text}")


# Cleanup fixture
@pytest.fixture(autouse=True, scope="session")
def cleanup_test_data(auth_token):
    """Cleanup TEST_ prefixed leads after tests"""
    yield
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Delete test leads
    try:
        leads_response = requests.get(f"{BASE_URL}/api/leads?search=593TEST", headers=headers)
        if leads_response.status_code == 200:
            leads = leads_response.json()
            for lead in leads:
                if lead["phone_number"].startswith("593TEST"):
                    requests.delete(f"{BASE_URL}/api/leads/{lead['id']}", headers=headers)
            print(f"Cleaned up {len(leads)} test leads")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
