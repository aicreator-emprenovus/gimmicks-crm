"""
Test iteration 11: Verify emergentintegrations LLM usage and real-time polling functionality
Tests:
1. Backend starts without import errors
2. Login API
3. GET /api/conversations
4. GET /api/conversations/{id}/messages
5. POST /api/ai/analyze-message (uses emergentintegrations LlmChat)
6. POST /api/ai/recommend-products (uses emergentintegrations LlmChat)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://interesado-crm.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "admin@gimmicks.com"
TEST_PASSWORD = "admin123456"


class TestAuthAndBasicAPIs:
    """Test authentication and basic conversation APIs"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers with token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_login_success(self):
        """Test login endpoint returns token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print("✓ Login successful")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpass"}
        )
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")
    
    def test_get_conversations(self, auth_headers):
        """Test GET /api/conversations returns list"""
        response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/conversations returned {len(data)} conversations")
        return data
    
    def test_get_conversation_messages(self, auth_headers):
        """Test GET /api/conversations/{id}/messages"""
        # First get conversations
        conv_response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        conversations = conv_response.json()
        
        if len(conversations) > 0:
            conv_id = conversations[0]["id"]
            msg_response = requests.get(
                f"{BASE_URL}/api/conversations/{conv_id}/messages",
                headers=auth_headers
            )
            assert msg_response.status_code == 200
            messages = msg_response.json()
            assert isinstance(messages, list)
            print(f"✓ GET /api/conversations/{conv_id}/messages returned {len(messages)} messages")
        else:
            pytest.skip("No conversations available to test messages")


class TestAIEndpoints:
    """Test AI endpoints that use emergentintegrations LlmChat"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers with token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = response.json()
        return {
            "Authorization": f"Bearer {data['access_token']}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def conversation_id(self, auth_headers):
        """Get a valid conversation ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        conversations = response.json()
        if len(conversations) > 0:
            return conversations[0]["id"]
        return None
    
    def test_analyze_message_endpoint(self, auth_headers, conversation_id):
        """Test POST /api/ai/analyze-message with emergentintegrations"""
        if not conversation_id:
            pytest.skip("No conversation ID available")
        
        # This endpoint uses emergentintegrations.llm.chat.LlmChat directly
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze-message",
            headers=auth_headers,
            params={
                "message": "Necesito cotizar 100 termos",
                "conversation_id": conversation_id
            }
        )
        
        # Should return 200 (not 500 due to import errors)
        assert response.status_code == 200, f"analyze-message failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "intent" in data or "lead_classification" in data, f"Missing expected fields in response: {data}"
        print(f"✓ POST /api/ai/analyze-message returned: {data.get('intent', 'N/A')}, classification: {data.get('lead_classification', 'N/A')}")
    
    def test_recommend_products_endpoint(self, auth_headers):
        """Test POST /api/ai/recommend-products with emergentintegrations"""
        # This endpoint uses emergentintegrations.llm.chat.LlmChat directly
        response = requests.post(
            f"{BASE_URL}/api/ai/recommend-products",
            headers=auth_headers,
            params={
                "query": "necesito regalos para navidad",
                "limit": 3
            }
        )
        
        # Should return 200 (not 500 due to import errors)
        assert response.status_code == 200, f"recommend-products failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "recommendations" in data or "products" in data or isinstance(data, list), f"Unexpected response format: {data}"
        recs = data.get("recommendations", data.get("products", data))
        print(f"✓ POST /api/ai/recommend-products returned {len(recs)} product recommendations")


class TestConversationDetails:
    """Test conversation-related functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        data = response.json()
        return {
            "Authorization": f"Bearer {data['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_conversation_includes_funnel_stage(self, auth_headers):
        """Verify conversations include funnel_stage for stage filter badges"""
        response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        assert response.status_code == 200
        conversations = response.json()
        
        if len(conversations) > 0:
            # At least one conversation should have funnel_stage field
            has_funnel_stage = any("funnel_stage" in c for c in conversations)
            assert has_funnel_stage or len(conversations) == 0, "Conversations missing funnel_stage field"
            
            # Count stages
            stages = {}
            for c in conversations:
                stage = c.get("funnel_stage", "unknown")
                stages[stage] = stages.get(stage, 0) + 1
            print(f"✓ Conversations have funnel_stage: {stages}")
        else:
            print("✓ No conversations to verify funnel_stage")
    
    def test_star_conversation(self, auth_headers):
        """Test star/unstar conversation functionality"""
        # Get conversations
        response = requests.get(
            f"{BASE_URL}/api/conversations",
            headers=auth_headers
        )
        conversations = response.json()
        
        if len(conversations) > 0:
            conv_id = conversations[0]["id"]
            
            # Toggle star
            star_response = requests.patch(
                f"{BASE_URL}/api/conversations/{conv_id}/star",
                headers=auth_headers
            )
            assert star_response.status_code == 200
            data = star_response.json()
            assert "is_starred" in data
            print(f"✓ Toggle star returned is_starred: {data['is_starred']}")
            
            # Toggle back
            requests.patch(
                f"{BASE_URL}/api/conversations/{conv_id}/star",
                headers=auth_headers
            )
        else:
            pytest.skip("No conversations available to test star")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
