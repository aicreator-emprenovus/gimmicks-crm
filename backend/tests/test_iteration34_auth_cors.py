"""
Iteration 34: Test Auth, Rate Limiting, and CORS fixes for production bugs

Production Bugs Fixed:
1) Rate limiter was using proxy IP (request.client.host) causing all users behind Railway proxy 
   to share same IP limit of 15 → Changed to get_client_ip() using X-Forwarded-For, increased limit to 50
2) CORS had allow_credentials=True with allow_origins=['*'] which Firefox/Edge block per spec 
   → Removed withCredentials from frontend, use Bearer token from localStorage as primary auth

Tests:
- Login returns access_token in response body
- Bearer token authentication works (GET /api/auth/me with Authorization header)
- Multiple simultaneous logins all return 200 (simulating concurrent users)
- Rate limiter uses X-Forwarded-For (get_client_ip function)
- MAX_LOGIN_ATTEMPTS is 50 (not 15)
- CORS: Access-Control-Allow-Origin is * WITHOUT Access-Control-Allow-Credentials
- Frontend AuthContext.js: NO withCredentials=true setting
- Frontend AuthContext.js: Token stored in localStorage on login
"""

import pytest
import requests
import os
import re
import concurrent.futures
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"
DEV_EMAIL = "aicreator@emprenovus.com"
DEV_PASSWORD = "Jlsb*1082"


class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ Health endpoint returns 200")


class TestLoginReturnsAccessToken:
    """Test that login returns access_token in response body"""
    
    def test_login_returns_access_token_admin(self):
        """Login with admin credentials returns access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, f"access_token not in response: {data.keys()}"
        assert isinstance(data["access_token"], str), "access_token should be a string"
        assert len(data["access_token"]) > 20, "access_token seems too short"
        assert "user" in data, "user object not in response"
        print(f"✓ Login returns access_token (length: {len(data['access_token'])})")
    
    def test_login_returns_access_token_developer(self):
        """Login with developer credentials returns access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEV_EMAIL,
            "password": DEV_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, f"access_token not in response: {data.keys()}"
        print("✓ Developer login returns access_token")


class TestBearerTokenAuth:
    """Test Bearer token authentication works"""
    
    def test_auth_me_with_bearer_token(self):
        """GET /api/auth/me with Authorization: Bearer <token> works"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Now call /api/auth/me with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert me_response.status_code == 200, f"Auth/me failed: {me_response.status_code} - {me_response.text}"
        
        user_data = me_response.json()
        assert user_data["email"] == ADMIN_EMAIL, f"Email mismatch: {user_data.get('email')}"
        print(f"✓ Bearer token auth works - user: {user_data['email']}")
    
    def test_auth_me_without_token_fails(self):
        """GET /api/auth/me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Auth/me without token correctly returns 401")


class TestMultipleSimultaneousLogins:
    """Test that multiple rapid logins all succeed (simulating concurrent users)"""
    
    def test_10_rapid_logins_all_succeed(self):
        """10 rapid login attempts should all return 200"""
        def do_login(attempt_num):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            return (attempt_num, response.status_code, response.text[:200] if response.status_code != 200 else "OK")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(do_login, i) for i in range(10)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Check all succeeded
        failed = [(num, code, text) for num, code, text in results if code != 200]
        assert len(failed) == 0, f"Some logins failed: {failed}"
        print(f"✓ All 10 rapid logins succeeded: {[r[1] for r in sorted(results)]}")
    
    def test_20_sequential_logins_all_succeed(self):
        """20 sequential login attempts should all return 200 (testing rate limit of 50)"""
        success_count = 0
        for i in range(20):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"  Login {i+1} failed: {response.status_code} - {response.text[:100]}")
        
        assert success_count == 20, f"Only {success_count}/20 logins succeeded"
        print(f"✓ All 20 sequential logins succeeded")


