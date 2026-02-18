"""
FASE 2 Integration Tests for CRM Gimmicks
Testing: Login, Inventory, Clients, Quotes (v2), QuoteBuilder, Dashboard, existing modules
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crm-cotizador-merge.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "admin@gimmicks.com"
TEST_PASSWORD = "admin123456"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for authenticated requests"""
    return {"Authorization": f"Bearer {auth_token}"}


# ==========================
# AUTH TESTS
# ==========================
class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test successful login with admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "admin"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@email.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
    
    def test_auth_me(self, auth_headers):
        """Test /auth/me endpoint returns current user"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL


# ==========================
# INVENTORY TESTS (NEW V2 Endpoints)
# ==========================
class TestInventoryV2:
    """Inventory module tests (Proyecto B)"""
    
    def test_get_inventory_paginated(self, auth_headers):
        """Test inventory endpoint with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/",
            params={"page": 1, "limit": 50},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "pages" in data
        print(f"Total products in inventory: {data['total']}")
        assert data["total"] > 0, "Inventory should have products (5000+)"
    
    def test_get_inventory_search(self, auth_headers):
        """Test inventory search by keyword"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/",
            params={"search": "jarro", "limit": 20},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"Found {len(data['products'])} products matching 'jarro'")
    
    def test_get_categories(self, auth_headers):
        """Test getting product categories"""
        response = requests.get(
            f"{BASE_URL}/api/inventory/categories",
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json()
        assert isinstance(categories, list)
        print(f"Found {len(categories)} categories")


# ==========================
# CLIENTS TESTS (NEW Module)
# ==========================
class TestClients:
    """Clients module tests (Proyecto B)"""
    
    def test_get_clients(self, auth_headers):
        """Test getting clients list"""
        response = requests.get(
            f"{BASE_URL}/api/clients/",
            headers=auth_headers
        )
        assert response.status_code == 200
        clients = response.json()
        assert isinstance(clients, list)
        print(f"Found {len(clients)} clients")
    
    def test_create_client_and_verify(self, auth_headers):
        """Test creating a new client"""
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Cliente_{unique_id}",
            "email": f"test_{unique_id}@test.com",
            "phone": "+593999999999",
            "contact_person": "Test Contact",
            "city": "Quito",
            "sector": "Tecnología"
        }
        
        # Create client
        response = requests.post(
            f"{BASE_URL}/api/clients/",
            json=client_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        created = response.json()
        assert created["name"] == client_data["name"]
        assert created["email"] == client_data["email"]
        client_id = created["id"]
        
        # Verify via GET (list)
        response = requests.get(
            f"{BASE_URL}/api/clients/",
            headers=auth_headers
        )
        assert response.status_code == 200
        clients = response.json()
        found = any(c["id"] == client_id for c in clients)
        assert found, "Created client should be in list"
        
        # Cleanup - delete the test client
        response = requests.delete(
            f"{BASE_URL}/api/clients/{client_id}",
            params={"permanent": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        print(f"Client CRUD test passed, cleaned up client {client_id}")
    
    def test_client_trash_restore(self, auth_headers):
        """Test client soft delete and restore"""
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "name": f"TEST_Trash_{unique_id}",
            "email": f"trash_{unique_id}@test.com"
        }
        
        # Create
        response = requests.post(
            f"{BASE_URL}/api/clients/",
            json=client_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        client_id = response.json()["id"]
        
        # Soft delete (move to trash)
        response = requests.delete(
            f"{BASE_URL}/api/clients/{client_id}",
            params={"permanent": False},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify in trash
        response = requests.get(
            f"{BASE_URL}/api/clients/",
            params={"trash": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        trash_clients = response.json()
        found_in_trash = any(c["id"] == client_id for c in trash_clients)
        assert found_in_trash, "Client should be in trash"
        
        # Restore
        response = requests.post(
            f"{BASE_URL}/api/clients/{client_id}/restore",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Cleanup
        response = requests.delete(
            f"{BASE_URL}/api/clients/{client_id}",
            params={"permanent": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        print("Client trash/restore test passed")


# ==========================
# QUOTES V2 TESTS (NEW Module)
# ==========================
class TestQuotesV2:
    """Quotes v2 module tests (Proyecto B)"""
    
    def test_get_quotes(self, auth_headers):
        """Test getting quotes list"""
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"doc_type": "QUOTE", "trash": False},
            headers=auth_headers
        )
        assert response.status_code == 200
        quotes = response.json()
        assert isinstance(quotes, list)
        print(f"Found {len(quotes)} quotes")
    
    def test_get_purchase_orders(self, auth_headers):
        """Test getting purchase orders (PO) list"""
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"doc_type": "PO", "trash": False},
            headers=auth_headers
        )
        assert response.status_code == 200
        pos = response.json()
        assert isinstance(pos, list)
        print(f"Found {len(pos)} purchase orders")
    
    def test_create_quote_draft(self, auth_headers):
        """Test creating a quote draft"""
        # First, get a client to use
        response = requests.get(f"{BASE_URL}/api/clients/", headers=auth_headers)
        clients = response.json()
        
        # Get a product
        response = requests.get(
            f"{BASE_URL}/api/inventory/",
            params={"limit": 1},
            headers=auth_headers
        )
        products = response.json().get("products", [])
        
        if not clients or not products:
            pytest.skip("Need at least one client and one product")
        
        client = clients[0]
        product = products[0]
        
        quote_data = {
            "doc_type": "QUOTE",
            "client_id": client["id"],
            "client_name": client["name"],
            "client_contact": client.get("contact_person", ""),
            "client_email": client["email"],
            "items": [
                {
                    "item_id": f"item-{uuid.uuid4()}",
                    "product_id": product.get("id", ""),
                    "code": product["code"],
                    "name": product["name"],
                    "description": product.get("description", ""),
                    "quantity": 10,
                    "unit_price": product.get("price", 5.0),
                    "total_price": product.get("price", 5.0) * 10,
                    "image_url": product.get("image_url", ""),
                    "categories": product.get("categories", []),
                    "discount_amount": 0,
                    "discount_type": "$",
                    "additional_amount": 0,
                    "additional_type": "$",
                    "otros": ""
                }
            ],
            "subtotal": product.get("price", 5.0) * 10,
            "tax": product.get("price", 5.0) * 10 * 0.15,
            "total": product.get("price", 5.0) * 10 * 1.15,
            "status": "draft",
            "payment_terms": "50% anticipo, 50% contra entrega",
            "validity": "8 días",
            "delivery_time": "Por confirmar"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/quotes-v2/",
            json=quote_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Create quote failed: {response.text}"
        created = response.json()
        assert created["client_id"] == client["id"]
        assert created["status"] == "draft"
        assert "quote_number" in created
        quote_id = created["id"]
        
        # Verify via GET
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/{quote_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        fetched = response.json()
        assert fetched["id"] == quote_id
        
        # Cleanup
        response = requests.delete(
            f"{BASE_URL}/api/quotes-v2/{quote_id}",
            params={"permanent": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        print(f"Quote CRUD test passed, cleaned up quote {quote_id}")
    
    def test_generate_pdf(self, auth_headers):
        """Test PDF generation for existing quote"""
        # Get an existing quote
        response = requests.get(
            f"{BASE_URL}/api/quotes-v2/",
            params={"doc_type": "QUOTE", "trash": False},
            headers=auth_headers
        )
        quotes = response.json()
        
        if not quotes:
            pytest.skip("No quotes available for PDF test")
        
        quote_id = quotes[0]["id"]
        
        # Generate PDF
        response = requests.post(
            f"{BASE_URL}/api/quotes-v2/{quote_id}/generate-pdf",
            params={"doc_type": "PROFORMA"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pdf_base64" in data
        assert "filename" in data
        assert len(data["pdf_base64"]) > 100, "PDF should have content"
        print(f"PDF generated successfully: {data['filename']}")


# ==========================
# DASHBOARD V2 TESTS (NEW Module)
# ==========================
class TestDashboardV2:
    """Dashboard v2 module tests (Proyecto B)"""
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard-v2/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_products" in data
        assert "total_clients" in data
        assert "total_quotes" in data
        assert "total_pos" in data
        print(f"Dashboard stats: {data['total_products']} products, {data['total_clients']} clients, {data['total_quotes']} quotes")
    
    def test_activity_chart(self, auth_headers):
        """Test activity chart data endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard-v2/activity-chart",
            params={"days": 30},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "date" in data[0]
            assert "cotizaciones" in data[0]
            assert "ordenes" in data[0]
    
    def test_top_products(self, auth_headers):
        """Test top products endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard-v2/top-products",
            params={"limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_top_clients(self, auth_headers):
        """Test top clients endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard-v2/top-clients",
            params={"limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ==========================
# EXISTING MODULES TESTS (Should NOT be broken)
# ==========================
class TestExistingModules:
    """Tests for existing modules that should still work"""
    
    def test_inbox_conversations(self, auth_headers):
        """Test conversations/inbox endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} conversations in Inbox")
    
    def test_leads(self, auth_headers):
        """Test leads endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} leads")
    
    def test_users(self, auth_headers):
        """Test users endpoint (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} users")
    
    def test_automation_rules(self, auth_headers):
        """Test automation rules endpoint (Settings)"""
        response = requests.get(
            f"{BASE_URL}/api/automation-rules",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} automation rules")
    
    def test_dashboard_metrics(self, auth_headers):
        """Test old dashboard metrics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/metrics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "messages_today" in data


# ==========================
# PUBLIC CATALOG TEST
# ==========================
class TestPublicCatalog:
    """Public catalog tests (no auth required)"""
    
    def test_public_catalog_no_auth(self):
        """Test public catalog works without authentication"""
        response = requests.get(
            f"{BASE_URL}/api/catalog/public",
            params={"q": "jarro", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Public catalog returned {len(data)} products for 'jarro'")
    
    def test_public_catalog_empty_query(self):
        """Test public catalog with empty query returns empty"""
        response = requests.get(
            f"{BASE_URL}/api/catalog/public",
            params={"q": "", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
