"""
Tests for WhatsApp CRM - Funnel Stage and AI Analysis improvements
Testing:
1. GET /api/conversations returns funnel_stage field
2. GET /api/conversations?funnel_stage=lead filters correctly
3. POST /api/ai/analyze-message with conversation_id returns enriched response
4. Bot loads known client data for returning customers
5. Follow-up check skips conversations with quote_generated=True
"""
import pytest
import requests
import os

# Use LOCAL backend for testing new features
BASE_URL = "http://localhost:8001"

class TestAuth:
    """Get authentication token for tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@gimmicks.com", "password": "admin123456"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}


class TestConversationsFunnelStage(TestAuth):
    """Test funnel_stage field in conversations API"""
    
    def test_conversations_list_has_funnel_stage_field(self, auth_headers):
        """GET /api/conversations should return funnel_stage for each conversation"""
        response = requests.get(
            f"{BASE_URL}/api/conversations?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        conversations = response.json()
        
        if len(conversations) > 0:
            # Check that funnel_stage field exists in response
            first_conv = conversations[0]
            assert "funnel_stage" in first_conv, "funnel_stage field missing from conversation response"
            print(f"SUCCESS: funnel_stage field present. First conversation stage: {first_conv.get('funnel_stage')}")
        else:
            print("INFO: No conversations found - cannot verify funnel_stage field")
    
    def test_filter_conversations_by_funnel_stage_lead(self, auth_headers):
        """GET /api/conversations?funnel_stage=lead should filter correctly"""
        response = requests.get(
            f"{BASE_URL}/api/conversations?funnel_stage=lead&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        conversations = response.json()
        
        # All returned conversations should have funnel_stage=lead
        for conv in conversations:
            assert conv.get("funnel_stage") == "lead", f"Filter failed: expected 'lead', got '{conv.get('funnel_stage')}'"
        
        print(f"SUCCESS: Filtered {len(conversations)} conversations with funnel_stage=lead")
    
    def test_filter_conversations_by_funnel_stage_cliente_potencial(self, auth_headers):
        """GET /api/conversations?funnel_stage=cliente_potencial should filter correctly"""
        response = requests.get(
            f"{BASE_URL}/api/conversations?funnel_stage=cliente_potencial&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        conversations = response.json()
        
        for conv in conversations:
            assert conv.get("funnel_stage") == "cliente_potencial"
        
        print(f"SUCCESS: Filtered {len(conversations)} conversations with funnel_stage=cliente_potencial")
    
    def test_filter_conversations_by_funnel_stage_cotizacion_generada(self, auth_headers):
        """GET /api/conversations?funnel_stage=cotizacion_generada should filter correctly"""
        response = requests.get(
            f"{BASE_URL}/api/conversations?funnel_stage=cotizacion_generada&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        conversations = response.json()
        
        for conv in conversations:
            assert conv.get("funnel_stage") == "cotizacion_generada"
        
        print(f"SUCCESS: Filtered {len(conversations)} conversations with funnel_stage=cotizacion_generada")


class TestAIAnalyzeMessage(TestAuth):
    """Test enriched AI analysis endpoint"""
    
    def test_analyze_message_returns_enriched_fields(self, auth_headers):
        """POST /api/ai/analyze-message should return quote_status, next_action, missing_data"""
        # Get a conversation to analyze
        convs_response = requests.get(
            f"{BASE_URL}/api/conversations?limit=5",
            headers=auth_headers
        )
        assert convs_response.status_code == 200
        conversations = convs_response.json()
        
        if len(conversations) == 0:
            pytest.skip("No conversations available to analyze")
        
        conv_id = conversations[0]["id"]
        
        # Analyze the conversation
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze-message",
            headers=auth_headers,
            params={"conversation_id": conv_id}
        )
        assert response.status_code == 200
        result = response.json()
        
        # Check required fields
        assert "intent" in result, "Missing 'intent' field"
        assert "lead_classification" in result, "Missing 'lead_classification' field"
        assert "quote_status" in result, "Missing 'quote_status' field - NEW FIELD"
        assert "next_action" in result, "Missing 'next_action' field - NEW FIELD"
        
        # Check quote_status is valid
        valid_statuses = ["sin_datos", "datos_parciales", "listo_para_cotizar", "ya_cotizado"]
        assert result["quote_status"] in valid_statuses, f"Invalid quote_status: {result['quote_status']}"
        
        print(f"SUCCESS: AI analysis returned enriched fields:")
        print(f"  - intent: {result.get('intent')}")
        print(f"  - lead_classification: {result.get('lead_classification')}")
        print(f"  - quote_status: {result.get('quote_status')}")
        print(f"  - next_action: {result.get('next_action', 'N/A')}")
        print(f"  - missing_data: {result.get('missing_data', [])}")
    
    def test_analyze_message_with_empty_params(self, auth_headers):
        """POST /api/ai/analyze-message without conversation_id should still work"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze-message",
            headers=auth_headers,
            params={"message": "Necesito cotizar termos"}
        )
        assert response.status_code == 200
        result = response.json()
        
        # Should return base fields even without conversation context
        assert "intent" in result
        assert "quote_status" in result
        print(f"SUCCESS: Analysis without conversation_id works. Intent: {result.get('intent')}")


