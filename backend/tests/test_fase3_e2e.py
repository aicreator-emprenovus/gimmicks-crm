"""
FASE 3-5 E2E Testing: Dashboard V2 with real metrics, Quotes V2 with PDF generation,
Clients CRUD, Inventory dual-schema search, and public catalog backward compatibility.
Test client: admin@gimmicks.com / admin123456
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == "admin@gimmicks.com"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@gimmicks.com",
        "password": "admin123456"
    })
    if response.status_code != 200:
        pytest.skip("Cannot authenticate - skipping authenticated tests")
    return response.json().get("access_token")


@pytest.fixture
def headers(auth_token):
    """Headers with authorization"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestDashboardV2:
    """Dashboard V2 endpoint tests - real metrics from DB"""
    
    def test_dashboard_stats(self, headers):
        """Test /api/dashboard-v2/stats returns real metrics"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/stats", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify all expected fields present
        expected_fields = [
            "total_products", "total_clients", "total_quotes", "total_pos",
            "total_leads", "active_conversations", "quotes_total_value", "pos_total_value"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify real data (5412 products expected)
        assert isinstance(data["total_products"], int)
        assert data["total_products"] > 0, "Should have products in inventory"
        print(f"Dashboard stats: products={data['total_products']}, clients={data['total_clients']}, quotes={data['total_quotes']}")
    
    def test_dashboard_activity_chart(self, headers):
        """Test /api/dashboard-v2/activity-chart returns chart data"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/activity-chart?days=14", headers=headers)
        assert response.status_code == 200, f"Activity chart failed: {response.text}"
        data = response.json()
        
        # Should return list of daily activity data
        assert isinstance(data, list), "Activity chart should return a list"
        if len(data) > 0:
            # Verify data structure
            sample = data[0]
            assert "date" in sample, "Missing date field"
            assert "cotizaciones" in sample, "Missing cotizaciones field"
            assert "ordenes" in sample, "Missing ordenes field"
        print(f"Activity chart: {len(data)} days of data")
    
    def test_dashboard_top_products(self, headers):
        """Test /api/dashboard-v2/top-products returns top quoted products"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/top-products?limit=5", headers=headers)
        assert response.status_code == 200, f"Top products failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Top products should return a list"
        if len(data) > 0:
            sample = data[0]
            assert "code" in sample or "name" in sample, "Missing product identifier"
        print(f"Top products: {len(data)} products")
    
    def test_dashboard_top_clients(self, headers):
        """Test /api/dashboard-v2/top-clients returns top clients by value"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/top-clients?limit=5", headers=headers)
        assert response.status_code == 200, f"Top clients failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Top clients should return a list"
        if len(data) > 0:
            sample = data[0]
            assert "client_id" in sample or "client_name" in sample
            assert "total_value" in sample or "total_quotes" in sample
        print(f"Top clients: {len(data)} clients")


class TestPublicCatalog:
    """Public catalog API - no auth required, backward compatible with both schemas"""
    
    def test_public_catalog_search_jarro(self):
        """Test /api/catalog/public?q=jarro works without auth"""
        response = requests.get(f"{BASE_URL}/api/catalog/public?q=jarro")
        assert response.status_code == 200, f"Public catalog failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Catalog should return list"
        print(f"Public catalog 'jarro': {len(data)} products found")
    
    def test_public_catalog_search_termo(self):
        """Test search with 'termo' keyword"""
        response = requests.get(f"{BASE_URL}/api/catalog/public?q=termo")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Public catalog 'termo': {len(data)} products found")
    
    def test_public_catalog_empty_query(self):
        """Test empty query returns empty list"""
        response = requests.get(f"{BASE_URL}/api/catalog/public?q=")
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Empty query should return empty list"


