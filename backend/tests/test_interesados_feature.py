"""
Test suite for Interesados feature - Iteration 13
Tests separation of WhatsApp clients (Interesados) from manual clients
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://catalog-pdf-fix.preview.emergentagent.com')

class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """POST /api/auth/login returns 200 with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@gimmicks.com"
        print("✓ Login successful with admin@gimmicks.com")

    def test_login_invalid_credentials(self):
        """POST /api/auth/login returns 401 for invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("✓ Login correctly rejects invalid credentials")


@pytest.fixture
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@gimmicks.com",
        "password": "admin123456"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def headers(auth_token):
    """Session with auth header"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestClientsSourceFilter:
    """Test client filtering by source"""
    
    def test_get_manual_clients(self, headers):
        """GET /api/clients/?source=manual&trash=false returns only manual clients"""
        response = requests.get(f"{BASE_URL}/api/clients/", 
                               params={"source": "manual", "trash": False},
                               headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All clients should have source=manual
        for client in data:
            assert client.get("source") == "manual", f"Client {client['name']} has source={client.get('source')}, expected manual"
        print(f"✓ Found {len(data)} manual clients, all have source=manual")
    
    def test_get_whatsapp_clients(self, headers):
        """GET /api/clients/?source=whatsapp&trash=false returns only WhatsApp clients"""
        response = requests.get(f"{BASE_URL}/api/clients/", 
                               params={"source": "whatsapp", "trash": False},
                               headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All clients should have source=whatsapp
        for client in data:
            assert client.get("source") == "whatsapp", f"Client {client['name']} has source={client.get('source')}, expected whatsapp"
        print(f"✓ Found {len(data)} WhatsApp clients (interesados), all have source=whatsapp")


class TestPromoteEndpoint:
    """Test promote endpoint functionality"""
    
    def test_promote_already_manual_returns_400(self, headers):
        """POST /api/clients/{id}/promote returns 400 if already manual"""
        # First, get a manual client
        response = requests.get(f"{BASE_URL}/api/clients/", 
                               params={"source": "manual", "trash": False},
                               headers=headers)
        assert response.status_code == 200
        manual_clients = response.json()
        if not manual_clients:
            pytest.skip("No manual clients available to test")
        
        manual_client_id = manual_clients[0]["id"]
        
        # Try to promote an already-manual client
        promote_response = requests.post(f"{BASE_URL}/api/clients/{manual_client_id}/promote",
                                         json={},
                                         headers=headers)
        assert promote_response.status_code == 400
        assert "ya es un cliente" in promote_response.json().get("detail", "").lower()
        print(f"✓ Promoting already-manual client correctly returns 400")
    
    def test_promote_nonexistent_client_returns_404(self, headers):
        """POST /api/clients/{id}/promote returns 404 for nonexistent client"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(f"{BASE_URL}/api/clients/{fake_id}/promote",
                                json={},
                                headers=headers)
        assert response.status_code == 404
        print(f"✓ Promoting nonexistent client correctly returns 404")


class TestClientModel:
    """Test client model has source field"""
    
    def test_client_has_source_field(self, headers):
        """Verify clients have source field with valid values"""
        # Get all clients without source filter
        response = requests.get(f"{BASE_URL}/api/clients/", 
                               params={"trash": False},
                               headers=headers)
        assert response.status_code == 200
        data = response.json()
        if not data:
            pytest.skip("No clients available")
        
        for client in data:
            assert "source" in client, f"Client {client['name']} missing source field"
            assert client["source"] in ["manual", "whatsapp"], f"Client {client['name']} has invalid source={client['source']}"
        print(f"✓ All {len(data)} clients have valid source field (manual or whatsapp)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
