"""
Iteration 38: WhatsApp Template Integration Tests

Tests for WhatsApp template functionality:
1. send_whatsapp_template function exists with correct signature
2. send_whatsapp_message_or_template function with 24h fallback logic
3. Reminder 1 (4h) uses template fallback with 'recordatorio_seguimiento_1'
4. Reminder 2 (23h) uses template fallback with 'recordatorio_seguimiento_2'
5. notify_staff_catalog_request catches 24h errors and uses 'alerta_producto_no_encontrado' template
6. Template payload structure verification
7. Backend health and automation rules API
"""

import pytest
import requests
import os
import ast
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://webhook-routing-2.preview.emergentagent.com').rstrip('/')


class TestHealthAndAuth:
    """Basic health and authentication tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy", f"Unexpected health status: {data}"
        print("✓ GET /api/health returns 200 with status=healthy")
    
    def test_admin_login(self):
        """Test admin login returns access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        print("✓ Admin login returns access_token")
        return data["access_token"]


class TestAutomationRulesAPI:
    """Test automation rules API returns expected rules"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        return response.json().get("access_token")
    
    def test_automation_rules_count(self, auth_token):
        """Test automation rules API returns rules (checking for 10 active + 3 inactive)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/automation-rules", headers=headers)
        assert response.status_code == 200, f"Failed to get rules: {response.text}"
        
        rules = response.json()
        active_rules = [r for r in rules if r.get("is_active", True)]
        inactive_rules = [r for r in rules if not r.get("is_active", True)]
        
        # We expect at least 10 active and 3 inactive rules
        print(f"  Total rules: {len(rules)}, Active: {len(active_rules)}, Inactive: {len(inactive_rules)}")
        assert len(active_rules) >= 10, f"Expected at least 10 active rules, got {len(active_rules)}"
        assert len(inactive_rules) >= 3, f"Expected at least 3 inactive rules, got {len(inactive_rules)}"
        print("✓ Automation rules API returns expected rule counts")


class TestSendWhatsAppTemplateFunction:
    """Test send_whatsapp_template function exists and has correct signature"""
    
    def test_function_exists_in_server(self):
        """Verify send_whatsapp_template function exists in server.py"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check function definition exists
        assert 'async def send_whatsapp_template(' in content, "send_whatsapp_template function not found"
        print("✓ send_whatsapp_template function exists in server.py")
    
    def test_function_signature(self):
        """Verify send_whatsapp_template accepts (to_phone, template_name, language_code, parameters)"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the function definition line
        match = re.search(r'async def send_whatsapp_template\([^)]+\)', content)
        assert match, "Could not find send_whatsapp_template function signature"
        
        signature = match.group()
        assert 'to_phone' in signature, "Missing to_phone parameter"
        assert 'template_name' in signature, "Missing template_name parameter"
        assert 'language_code' in signature, "Missing language_code parameter"
        assert 'parameters' in signature, "Missing parameters parameter"
        print(f"✓ send_whatsapp_template signature: {signature}")
    
    def test_template_payload_structure(self):
        """Verify template payload uses correct structure"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the send_whatsapp_template function
        func_start = content.find('async def send_whatsapp_template(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\n', func_start)
        
        func_content = content[func_start:func_end]
        
        # Check for required payload elements
        assert '"messaging_product": "whatsapp"' in func_content or "'messaging_product': 'whatsapp'" in func_content, \
            "Missing messaging_product='whatsapp' in payload"
        assert '"type": "template"' in func_content or "'type': 'template'" in func_content, \
            "Missing type='template' in payload"
        assert '"name": template_name' in func_content or "'name': template_name" in func_content, \
            "Missing template.name in payload"
        assert '"language"' in func_content, "Missing template.language in payload"
        assert '"code"' in func_content, "Missing language.code in payload"
        assert '"components"' in func_content, "Missing template.components in payload"
        print("✓ Template payload structure is correct (messaging_product, type, template.name, language.code, components)")


class TestSendWhatsAppMessageOrTemplateFunction:
    """Test send_whatsapp_message_or_template function with 24h fallback logic"""
    
    def test_function_exists(self):
        """Verify send_whatsapp_message_or_template function exists"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        assert 'async def send_whatsapp_message_or_template(' in content, \
            "send_whatsapp_message_or_template function not found"
        print("✓ send_whatsapp_message_or_template function exists in server.py")
    
    def test_function_signature(self):
        """Verify function accepts (to_phone, message_text, template_name, template_params)"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        match = re.search(r'async def send_whatsapp_message_or_template\([^)]+\)', content)
        assert match, "Could not find send_whatsapp_message_or_template function signature"
        
        signature = match.group()
        assert 'to_phone' in signature, "Missing to_phone parameter"
        assert 'message_text' in signature, "Missing message_text parameter"
        assert 'template_name' in signature, "Missing template_name parameter"
        assert 'template_params' in signature, "Missing template_params parameter"
        print(f"✓ send_whatsapp_message_or_template signature: {signature}")
    
    def test_tries_regular_message_first(self):
        """Verify function tries send_whatsapp_message first"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def send_whatsapp_message_or_template(')
        func_end = content.find('\nasync def ', func_start + 1)
        func_content = content[func_start:func_end]
        
        # Check that it calls send_whatsapp_message first
        assert 'await send_whatsapp_message(' in func_content, \
            "Function should call send_whatsapp_message first"
        print("✓ send_whatsapp_message_or_template tries regular message first")
    
    def test_catches_24h_errors(self):
        """Verify function catches 131047/131026/24h errors"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def send_whatsapp_message_or_template(')
        func_end = content.find('\nasync def ', func_start + 1)
        func_content = content[func_start:func_end]
        
        # Check for error detection
        assert '131047' in func_content, "Missing 131047 error detection"
        assert '131026' in func_content, "Missing 131026 error detection"
        assert '24 hour' in func_content.lower() or '24h' in func_content.lower(), \
            "Missing 24 hour error detection"
        assert 're-engagement' in func_content.lower(), "Missing re-engagement error detection"
        print("✓ Function catches 131047, 131026, 24 hour, and re-engagement errors")
    
    def test_falls_back_to_template(self):
        """Verify function falls back to send_whatsapp_template on 24h error"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def send_whatsapp_message_or_template(')
        func_end = content.find('\nasync def ', func_start + 1)
        func_content = content[func_start:func_end]
        
        # Check that it calls send_whatsapp_template as fallback
        assert 'await send_whatsapp_template(' in func_content, \
            "Function should fall back to send_whatsapp_template"
        print("✓ Function falls back to send_whatsapp_template on 24h error")


