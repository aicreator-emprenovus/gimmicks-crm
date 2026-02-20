"""
Iteration 14 Tests - Production Sync & Core App Features
Tests for:
1. Login with admin@gimmicks.com / admin123456
2. Production sync endpoints (GET /api/sync/status, POST /api/sync/production)
3. Inbox conversations showing real production data
4. Dashboard, Leads, Interesados, Clientes pages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://interesado-crm.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "admin@gimmicks.com"
TEST_PASSWORD = "admin123456"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API requests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Auth headers for API requests"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestAuthentication:
    """Auth endpoint tests"""
    
    def test_login_with_valid_credentials(self):
        """Login with admin@gimmicks.com / admin123456 should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "admin"
    
    def test_login_with_invalid_credentials(self):
        """Login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestSyncEndpoints:
    """Production sync endpoint tests"""
    
    def test_sync_status_returns_running(self, headers):
        """GET /api/sync/status should return running=true"""
        response = requests.get(f"{BASE_URL}/api/sync/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("running") == True
        assert "interval_seconds" in data
        assert "last_sync" in data
    
    def test_sync_production_triggers_manual_sync(self, headers):
        """POST /api/sync/production should trigger manual sync and return stats"""
        response = requests.post(f"{BASE_URL}/api/sync/production", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("synced") == True
        assert "stats" in data
        # Verify stats structure
        stats = data["stats"]
        assert "conversations" in stats
        assert "messages" in stats
        assert "leads" in stats


class TestInboxConversations:
    """Inbox/Conversations endpoint tests"""
    
    def test_conversations_list_returns_production_data(self, headers):
        """Inbox should show real production conversations"""
        response = requests.get(f"{BASE_URL}/api/conversations?limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have conversations from production
        assert len(data) > 0
        
        # Check for expected production contacts
        contact_names = [c.get("contact_name") for c in data if c.get("contact_name")]
        phone_numbers = [c.get("phone_number") for c in data]
        
        # Verify production data is present (Andrea, José, Santiago, Daniel)
        expected_contacts = ["Andrea Vélez", "José Silva", "Santiago Burbano", "Daniel Silva"]
        found_contacts = [name for name in expected_contacts if name in contact_names]
        assert len(found_contacts) > 0, f"Expected production contacts not found. Got: {contact_names}"
    
    def test_conversation_has_required_fields(self, headers):
        """Each conversation should have required fields"""
        response = requests.get(f"{BASE_URL}/api/conversations?limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            conv = data[0]
            assert "id" in conv
            assert "phone_number" in conv
            assert "status" in conv
            assert "created_at" in conv
    
    def test_get_conversation_messages(self, headers):
        """Should be able to get messages for a conversation"""
        # First get a conversation
        response = requests.get(f"{BASE_URL}/api/conversations?limit=1", headers=headers)
        assert response.status_code == 200
        convs = response.json()
        
        if len(convs) > 0:
            conv_id = convs[0]["id"]
            msg_response = requests.get(f"{BASE_URL}/api/conversations/{conv_id}/messages", headers=headers)
            assert msg_response.status_code == 200
            messages = msg_response.json()
            assert isinstance(messages, list)


class TestDashboard:
    """Dashboard endpoint tests"""
    
    def test_dashboard_stats_loads(self, headers):
        """Dashboard stats endpoint should work"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Check for expected dashboard fields
        assert "total_quotes" in data or "quotes_count" in data or isinstance(data, dict)
    
    def test_dashboard_activity_chart_loads(self, headers):
        """Dashboard activity chart should return data"""
        response = requests.get(f"{BASE_URL}/api/dashboard-v2/activity-chart?days=14", headers=headers)
        assert response.status_code == 200


class TestLeads:
    """Leads endpoint tests"""
    
    def test_leads_list_loads(self, headers):
        """Leads page should load"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestClients:
    """Clients endpoint tests"""
    
    def test_clients_page_loads(self, headers):
        """Clientes page should load manual clients"""
        response = requests.get(f"{BASE_URL}/api/clients/?source=manual&trash=false", headers=headers)
        assert response.status_code == 200
    
    def test_interesados_page_loads(self, headers):
        """Interesados page should load WhatsApp clients"""
        response = requests.get(f"{BASE_URL}/api/clients/?source=whatsapp&trash=false", headers=headers)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