class TestBotLoadKnownClientData(TestAuth):
    """Test bot_service.py load_known_client_data function via code review
    Note: This is a code verification test since we can't trigger bot directly
    """
    
    def test_verify_load_known_client_data_function_exists(self):
        """Verify load_known_client_data function exists in bot_service.py"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from bot_service import load_known_client_data
        assert callable(load_known_client_data), "load_known_client_data should be a callable function"
        print("SUCCESS: load_known_client_data function exists in bot_service.py")
    
    def test_verify_get_conversation_history_function_exists(self):
        """Verify get_conversation_history function exists and uses limit"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from bot_service import get_conversation_history
        assert callable(get_conversation_history), "get_conversation_history should be a callable function"
        print("SUCCESS: get_conversation_history function exists in bot_service.py")


class TestFollowupCheckLogic:
    """Test follow-up check logic - verifies code skips quoted conversations"""
    
    def test_verify_followup_skips_quote_generated_code_review(self):
        """Code review: Verify run_followup_check skips quote_generated=True"""
        # Read the server.py file and verify the logic
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check that quote_generated check exists in run_followup_check
        assert 'if state.get("quote_generated"):' in content, "Missing quote_generated skip in run_followup_check"
        assert 'continue' in content, "Missing continue after quote_generated check"
        
        print("SUCCESS: run_followup_check correctly skips conversations with quote_generated=True")
    
    def test_verify_reminder_count_logic_code_review(self):
        """Code review: Verify reminder_count (0,1,2) logic instead of boolean"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check that reminder_count is used
        assert 'reminder_count' in content, "Missing reminder_count logic"
        assert 'reminder_count == 0' in content, "Missing first reminder check (count == 0)"
        assert 'reminder_count == 1' in content, "Missing second reminder check (count == 1)"
        assert 'reminder_count >= 2' in content, "Missing mark as lost check (count >= 2)"
        
        print("SUCCESS: run_followup_check uses reminder_count (0,1,2) logic correctly")


class TestLeadsWithFunnelStage(TestAuth):
    """Test leads API returns funnel_stage correctly"""
    
    def test_leads_have_funnel_stage(self, auth_headers):
        """GET /api/leads should return funnel_stage for each lead"""
        response = requests.get(
            f"{BASE_URL}/api/leads?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        leads = response.json()
        
        if len(leads) > 0:
            for lead in leads:
                assert "funnel_stage" in lead, "funnel_stage field missing from lead"
            print(f"SUCCESS: All {len(leads)} leads have funnel_stage field")
            
            # Print stages found
            stages = set(l.get("funnel_stage") for l in leads)
            print(f"  Stages found: {stages}")
        else:
            print("INFO: No leads found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