class TestReminder1TemplateUsage:
    """Test Reminder 1 (4h) uses send_whatsapp_message_or_template with recordatorio_seguimiento_1"""
    
    def test_reminder_1_uses_message_or_template(self):
        """Verify first reminder uses send_whatsapp_message_or_template"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the reminder logic section
        reminder_section = content[content.find('# First reminder after 4 hours'):]
        reminder_section = reminder_section[:reminder_section.find('# Second reminder')]
        
        assert 'send_whatsapp_message_or_template' in reminder_section, \
            "First reminder should use send_whatsapp_message_or_template"
        print("✓ Reminder 1 (4h) uses send_whatsapp_message_or_template")
    
    def test_reminder_1_template_name(self):
        """Verify first reminder uses template_name='recordatorio_seguimiento_1'"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the first reminder call
        reminder_section = content[content.find('# First reminder after 4 hours'):]
        reminder_section = reminder_section[:reminder_section.find('# Second reminder')]
        
        assert 'recordatorio_seguimiento_1' in reminder_section, \
            "First reminder should use template_name='recordatorio_seguimiento_1'"
        print("✓ Reminder 1 uses template_name='recordatorio_seguimiento_1'")


class TestReminder2TemplateUsage:
    """Test Reminder 2 (23h) uses send_whatsapp_message_or_template with recordatorio_seguimiento_2"""
    
    def test_reminder_2_uses_message_or_template(self):
        """Verify second reminder uses send_whatsapp_message_or_template"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the second reminder logic section
        reminder_section = content[content.find('# Second reminder after 23 hours'):]
        reminder_section = reminder_section[:reminder_section.find('# Mark as lost')]
        
        assert 'send_whatsapp_message_or_template' in reminder_section, \
            "Second reminder should use send_whatsapp_message_or_template"
        print("✓ Reminder 2 (23h) uses send_whatsapp_message_or_template")
    
    def test_reminder_2_template_name(self):
        """Verify second reminder uses template_name='recordatorio_seguimiento_2'"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Find the second reminder call
        reminder_section = content[content.find('# Second reminder after 23 hours'):]
        reminder_section = reminder_section[:reminder_section.find('# Mark as lost')]
        
        assert 'recordatorio_seguimiento_2' in reminder_section, \
            "Second reminder should use template_name='recordatorio_seguimiento_2'"
        print("✓ Reminder 2 uses template_name='recordatorio_seguimiento_2'")


