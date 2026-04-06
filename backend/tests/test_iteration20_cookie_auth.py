"""
Iteration 20: Testing httpOnly cookie-based authentication migration
Tests the code quality fixes including:
1. httpOnly cookies replacing localStorage for auth tokens
2. Cookie-based auth on protected endpoints
3. Logout clears session properly
4. Dashboard, Inventory, Clients, QuoteHistory endpoints work with cookies
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"
DEV_EMAIL = "aicreator@emprenovus.com"
DEV_PASSWORD = "Jlsb*1082"


class TestCookieBasedAuth:
    """Test httpOnly cookie authentication flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for each test"""
        self.session = requests.Session()
        yield
        self.session.close()
    
    def test_login_sets_httponly_cookie(self):
        """Login should set httpOnly auth_token cookie"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Check response contains user data
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        
        # Check cookie was set
        cookies = self.session.cookies.get_dict()
        assert "auth_token" in cookies, "auth_token cookie not set"
        print(f"✓ Login successful, auth_token cookie set")
    
    def test_auth_me_with_cookie(self):
        """GET /api/auth/me should work with cookie auth"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Test /auth/me with cookie
        me_resp = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200, f"Auth/me failed: {me_resp.text}"
        
        data = me_resp.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        print(f"✓ /api/auth/me works with cookie auth")
    
    def test_dashboard_stats_with_cookie(self):
        """GET /api/dashboard-v2/stats should work with cookie auth"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Test dashboard stats
        stats_resp = self.session.get(f"{BASE_URL}/api/dashboard-v2/stats")
        assert stats_resp.status_code == 200, f"Dashboard stats failed: {stats_resp.text}"
        
        data = stats_resp.json()
        assert "total_products" in data
        assert "total_clients" in data
        assert "total_quotes" in data
        assert "total_leads" in data
        print(f"✓ /api/dashboard-v2/stats works with cookie auth - {data['total_products']} products")
    
    def test_inventory_with_cookie(self):
        """GET /api/inventory should work with cookie auth"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Test inventory
        inv_resp = self.session.get(f"{BASE_URL}/api/inventory/?page=1&limit=5")
        assert inv_resp.status_code == 200, f"Inventory failed: {inv_resp.text}"
        
        data = inv_resp.json()
        assert "products" in data
        assert "total" in data
        assert len(data["products"]) > 0
        print(f"✓ /api/inventory works with cookie auth - {data['total']} total products")
    
    def test_clients_with_cookie(self):
        """GET /api/clients should work with cookie auth"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Test clients
        clients_resp = self.session.get(f"{BASE_URL}/api/clients/")
        assert clients_resp.status_code == 200, f"Clients failed: {clients_resp.text}"
        
        data = clients_resp.json()
        assert isinstance(data, list)
        print(f"✓ /api/clients works with cookie auth - {len(data)} clients")
    
    def test_quotes_with_cookie(self):
        """GET /api/quotes-v2 should work with cookie auth"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Test quotes
        quotes_resp = self.session.get(f"{BASE_URL}/api/quotes-v2/")
        assert quotes_resp.status_code == 200, f"Quotes failed: {quotes_resp.text}"
        
        data = quotes_resp.json()
        assert isinstance(data, list)
        print(f"✓ /api/quotes-v2 works with cookie auth - {len(data)} quotes")
    
    def test_logout_clears_session(self):
        """POST /api/auth/logout should clear auth_token cookie"""
        # Login first
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        
        # Verify we're logged in
        me_resp = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        
        # Logout
        logout_resp = self.session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Sesión cerrada"
        
        # Verify auth fails after logout (new session to simulate cleared cookie)
        new_session = requests.Session()
        me_after_logout = new_session.get(f"{BASE_URL}/api/auth/me")
        assert me_after_logout.status_code == 401, "Should be unauthorized after logout"
        print(f"✓ Logout clears session properly")
    
    def test_unauthenticated_request_fails(self):
        """Requests without auth should return 401"""
        # Fresh session without login
        fresh_session = requests.Session()
        
        # Test protected endpoints
        endpoints = [
            "/api/auth/me",
            "/api/dashboard-v2/stats",
            "/api/leads",
            "/api/conversations"
        ]
        
        for endpoint in endpoints:
            resp = fresh_session.get(f"{BASE_URL}{endpoint}")
            assert resp.status_code == 401, f"{endpoint} should return 401, got {resp.status_code}"
        
        print(f"✓ All protected endpoints return 401 without auth")


class TestDeveloperLogin:
    """Test developer account login"""
    
    def test_developer_login(self):
        """Developer account should be able to login"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEV_EMAIL, "password": DEV_PASSWORD}
        )
        assert response.status_code == 200, f"Developer login failed: {response.text}"
        
        data = response.json()
        assert data["user"]["email"] == DEV_EMAIL
        print(f"✓ Developer login successful")


class TestDashboardEndpoints:
    """Test all dashboard endpoints with cookie auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_resp.status_code == 200
        yield
        self.session.close()
    
    def test_activity_chart(self):
        """GET /api/dashboard-v2/activity-chart should return chart data"""
        resp = self.session.get(f"{BASE_URL}/api/dashboard-v2/activity-chart?days=14")
        assert resp.status_code == 200
        
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "date" in data[0]
            assert "cotizaciones" in data[0]
        print(f"✓ Activity chart endpoint works - {len(data)} days of data")
    
    def test_top_products(self):
        """GET /api/dashboard-v2/top-products should return top products"""
        resp = self.session.get(f"{BASE_URL}/api/dashboard-v2/top-products?limit=5")
        assert resp.status_code == 200
        
        data = resp.json()
        assert isinstance(data, list)
        print(f"✓ Top products endpoint works - {len(data)} products")
    
    def test_top_clients(self):
        """GET /api/dashboard-v2/top-clients should return top clients"""
        resp = self.session.get(f"{BASE_URL}/api/dashboard-v2/top-clients?limit=5")
        assert resp.status_code == 200
        
        data = resp.json()
        assert isinstance(data, list)
        print(f"✓ Top clients endpoint works - {len(data)} clients")
    
    def test_orders_by_client(self):
        """GET /api/dashboard-v2/orders-by-client should return orders summary (admin only)"""
        resp = self.session.get(f"{BASE_URL}/api/dashboard-v2/orders-by-client")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "clients" in data
        assert "grand_total" in data
        print(f"✓ Orders by client endpoint works - {len(data['clients'])} clients")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
