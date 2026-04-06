"""
Iteration 21: Cookie-based Authentication Testing
Tests the httpOnly cookie auth migration from localStorage JWT.
Focus: Login, session persistence, logout, protected routes, page refresh behavior.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"
DEVELOPER_EMAIL = "aicreator@emprenovus.com"
DEVELOPER_PASSWORD = "Jlsb*1082"


class TestLoginFlow:
    """Test login endpoint returns 200 with Set-Cookie header"""
    
    def test_login_success_returns_200_with_cookie(self):
        """POST /api/auth/login should return 200 with Set-Cookie header containing auth_token"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Set-Cookie header
        set_cookie = response.headers.get('Set-Cookie', '')
        assert 'auth_token=' in set_cookie, f"Expected auth_token in Set-Cookie header, got: {set_cookie}"
        
        # Verify cookie attributes
        assert 'HttpOnly' in set_cookie or 'httponly' in set_cookie.lower(), "Cookie should be HttpOnly"
        assert 'Secure' in set_cookie or 'secure' in set_cookie.lower(), "Cookie should be Secure"
        assert 'SameSite' in set_cookie or 'samesite' in set_cookie.lower(), "Cookie should have SameSite"
        
        # Verify response data
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Login success: Set-Cookie header contains auth_token with HttpOnly, Secure, SameSite")
    
    def test_login_invalid_credentials_returns_401(self):
        """POST /api/auth/login with wrong password should return 401"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrongpassword"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials returns 401")
    
    def test_developer_login_success(self):
        """Developer account should also work"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEVELOPER_EMAIL, "password": DEVELOPER_PASSWORD}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["user"]["email"] == DEVELOPER_EMAIL
        assert data["user"]["role"] == "desarrollador"
        print(f"✓ Developer login success: {DEVELOPER_EMAIL}")


class TestSessionPersistence:
    """Test session persistence with cookie-based auth"""
    
    @pytest.fixture
    def authenticated_session(self):
        """Create an authenticated session"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return session
    
    def test_auth_me_with_cookie(self, authenticated_session):
        """GET /api/auth/me should return user data with cookie auth"""
        response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert "id" in data
        assert "name" in data
        assert "role" in data
        print(f"✓ GET /api/auth/me works with cookie auth: {data['email']}")
    
    def test_auth_me_without_cookie_returns_401(self):
        """GET /api/auth/me without cookie should return 401"""
        session = requests.Session()  # Fresh session, no cookie
        response = session.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/auth/me without cookie returns 401")


class TestProtectedRoutes:
    """Test protected routes work with cookie auth"""
    
    @pytest.fixture
    def authenticated_session(self):
        """Create an authenticated session"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return session
    
    def test_leads_endpoint_with_cookie(self, authenticated_session):
        """GET /api/leads should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/leads")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Leads should be a list"
        print(f"✓ GET /api/leads works with cookie auth: {len(data)} leads")
    
    def test_conversations_endpoint_with_cookie(self, authenticated_session):
        """GET /api/conversations should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/conversations")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Conversations should be a list"
        print(f"✓ GET /api/conversations works with cookie auth: {len(data)} conversations")
    
    def test_products_endpoint_with_cookie(self, authenticated_session):
        """GET /api/products should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/products")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "products" in data, "Response should contain products"
        print(f"✓ GET /api/products works with cookie auth: {len(data['products'])} products")
    
    def test_dashboard_stats_with_cookie(self, authenticated_session):
        """GET /api/dashboard-v2/stats should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/dashboard-v2/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total_products" in data or "products" in data or isinstance(data, dict), "Should return stats"
        print(f"✓ GET /api/dashboard-v2/stats works with cookie auth")
    
    def test_inventory_endpoint_with_cookie(self, authenticated_session):
        """GET /api/inventory should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/inventory/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/inventory works with cookie auth")
    
    def test_clients_endpoint_with_cookie(self, authenticated_session):
        """GET /api/clients should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/clients/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/clients works with cookie auth")
    
    def test_quotes_endpoint_with_cookie(self, authenticated_session):
        """GET /api/quotes-v2 should return 200 with valid auth cookie"""
        response = authenticated_session.get(f"{BASE_URL}/api/quotes-v2/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/quotes-v2 works with cookie auth")


class TestLogout:
    """Test logout clears the cookie"""
    
    def test_logout_clears_cookie(self):
        """POST /api/auth/logout should clear the auth_token cookie"""
        session = requests.Session()
        
        # First login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200
        
        # Verify we're authenticated
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        
        # Logout
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200, f"Expected 200, got {logout_response.status_code}"
        
        # Check Set-Cookie header clears the cookie
        set_cookie = logout_response.headers.get('Set-Cookie', '')
        # Cookie should be deleted (max-age=0 or expires in past)
        print(f"Logout Set-Cookie: {set_cookie}")
        
        # Verify we're no longer authenticated
        me_response_after = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response_after.status_code == 401, f"Expected 401 after logout, got {me_response_after.status_code}"
        print("✓ POST /api/auth/logout clears cookie, subsequent /api/auth/me returns 401")


class TestSessionPersistenceAcrossRequests:
    """Test that session persists across multiple requests (simulating page refresh)"""
    
    def test_session_persists_across_multiple_requests(self):
        """After login, multiple requests should all succeed with the same session"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200
        
        # Make multiple requests (simulating page navigation)
        endpoints = [
            "/api/auth/me",
            "/api/dashboard-v2/stats",
            "/api/leads",
            "/api/conversations",
            "/api/auth/me",  # Check again (simulating page refresh)
        ]
        
        for endpoint in endpoints:
            response = session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Expected 200 for {endpoint}, got {response.status_code}"
        
        print(f"✓ Session persists across {len(endpoints)} requests (simulating page refresh)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