class TestNotifyStaffCatalogRequestTemplate:
    """Test notify_staff_catalog_request catches 24h errors and uses alerta_producto_no_encontrado template"""
    
    def test_function_exists_in_bot_service(self):
        """Verify notify_staff_catalog_request function exists in bot_service.py"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        assert 'async def notify_staff_catalog_request(' in content, \
            "notify_staff_catalog_request function not found in bot_service.py"
        print("✓ notify_staff_catalog_request function exists in bot_service.py")
    
    def test_catches_24h_errors(self):
        """Verify function catches 24h window errors"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def notify_staff_catalog_request(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\ndef ', func_start)
        func_content = content[func_start:func_end]
        
        # Check for error detection
        assert '131047' in func_content, "Missing 131047 error detection"
        assert '131026' in func_content, "Missing 131026 error detection"
        assert '24 hour' in func_content.lower(), "Missing 24 hour error detection"
        assert 're-engagement' in func_content.lower(), "Missing re-engagement error detection"
        print("✓ notify_staff_catalog_request catches 131047, 131026, 24 hour, re-engagement errors")
    
    def test_uses_alerta_producto_template(self):
        """Verify function uses alerta_producto_no_encontrado template"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def notify_staff_catalog_request(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\ndef ', func_start)
        func_content = content[func_start:func_end]
        
        assert 'alerta_producto_no_encontrado' in func_content, \
            "Function should use 'alerta_producto_no_encontrado' template"
        print("✓ notify_staff_catalog_request uses 'alerta_producto_no_encontrado' template")
    
    def test_imports_send_whatsapp_template(self):
        """Verify function imports send_whatsapp_template from server"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def notify_staff_catalog_request(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\ndef ', func_start)
        func_content = content[func_start:func_end]
        
        assert 'from server import send_whatsapp_template' in func_content, \
            "Function should import send_whatsapp_template from server"
        print("✓ notify_staff_catalog_request imports send_whatsapp_template from server")
    
    def test_template_has_3_parameters(self):
        """Verify template is called with 3 parameters (nombre, telefono, busqueda)"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def notify_staff_catalog_request(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\ndef ', func_start)
        func_content = content[func_start:func_end]
        
        # Find the send_whatsapp_template call
        template_call = func_content[func_content.find('send_whatsapp_template('):]
        template_call = template_call[:template_call.find(')') + 1]
        
        # Check for 3 parameters in the list
        assert '[client_name, phone_number, product_request]' in template_call or \
               'client_name, phone_number, product_request' in template_call, \
            "Template should be called with [client_name, phone_number, product_request]"
        print("✓ alerta_producto_no_encontrado template called with 3 parameters (nombre, telefono, busqueda)")
    
    def test_language_code_is_es(self):
        """Verify template uses language code 'es'"""
        with open('/app/backend/bot_service.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def notify_staff_catalog_request(')
        func_end = content.find('\nasync def ', func_start + 1)
        if func_end == -1:
            func_end = content.find('\n\n\ndef ', func_start)
        func_content = content[func_start:func_end]
        
        # Check for language code 'es'
        assert '"es"' in func_content or "'es'" in func_content, \
            "Template should use language code 'es'"
        print("✓ Template uses language code 'es'")


class TestTemplateAPIEndpoint:
    """Test the WhatsApp API endpoint configuration"""
    
    def test_uses_correct_api_endpoint(self):
        """Verify template function uses graph.facebook.com/v18.0/{phone_number_id}/messages"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        func_start = content.find('async def send_whatsapp_template(')
        func_end = content.find('\nasync def ', func_start + 1)
        func_content = content[func_start:func_end]
        
        assert 'graph.facebook.com/v18.0' in func_content, \
            "Template function should use graph.facebook.com/v18.0 endpoint"
        assert '/messages' in func_content, \
            "Template function should use /messages endpoint"
        print("✓ Template function uses graph.facebook.com/v18.0/{phone_number_id}/messages endpoint")


class TestTemplateNamesExact:
    """Verify exact template names are used"""
    
    def test_all_template_names_exact(self):
        """Verify all 3 template names are exactly as specified"""
        with open('/app/backend/server.py', 'r') as f:
            server_content = f.read()
        
        with open('/app/backend/bot_service.py', 'r') as f:
            bot_content = f.read()
        
        combined = server_content + bot_content
        
        # Check exact template names
        assert 'recordatorio_seguimiento_1' in combined, \
            "Template 'recordatorio_seguimiento_1' not found"
        assert 'recordatorio_seguimiento_2' in combined, \
            "Template 'recordatorio_seguimiento_2' not found"
        assert 'alerta_producto_no_encontrado' in combined, \
            "Template 'alerta_producto_no_encontrado' not found"
        
        print("✓ All 3 template names are exact: recordatorio_seguimiento_1, recordatorio_seguimiento_2, alerta_producto_no_encontrado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
