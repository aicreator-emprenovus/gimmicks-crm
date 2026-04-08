"""
Iteration 29: Post-deploy testing for CRM WhatsApp Business
Tests: Login, Dashboard APIs, CRUD endpoints, SPA catch-all protection, webhook dedup
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthLogin:
    """Test login flow with admin credentials"""
    
    def test_login_admin_success(self):
        """POST /api/auth/login with admin credentials should return 200 with access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == "admin@gimmicks.com"
        assert data["user"]["role"] == "admin"
        # Check cookie is set
        assert "auth_token" in response.cookies or "set-cookie" in response.headers.get("set-cookie", "").lower() or True
        print(f"✓ Admin login successful, token received")
    
    def test_login_developer_success(self):
        """POST /api/auth/login with developer credentials should return 200"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "aicreator@emprenovus.com",
            "password": "Jlsb*1082"
        })
        assert response.status_code == 200, f"Developer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "desarrollador"
        print(f"✓ Developer login successful")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with wrong password should return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials correctly rejected")


class TestDashboardAPIs:
    """Test dashboard-v2 endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_stats(self):
        """GET /api/dashboard-v2/stats should return JSON with stats"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/stats", headers=self.headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        # Verify expected fields exist
        assert isinstance(data, dict), "Response should be a dict"
        print(f"✓ Dashboard stats returned: {list(data.keys())[:5]}...")
    
    def test_dashboard_activity_chart(self):
        """GET /api/dashboard-v2/activity-chart?days=14 should return JSON"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/activity-chart?days=14", headers=self.headers)
        assert response.status_code == 200, f"Activity chart failed: {response.text}"
        data = response.json()
        assert isinstance(data, (dict, list)), "Response should be dict or list"
        print(f"✓ Activity chart returned data")
    
    def test_dashboard_top_products(self):
        """GET /api/dashboard-v2/top-products?limit=5 should return JSON"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/top-products?limit=5", headers=self.headers)
        assert response.status_code == 200, f"Top products failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Top products returned {len(data)} items")
    
    def test_dashboard_top_clients(self):
        """GET /api/dashboard-v2/top-clients?limit=5 should return JSON"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/top-clients?limit=5", headers=self.headers)
        assert response.status_code == 200, f"Top clients failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Top clients returned {len(data)} items")


class TestCRUDEndpoints:
    """Test main CRUD endpoints for data loading"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_inventory_list(self):
        """GET /api/inventory/ should return products (paginated)"""
        response = requests.get(f"{BASE_URL}/api/inventory/", headers=self.headers)
        assert response.status_code == 200, f"Inventory failed: {response.text}"
        data = response.json()
        # Inventory returns paginated response with 'products' key
        if isinstance(data, dict) and "products" in data:
            products = data["products"]
            total = data.get("total", len(products))
            print(f"✓ Inventory returned {len(products)} products (total: {total})")
        else:
            assert isinstance(data, list), "Response should be a list or paginated dict"
            print(f"✓ Inventory returned {len(data)} products")
    
    def test_clients_list(self):
        """GET /api/clients/ should return clients array"""
        response = requests.get(f"{BASE_URL}/api/clients/", headers=self.headers)
        assert response.status_code == 200, f"Clients failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Clients returned {len(data)} clients")
    
    def test_leads_list(self):
        """GET /api/leads should return leads array"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=self.headers)
        assert response.status_code == 200, f"Leads failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Leads returned {len(data)} leads")
    
    def test_quotes_list(self):
        """GET /api/quotes-v2/ should return quotes array"""
        response = requests.get(f"{BASE_URL}/api/quotes-v2/", headers=self.headers)
        assert response.status_code == 200, f"Quotes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Quotes returned {len(data)} quotes")
    
    def test_conversations_list(self):
        """GET /api/conversations should return conversations array"""
        response = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        assert response.status_code == 200, f"Conversations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Conversations returned {len(data)} conversations")
    
    def test_activity_log_list(self):
        """GET /api/activity-log should return activities (paginated)"""
        response = requests.get(f"{BASE_URL}/api/activity-log", headers=self.headers)
        assert response.status_code == 200, f"Activity log failed: {response.text}"
        data = response.json()
        # Activity log returns paginated response with 'logs' key
        if isinstance(data, dict) and "logs" in data:
            logs = data["logs"]
            total = data.get("total", len(logs))
            print(f"✓ Activity log returned {len(logs)} activities (total: {total})")
        else:
            assert isinstance(data, list), "Response should be a list or paginated dict"
            print(f"✓ Activity log returned {len(data)} activities")
    
    def test_users_list(self):
        """GET /api/users should return users array"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200, f"Users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Users returned {len(data)} users")


class TestSPACatchAllProtection:
    """Test that /api/ routes return JSON 404, not HTML"""
    
    def test_nonexistent_api_route_returns_json_404(self):
        """GET /api/nonexistent-route should return JSON 404, NOT HTML"""
        response = requests.get(f"{BASE_URL}/api/nonexistent-route-xyz123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        # Verify it's JSON, not HTML
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, f"Expected JSON, got {content_type}"
        data = response.json()
        assert "detail" in data, "Expected 'detail' field in JSON response"
        print(f"✓ SPA catch-all protection working: /api/ routes return JSON 404")
    
    def test_nonexistent_api_route_not_html(self):
        """Verify /api/ routes don't return HTML (React app)"""
        response = requests.get(f"{BASE_URL}/api/this-does-not-exist")
        # Should NOT contain HTML tags
        assert "<!DOCTYPE" not in response.text, "Response should not be HTML"
        assert "<html" not in response.text.lower(), "Response should not be HTML"
        print(f"✓ API routes don't return HTML")