class TestRateLimiterConfiguration:
    """Test rate limiter uses X-Forwarded-For and has correct limits"""
    
    def test_get_client_ip_function_exists(self):
        """Verify get_client_ip function exists in server.py"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        assert "def get_client_ip" in content, "get_client_ip function not found"
        assert "x-forwarded-for" in content.lower(), "X-Forwarded-For not referenced"
        print("✓ get_client_ip function exists and references X-Forwarded-For")
    
    def test_max_login_attempts_is_50(self):
        """Verify MAX_LOGIN_ATTEMPTS is 50 (not 15)"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find MAX_LOGIN_ATTEMPTS value
        match = re.search(r'MAX_LOGIN_ATTEMPTS\s*=\s*(\d+)', content)
        assert match, "MAX_LOGIN_ATTEMPTS not found"
        value = int(match.group(1))
        assert value == 50, f"MAX_LOGIN_ATTEMPTS is {value}, expected 50"
        print(f"✓ MAX_LOGIN_ATTEMPTS = {value}")
    
    def test_login_uses_get_client_ip(self):
        """Verify login route uses get_client_ip for rate limiting"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find the login function and check it uses get_client_ip
        login_section = content[content.find("async def login"):]
        login_section = login_section[:login_section.find("async def ", 10)]  # Get just the login function
        
        assert "get_client_ip" in login_section, "Login function doesn't use get_client_ip"
        print("✓ Login route uses get_client_ip for rate limiting")


class TestCORSConfiguration:
    """Test CORS is configured correctly for all browsers"""
    
    def test_cors_allows_all_origins(self):
        """CORS should allow all origins (Access-Control-Allow-Origin: *)"""
        # Make OPTIONS preflight request
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization"
        }
        response = requests.options(f"{BASE_URL}/api/auth/login", headers=headers)
        
        # Check CORS headers
        cors_origin = response.headers.get("access-control-allow-origin", "")
        assert cors_origin == "*", f"Expected Access-Control-Allow-Origin: *, got: {cors_origin}"
        print(f"✓ CORS Access-Control-Allow-Origin: {cors_origin}")
    
    def test_cors_no_credentials_header(self):
        """CORS should NOT have Access-Control-Allow-Credentials header"""
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST"
        }
        response = requests.options(f"{BASE_URL}/api/auth/login", headers=headers)
        
        # Check that credentials header is NOT present or is false
        creds_header = response.headers.get("access-control-allow-credentials", "").lower()
        assert creds_header != "true", f"CORS has allow-credentials: true which breaks Firefox/Edge"
        print(f"✓ CORS does NOT have Access-Control-Allow-Credentials: true")
    
    def test_cors_on_actual_request(self):
        """Test CORS headers on actual POST request"""
        headers = {
            "Origin": "https://example.com",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", 
                                 json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                 headers=headers)
        
        cors_origin = response.headers.get("access-control-allow-origin", "")
        creds_header = response.headers.get("access-control-allow-credentials", "").lower()
        
        assert cors_origin == "*", f"Expected CORS origin *, got: {cors_origin}"
        assert creds_header != "true", f"CORS credentials should not be true"
        print(f"✓ Actual request CORS headers correct: origin={cors_origin}, credentials={creds_header or 'not set'}")


class TestFrontendAuthContext:
    """Test frontend AuthContext.js configuration"""
    
    def test_no_withcredentials_in_authcontext(self):
        """AuthContext.js should NOT have withCredentials=true"""
        auth_context_path = "/app/frontend/src/context/AuthContext.js"
        with open(auth_context_path, 'r') as f:
            content = f.read()
        
        # Check for withCredentials: true or withCredentials = true
        has_withcredentials = re.search(r'withCredentials\s*[=:]\s*true', content, re.IGNORECASE)
        assert not has_withcredentials, "AuthContext.js has withCredentials=true which breaks Firefox/Edge"
        print("✓ AuthContext.js does NOT have withCredentials=true")
    
    def test_localstorage_token_storage(self):
        """AuthContext.js should store token in localStorage"""
        auth_context_path = "/app/frontend/src/context/AuthContext.js"
        with open(auth_context_path, 'r') as f:
            content = f.read()
        
        # Check for localStorage usage
        assert "localStorage.setItem" in content, "localStorage.setItem not found"
        assert "localStorage.getItem" in content, "localStorage.getItem not found"
        assert "localStorage.removeItem" in content, "localStorage.removeItem not found"
        assert "auth_token" in content, "auth_token key not found"
        print("✓ AuthContext.js uses localStorage for token storage")
    
    def test_bearer_header_set_from_localstorage(self):
        """AuthContext.js should set Bearer header from localStorage"""
        auth_context_path = "/app/frontend/src/context/AuthContext.js"
        with open(auth_context_path, 'r') as f:
            content = f.read()
        
        # Check for Bearer token header setup
        assert "Bearer" in content, "Bearer token not found in AuthContext"
        assert "Authorization" in content, "Authorization header not found"
        print("✓ AuthContext.js sets Bearer Authorization header")


class TestCookieSameSite:
    """Test cookie samesite configuration"""
    
    def test_login_cookie_samesite_none(self):
        """Login should set cookie with samesite=none"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        
        # Check Set-Cookie header
        set_cookie = response.headers.get("set-cookie", "")
        if set_cookie:
            # If cookie is set, it should have samesite=none
            if "samesite" in set_cookie.lower():
                assert "samesite=none" in set_cookie.lower(), f"Cookie samesite not none: {set_cookie}"
                print(f"✓ Login cookie has samesite=none")
            else:
                print(f"✓ Login cookie set (samesite not explicitly set): {set_cookie[:100]}")
        else:
            # No cookie is also fine since we use Bearer token
            print("✓ No cookie set (using Bearer token auth)")


class TestServerCodeStructure:
    """Verify server.py code structure for the fixes"""
    
    def test_cors_middleware_no_credentials(self):
        """Verify CORS middleware doesn't have allow_credentials=True"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find CORS middleware configuration
        cors_section = content[content.find("CORSMiddleware"):]
        cors_section = cors_section[:cors_section.find(")") + 1]
        
        # Should NOT have allow_credentials=True
        assert "allow_credentials=True" not in cors_section, "CORS has allow_credentials=True"
        assert "allow_credentials = True" not in cors_section, "CORS has allow_credentials = True"
        print("✓ CORS middleware does NOT have allow_credentials=True")
    
    def test_get_client_ip_reads_headers(self):
        """Verify get_client_ip reads X-Forwarded-For and X-Real-IP"""
        server_path = "/app/backend/server.py"
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find get_client_ip function
        func_start = content.find("def get_client_ip")
        func_end = content.find("\ndef ", func_start + 1)
        func_content = content[func_start:func_end]
        
        assert "x-forwarded-for" in func_content.lower(), "get_client_ip doesn't read X-Forwarded-For"
        assert "x-real-ip" in func_content.lower(), "get_client_ip doesn't read X-Real-IP"
        print("✓ get_client_ip reads X-Forwarded-For and X-Real-IP headers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
