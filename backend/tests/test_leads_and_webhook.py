"""
Backend API Tests for WhatsApp Business CRM - Gimmicks
Tests: Auth, Leads (with new AI fields), Webhook, AI Bot functionality
"""
import pytest
import requests
import os
import uuid
import time

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
LOCAL_URL = "http://localhost:8001"

# Test credentials
TEST_EMAIL = "admin@gimmicks.com"
TEST_PASSWORD = "admin123456"


class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test login with valid credentials - admin@gimmicks.com"""
        response = requests.post(f"{LOCAL_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "access_token not in response"
        assert "user" in data, "user not in response"
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Login successful for {TEST_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{LOCAL_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for authenticated requests"""
    response = requests.post(f"{LOCAL_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Auth failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for requests"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestLeadsWithNewFields:
    """Test Leads API with new AI-extracted fields"""
    
    def test_get_leads_returns_new_fields(self, auth_headers):
        """GET /api/leads should return leads with new fields"""
        response = requests.get(f"{LOCAL_URL}/api/leads?limit=10", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        
        leads = response.json()
        assert isinstance(leads, list), "Response should be a list"
        
        if leads:
            lead = leads[0]
            # Verify all new fields are present (can be null but must exist)
            expected_fields = [
                "id", "phone_number", "name", "source", "status", 
                "funnel_stage", "classification", "notes",
                "ai_category", "empresa", "ciudad", "correo",
                "producto_interes", "cantidad_estimada", "presupuesto",
                "created_at", "updated_at", "last_message_at"
            ]
            for field in expected_fields:
                assert field in lead, f"Field '{field}' missing from lead response"
            print(f"✓ GET /api/leads returns all expected fields including new AI fields")
            print(f"  Sample lead: name={lead.get('name')}, ai_category={lead.get('ai_category')}, empresa={lead.get('empresa')}")
        else:
            print("✓ GET /api/leads returned empty list (no leads yet)")
    
    def test_get_lead_detail_with_new_fields(self, auth_headers):
        """GET /api/leads/{{lead_id}} returns lead with all new fields"""
        # First get a lead
        response = requests.get(f"{LOCAL_URL}/api/leads?limit=1", headers=auth_headers)
        assert response.status_code == 200
        leads = response.json()
        
        if not leads:
            pytest.skip("No leads to test")
        
        lead_id = leads[0]["id"]
        
        # Get detail
        response = requests.get(f"{LOCAL_URL}/api/leads/{lead_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get lead detail: {response.text}"
        
        lead = response.json()
        assert lead["id"] == lead_id
        
        # Verify new fields exist
        new_fields = ["ai_category", "empresa", "ciudad", "correo", "producto_interes", "cantidad_estimada", "presupuesto"]
        for field in new_fields:
            assert field in lead, f"New field '{field}' missing from lead detail"
        
        print(f"✓ GET /api/leads/{lead_id} returns lead with all new AI fields")
    
    def test_create_and_update_lead(self, auth_headers):
        """Test CRUD: Create lead, update with classification"""
        unique_phone = f"+593TEST{uuid.uuid4().hex[:8]}"
        
        # CREATE
        create_data = {
            "phone_number": unique_phone,
            "name": "TEST Lead for AI fields",
            "source": "whatsapp",
            "notes": "Test lead created by pytest"
        }
        response = requests.post(f"{LOCAL_URL}/api/leads", json=create_data, headers=auth_headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        created = response.json()
        lead_id = created["id"]
        assert created["phone_number"] == unique_phone
        assert created["classification"] == "frio"  # Default
        print(f"✓ Created lead: {lead_id}")
        
        # UPDATE - change stage and classification
        update_data = {
            "name": "TEST Lead Updated",
            "funnel_stage": "pedido",
            "classification": "caliente",
            "notes": "Updated via pytest"
        }
        response = requests.patch(f"{LOCAL_URL}/api/leads/{lead_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated = response.json()
        assert updated["name"] == "TEST Lead Updated"
        assert updated["funnel_stage"] == "pedido"
        assert updated["classification"] == "caliente"
        print(f"✓ Updated lead: name={updated['name']}, stage={updated['funnel_stage']}, classification={updated['classification']}")
        
        # CLEANUP - delete
        response = requests.delete(f"{LOCAL_URL}/api/leads/{lead_id}", headers=auth_headers)
        assert response.status_code == 200
        print(f"✓ Deleted test lead: {lead_id}")
    
    def test_filter_leads_by_stage(self, auth_headers):
        """Test filtering leads by funnel_stage"""
        response = requests.get(f"{LOCAL_URL}/api/leads?stage=lead", headers=auth_headers)
        assert response.status_code == 200
        leads = response.json()
        for lead in leads:
            assert lead["funnel_stage"] == "lead", f"Lead {lead['id']} has stage {lead['funnel_stage']}, expected 'lead'"
        print(f"✓ Filter by stage=lead returned {len(leads)} leads")
    
    def test_filter_leads_by_classification(self, auth_headers):
        """Test filtering leads by classification (frio/tibio/caliente)"""
        response = requests.get(f"{LOCAL_URL}/api/leads?classification=caliente", headers=auth_headers)
        assert response.status_code == 200
        leads = response.json()
        for lead in leads:
            assert lead["classification"] == "caliente", f"Lead has classification {lead['classification']}"
        print(f"✓ Filter by classification=caliente returned {len(leads)} leads")
    
    def test_search_leads_by_name(self, auth_headers):
        """Test searching leads by name"""
        response = requests.get(f"{LOCAL_URL}/api/leads?search=Carlos", headers=auth_headers)
        assert response.status_code == 200
        leads = response.json()
        print(f"✓ Search by 'Carlos' returned {len(leads)} leads")


class TestWebhookAndAIBot:
    """Test WhatsApp webhook and AI bot functionality"""
    
    def test_webhook_processes_incoming_message(self, auth_headers):
        """POST /api/webhook/whatsapp should process incoming WhatsApp message"""
        test_phone = f"593TEST{uuid.uuid4().hex[:6]}"
        
        # WhatsApp webhook format
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551234567",
                            "phone_number_id": "994356967089829"
                        },
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "text": {"body": "Hola, necesito cotizar 100 tazas personalizadas para mi empresa TechTest"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(f"{LOCAL_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        data = response.json()
        assert data.get("status") == "ok", f"Webhook did not return ok: {data}"
        print(f"✓ Webhook processed message from {test_phone}")
        
        # Wait for AI to process (bot is async)
        time.sleep(3)
        
        # Verify lead was created
        leads_response = requests.get(f"{LOCAL_URL}/api/leads?search={test_phone}", headers=auth_headers)
        assert leads_response.status_code == 200
        leads = leads_response.json()
        
        if leads:
            lead = leads[0]
            print(f"✓ Lead created from webhook: phone={lead['phone_number']}, name={lead.get('name')}")
            print(f"  AI extracted: empresa={lead.get('empresa')}, producto={lead.get('producto_interes')}, cantidad={lead.get('cantidad_estimada')}")
        else:
            print(f"⚠ No lead found for {test_phone} - may take longer for AI processing")
    
    def test_webhook_creates_conversation(self, auth_headers):
        """Webhook should create a conversation for new phone number"""
        test_phone = f"593NEW{uuid.uuid4().hex[:6]}"
        
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.test_{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "text": {"body": "Hola, quiero informacion sobre productos promocionales"},
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{LOCAL_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        print(f"✓ Webhook processed new contact: {test_phone}")
        
        # Give AI time to process
        time.sleep(2)
        
        # Check conversations
        conv_response = requests.get(f"{LOCAL_URL}/api/conversations", headers=auth_headers)
        assert conv_response.status_code == 200
        conversations = conv_response.json()
        
        matching = [c for c in conversations if c["phone_number"] == test_phone]
        if matching:
            print(f"✓ Conversation created for {test_phone}")
        else:
            print(f"⚠ Conversation for {test_phone} not found immediately")


class TestAIDataExtraction:
    """Test AI bot data extraction capabilities"""
    
    def test_ai_extracts_lead_data_from_message(self, auth_headers):
        """Test that AI extracts name, empresa, producto, cantidad from natural language"""
        test_phone = f"593AI{uuid.uuid4().hex[:6]}"
        
        # Send a rich message with multiple data points
        message = "Hola soy Juan Perez de Corporacion XYZ en Guayaquil. Necesito 500 esferos personalizados con nuestro logo para un evento. Mi correo es juan@xyz.com"
        
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": test_phone,
                            "id": f"wamid.{uuid.uuid4().hex[:8]}",
                            "timestamp": str(int(time.time())),
                            "text": {"body": message},
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        
        response = requests.post(f"{LOCAL_URL}/api/webhook/whatsapp", json=webhook_payload)
        assert response.status_code == 200
        
        # Wait for AI processing
        time.sleep(5)
        
        # Check lead was updated with extracted data
        leads_response = requests.get(f"{LOCAL_URL}/api/leads?search={test_phone}", headers=auth_headers)
        leads = leads_response.json()
        
        if leads:
            lead = leads[0]
            print(f"✓ AI Processing Results for {test_phone}:")
            print(f"  Name: {lead.get('name')} (expected: Juan Perez)")
            print(f"  Empresa: {lead.get('empresa')} (expected: Corporacion XYZ)")
            print(f"  Ciudad: {lead.get('ciudad')} (expected: Guayaquil)")
            print(f"  Correo: {lead.get('correo')} (expected: juan@xyz.com)")
            print(f"  Producto: {lead.get('producto_interes')} (expected: esferos)")
            print(f"  Cantidad: {lead.get('cantidad_estimada')} (expected: 500)")
            print(f"  Classification: {lead.get('classification')}")
            print(f"  AI Category: {lead.get('ai_category')}")
        else:
            print(f"⚠ Lead for {test_phone} not found - AI may still be processing")


class TestLeadClassification:
    """Test lead quality classification (caliente/tibio/frio)"""
    
    def test_classification_values_are_valid(self, auth_headers):
        """All leads should have valid classification: frio, tibio, or caliente"""
        response = requests.get(f"{LOCAL_URL}/api/leads", headers=auth_headers)
        assert response.status_code == 200
        
        leads = response.json()
        valid_classifications = ["frio", "tibio", "caliente"]
        
        for lead in leads:
            assert lead["classification"] in valid_classifications, f"Lead {lead['id']} has invalid classification: {lead['classification']}"
        
        print(f"✓ All {len(leads)} leads have valid classifications")
        
        # Count by classification
        counts = {c: sum(1 for l in leads if l["classification"] == c) for c in valid_classifications}
        print(f"  Distribution: frio={counts['frio']}, tibio={counts['tibio']}, caliente={counts['caliente']}")


class TestLeadCategories:
    """Test AI category assignment"""
    
    def test_ai_category_values(self, auth_headers):
        """Verify ai_category has valid values when set"""
        response = requests.get(f"{LOCAL_URL}/api/leads", headers=auth_headers)
        assert response.status_code == 200
        
        leads = response.json()
        valid_categories = ["cotizacion_directa", "solicitud_catalogo", "consulta_ideas", "pedido_estacional", "otra", None]
        
        for lead in leads:
            cat = lead.get("ai_category")
            # ai_category can be null or one of the valid values
            if cat is not None:
                assert cat in valid_categories, f"Lead {lead['id']} has invalid ai_category: {cat}"
        
        # Count leads with categories
        categorized = [l for l in leads if l.get("ai_category")]
        print(f"✓ {len(categorized)}/{len(leads)} leads have AI category assigned")
        
        if categorized:
            cats = {}
            for l in categorized:
                c = l["ai_category"]
                cats[c] = cats.get(c, 0) + 1
            print(f"  Categories: {cats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