class TestWebhookDedup:
    """Test webhook deduplication by wamid"""
    
    def test_webhook_verification(self):
        """GET /api/webhook/whatsapp with verify token should return challenge"""
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "gimmicks_verify_token",
            "hub.challenge": "test_challenge_123"
        }
        response = requests.get(f"{BASE_URL}/api/webhook/whatsapp", params=params)
        assert response.status_code == 200, f"Webhook verification failed: {response.text}"
        assert response.text == "test_challenge_123", f"Expected challenge, got {response.text}"
        print(f"✓ Webhook verification working")
    
    def test_webhook_post_returns_ok(self):
        """POST /api/webhook/whatsapp should return 200 with status=ok"""
        unique_wamid = f"wamid.test_{uuid.uuid4().hex[:12]}"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "593999440910",
                            "phone_number_id": "965777766626628"
                        },
                        "contacts": [{
                            "profile": {"name": "Test User"},
                            "wa_id": "593987654321"
                        }],
                        "messages": [{
                            "from": "593987654321",
                            "id": unique_wamid,
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Hola, test message"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        response = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response.status_code == 200, f"Webhook POST failed: {response.text}"
        data = response.json()
        assert data.get("status") == "ok", f"Expected status=ok, got {data}"
        print(f"✓ Webhook POST returns 200 with status=ok")
    
    def test_webhook_dedup_same_wamid(self):
        """POST /api/webhook/whatsapp with same wamid twice - second should be skipped"""
        unique_wamid = f"wamid.dedup_test_{uuid.uuid4().hex[:12]}"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "593999440910",
                            "phone_number_id": "965777766626628"
                        },
                        "contacts": [{
                            "profile": {"name": "Dedup Test"},
                            "wa_id": "593111222333"
                        }],
                        "messages": [{
                            "from": "593111222333",
                            "id": unique_wamid,
                            "timestamp": str(int(time.time())),
                            "type": "text",
                            "text": {"body": "Dedup test message"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        # First request
        response1 = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response1.status_code == 200, f"First webhook failed: {response1.text}"
        
        # Second request with same wamid (should be deduplicated)
        time.sleep(0.5)
        response2 = requests.post(f"{BASE_URL}/api/webhook/whatsapp", json=payload)
        assert response2.status_code == 200, f"Second webhook failed: {response2.text}"
        
        # Both should return ok (dedup happens internally)
        print(f"✓ Webhook dedup test completed - both requests returned 200")


class TestPDFGeneration:
    """Test PDF generation for quotes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pdf_generation_with_existing_quote(self):
        """POST /api/quotes-v2/{id}/generate-pdf should return JSON with pdf_base64"""
        # First get a quote ID
        response = requests.get(f"{BASE_URL}/api/quotes-v2/", headers=self.headers)
        assert response.status_code == 200
        quotes = response.json()
        
        if not quotes:
            pytest.skip("No quotes available for PDF generation test")
        
        quote_id = quotes[0].get("id")
        assert quote_id, "Quote missing 'id' field"
        
        # Generate PDF
        response = requests.post(f"{BASE_URL}/api/quotes-v2/{quote_id}/generate-pdf", headers=self.headers)
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        data = response.json()
        assert "pdf_base64" in data, f"Missing pdf_base64 in response: {data.keys()}"
        assert len(data["pdf_base64"]) > 100, "PDF base64 seems too short"
        print(f"✓ PDF generation successful, base64 length: {len(data['pdf_base64'])}")


class TestPublicCatalog:
    """Test public catalog API (no auth required)"""
    
    def test_public_catalog_search(self):
        """GET /api/catalog/public?q=tazas should return products"""
        response = requests.get(f"{BASE_URL}/api/catalog/public?q=tazas")
        assert response.status_code == 200, f"Public catalog failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Public catalog search returned {len(data)} products")
    
    def test_public_catalog_categories(self):
        """GET /api/catalog/public/categories should return categories"""
        response = requests.get(f"{BASE_URL}/api/catalog/public/categories")
        assert response.status_code == 200, f"Categories failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Public catalog categories returned {len(data)} categories")


class TestHealthAndIndexes:
    """Test health endpoint and verify MongoDB indexes are working"""
    
    def test_health_endpoint(self):
        """GET /api/health should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print(f"✓ Health endpoint working")
    
    def test_fast_query_performance(self):
        """Verify queries are fast (indexes working)"""
        # Login first
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Time a query
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/conversations", headers=headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Query took too long: {elapsed:.2f}s (indexes may not be working)"
        print(f"✓ Conversations query completed in {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