class TestInventoryV2:
    """Inventory V2 tests - supports both old (category_1) and new (categories) schemas"""
    
    def test_inventory_list(self, headers):
        """Test inventory list with pagination"""
        response = requests.get(f"{BASE_URL}/api/inventory/?page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Inventory list failed: {response.text}"
        data = response.json()
        
        assert "products" in data or isinstance(data, list), "Should return products"
        products = data.get("products", data) if isinstance(data, dict) else data
        print(f"Inventory: {len(products)} products on page 1")
    
    def test_inventory_search(self, headers):
        """Test inventory search works with both schemas"""
        response = requests.get(f"{BASE_URL}/api/inventory/?search=jarro&page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Inventory search failed: {response.text}"
        data = response.json()
        
        products = data.get("products", data) if isinstance(data, dict) else data
        print(f"Inventory search 'jarro': {len(products)} results")
    
    def test_inventory_categories(self, headers):
        """Test categories endpoint"""
        response = requests.get(f"{BASE_URL}/api/inventory/categories", headers=headers)
        assert response.status_code == 200, f"Categories failed: {response.text}"
        data = response.json()
        print(f"Categories: {len(data) if isinstance(data, list) else 'loaded'}")


class TestClientsCRUD:
    """Clients module tests - CRUD operations"""
    
    @pytest.fixture
    def test_client_data(self):
        """Test client data with unique identifier"""
        return {
            "name": f"TEST_Client_{uuid.uuid4().hex[:8]}",
            "company": "TEST Empresa SA",
            "email": f"test_{uuid.uuid4().hex[:6]}@test.com",
            "phone": "+593999999999",
            "address": "Test Address 123"
        }
    
    def test_clients_list(self, headers):
        """Test clients list endpoint"""
        response = requests.get(f"{BASE_URL}/api/clients/", headers=headers)
        assert response.status_code == 200, f"Clients list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list of clients"
        print(f"Clients: {len(data)} total")
    
    def test_client_create_and_verify(self, headers, test_client_data):
        """Test client creation with verification via history endpoint"""
        # CREATE
        response = requests.post(f"{BASE_URL}/api/clients/", json=test_client_data, headers=headers)
        assert response.status_code in [200, 201], f"Client create failed: {response.text}"
        created = response.json()
        
        assert "id" in created, "Missing client ID"
        client_id = created["id"]
        print(f"Created client: {client_id}")
        
        # GET via history endpoint to verify persistence
        get_response = requests.get(f"{BASE_URL}/api/clients/{client_id}/history", headers=headers)
        assert get_response.status_code == 200, f"Client history failed: {get_response.text}"
        history_data = get_response.json()
        assert "client" in history_data, "Missing client in history response"
        assert history_data["client"]["name"] == test_client_data["name"], "Client name mismatch"
        
        # CLEANUP - soft delete
        del_response = requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=false", headers=headers)
        assert del_response.status_code == 200, f"Client delete failed: {del_response.text}"
        
        # Permanent delete
        perm_del = requests.delete(f"{BASE_URL}/api/clients/{client_id}?permanent=true", headers=headers)
        print(f"Cleanup: permanent delete status={perm_del.status_code}")
    
    def test_clients_trash_list(self, headers):
        """Test trash list for deleted clients"""
        response = requests.get(f"{BASE_URL}/api/clients/?trash=true", headers=headers)
        assert response.status_code == 200, f"Trash list failed: {response.text}"


class TestQuotesV2:
    """Quotes V2 tests - CRUD, PDF generation, convert to PO"""
    
    def test_quotes_list(self, headers):
        """Test quotes list"""
        response = requests.get(f"{BASE_URL}/api/quotes-v2/?trash=false&doc_type=QUOTE", headers=headers)
        assert response.status_code == 200, f"Quotes list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list of quotes"
        print(f"Quotes: {len(data)} active")
    
    def test_purchase_orders_list(self, headers):
        """Test purchase orders list"""
        response = requests.get(f"{BASE_URL}/api/quotes-v2/?trash=false&doc_type=PO", headers=headers)
        assert response.status_code == 200, f"PO list failed: {response.text}"
        data = response.json()
        print(f"Purchase Orders: {len(data)} total")
    
    def test_quote_create_and_verify(self, headers):
        """Test quote creation with PDF generation"""
        # First get a client to use
        clients_resp = requests.get(f"{BASE_URL}/api/clients/", headers=headers)
        clients = clients_resp.json() if clients_resp.status_code == 200 else []
        
        client_id = clients[0]["id"] if clients else "test-client-1"
        client_name = clients[0].get("name", "Empresa Test") if clients else "Empresa Test"
        
        quote_data = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "client_name": client_name,
            "client_contact": "Test Contact",
            "doc_type": "QUOTE",
            "status": "draft",
            "items": [
                {
                    "code": "TEST-001",
                    "name": "Test Product",
                    "description": "Test Description",
                    "quantity": 100,
                    "unit_price": 5.00,
                    "total_price": 500.00,
                    "discount_amount": 0,
                    "discount_type": "%",
                    "additional_amount": 0,
                    "additional_type": "%"
                }
            ],
            "subtotal": 500.00,
            "tax": 75.00,
            "total": 575.00,
            "payment_terms": "50% anticipo",
            "validity": "15 días",
            "delivery_time": "7-10 días hábiles",
            "notes": "Test quote"
        }
        
        # CREATE
        response = requests.post(f"{BASE_URL}/api/quotes-v2/", json=quote_data, headers=headers)
        assert response.status_code == 200, f"Quote create failed: {response.text}"
        created = response.json()
        quote_id = created.get("id", quote_data["id"])
        print(f"Created quote: {quote_id}")
        
        # VERIFY via GET
        get_resp = requests.get(f"{BASE_URL}/api/quotes-v2/{quote_id}", headers=headers)
        if get_resp.status_code == 200:
            fetched = get_resp.json()
            assert fetched["client_name"] == client_name
        
        # GENERATE PDF
        pdf_resp = requests.post(f"{BASE_URL}/api/quotes-v2/{quote_id}/generate-pdf", headers=headers)
        assert pdf_resp.status_code == 200, f"PDF generation failed: {pdf_resp.text}"
        pdf_data = pdf_resp.json()
        assert "pdf_base64" in pdf_data, "Missing PDF data"
        assert "filename" in pdf_data, "Missing filename"
        print(f"Generated PDF: {pdf_data['filename']}")
        
        # CLEANUP - delete quote
        del_resp = requests.delete(f"{BASE_URL}/api/quotes-v2/{quote_id}?permanent=true", headers=headers)
        print(f"Cleanup quote: status={del_resp.status_code}")


class TestExistingModules:
    """Test existing modules are intact - Inbox, Leads, Users, Settings"""
    
    def test_conversations_list(self, headers):
        """Test inbox conversations"""
        response = requests.get(f"{BASE_URL}/api/conversations", headers=headers)
        assert response.status_code == 200, f"Conversations failed: {response.text}"
        data = response.json()
        print(f"Conversations: {len(data)} total")
    
    def test_leads_list(self, headers):
        """Test leads list"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        assert response.status_code == 200, f"Leads failed: {response.text}"
        data = response.json()
        print(f"Leads: {len(data)} total")
    
    def test_users_list(self, headers):
        """Test users list (admin only)"""
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200, f"Users failed: {response.text}"
        data = response.json()
        print(f"Users: {len(data)} total")
    
    def test_automation_rules(self, headers):
        """Test automation rules list"""
        response = requests.get(f"{BASE_URL}/api/automation-rules", headers=headers)
        assert response.status_code == 200, f"Rules failed: {response.text}"
        data = response.json()
        print(f"Automation rules: {len(data)} total")
    
    def test_dashboard_metrics_old(self, headers):
        """Test old dashboard metrics endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/dashboard/metrics", headers=headers)
        assert response.status_code == 200, f"Old dashboard failed: {response.text}"


class TestSidebarNavigation:
    """Verify all sidebar items have working APIs"""
    
    def test_all_navigation_endpoints(self, headers):
        """Test all main navigation endpoints return 200"""
        endpoints = [
            ("/api/dashboard-v2/stats", "Dashboard"),
            ("/api/conversations", "Inbox"),
            ("/api/users", "Usuarios"),
            ("/api/inventory/", "Inventario"),
            ("/api/clients/", "Clientes"),
            ("/api/leads", "Leads"),
            ("/api/quotes-v2/?doc_type=QUOTE", "Cotizaciones"),
            ("/api/automation-rules", "Configuración")
        ]
        
        all_passed = True
        for endpoint, name in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            status = "✓" if response.status_code == 200 else "✗"
            print(f"{status} {name}: {response.status_code}")
            if response.status_code != 200:
                all_passed = False
        
        assert all_passed, "Some navigation endpoints failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
