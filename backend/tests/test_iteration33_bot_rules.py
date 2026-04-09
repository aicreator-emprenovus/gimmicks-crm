"""
Iteration 33: Test 4 NEW bot rules for WhatsApp AI CRM
1) PERSONALIDAD: mensajes cortos, naturales, sin emojis
2) PASO 3: asks for 'nombre y apellido' not just 'nombre'
3) PASO 5: DATOS PERSONALES UNICAMENTE despues de entender cuales articulos
4) PASO 2 is PRODUCTO before PASO 3 NOMBRE (product first, name after)
5) run_followup_check: REMINDER_1_MSG exact text
6) run_followup_check: REMINDER_2_MSG exact text
7) run_followup_check: first reminder at 4h AND lead_stage in ('lead','cliente_potencial')
8) run_followup_check: second reminder at 23h AND lead_stage in ('lead','cliente_potencial')
9) run_followup_check: reminders do NOT send for 'cotizacion_generada', 'pedido', 'perdido' stages
10) Backend /api/health returns 200
11) Backend /api/auth/login works
"""
import pytest
import requests
import os
import re
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Expected exact reminder messages
EXPECTED_REMINDER_1_MSG = "Hola, te escribo solo para saber si pudiste revisar la información que te envié. Recuerda que estoy aquí para ayudarte en tus requerimientos"
EXPECTED_REMINDER_2_MSG = "Hola, solo quería hacer seguimiento a la información que te compartí. Si deseas, puedo ayudarte por aquí mismo a resolver cualquier duda o avanzar con lo que necesitas. Quedo atenta."
EXPECTED_ELIGIBLE_STAGES = ("lead", "cliente_potencial")


class TestSystemPromptRules:
    """Test SYSTEM_PROMPT rules in bot_service.py"""
    
    def test_personalidad_mensajes_cortos_naturales_sin_emojis(self):
        """Rule 1: PERSONALIDAD says 'mensajes cortos, de manera natural, sin emojis'"""
        from bot_service import SYSTEM_PROMPT
        
        # Check PERSONALIDAD section exists
        assert "PERSONALIDAD:" in SYSTEM_PROMPT, "PERSONALIDAD section missing"
        
        # Extract PERSONALIDAD section
        personalidad_match = re.search(r'PERSONALIDAD:(.*?)(?=\n\n|\nREGLA|\nFLUJO)', SYSTEM_PROMPT, re.DOTALL)
        assert personalidad_match, "Could not extract PERSONALIDAD section"
        personalidad_text = personalidad_match.group(1)
        
        # Verify exact rule: "mensajes cortos, de manera natural, sin emojis"
        assert "mensajes cortos" in personalidad_text.lower(), "Missing 'mensajes cortos' in PERSONALIDAD"
        assert "natural" in personalidad_text.lower(), "Missing 'natural' in PERSONALIDAD"
        assert "sin emojis" in personalidad_text.lower(), "Missing 'sin emojis' in PERSONALIDAD"
        
        print("✓ PERSONALIDAD correctly says 'mensajes cortos, de manera natural, sin emojis'")
    
    def test_paso_3_asks_nombre_y_apellido(self):
        """Rule 2: PASO 3 asks for 'nombre y apellido' not just 'nombre'"""
        from bot_service import SYSTEM_PROMPT
        
        # Find PASO 3 section
        paso3_match = re.search(r'PASO 3[^:]*:(.*?)(?=PASO 4|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso3_match, "PASO 3 section not found"
        paso3_text = paso3_match.group(1)
        
        # Verify it asks for "nombre y apellido"
        assert "nombre y apellido" in paso3_text.lower(), "PASO 3 should ask for 'nombre y apellido'"
        
        # Verify the example message includes "nombre y apellido"
        assert "nombre y apellido" in paso3_text, "PASO 3 example should include 'nombre y apellido'"
        
        print("✓ PASO 3 correctly asks for 'nombre y apellido' (not just 'nombre')")
    
    def test_paso_5_datos_personales_unicamente_despues_articulos(self):
        """Rule 3: PASO 5 says 'DATOS PERSONALES' and 'UNICAMENTE despues de entender cuales articulos'"""
        from bot_service import SYSTEM_PROMPT
        
        # Find PASO 5 section
        paso5_match = re.search(r'PASO 5[^:]*:(.*?)(?=REGLAS ADICIONALES|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso5_match, "PASO 5 section not found"
        paso5_text = paso5_match.group(1)
        
        # Verify it mentions DATOS PERSONALES
        assert "datos personales" in paso5_text.lower(), "PASO 5 should mention 'DATOS PERSONALES'"
        
        # Verify it says UNICAMENTE despues de entender cuales articulos
        assert "unicamente" in paso5_text.lower() or "únicamente" in paso5_text.lower(), "PASO 5 should say 'UNICAMENTE'"
        assert "despues" in paso5_text.lower() or "después" in paso5_text.lower(), "PASO 5 should say 'despues'"
        assert "articulos" in paso5_text.lower() or "artículos" in paso5_text.lower(), "PASO 5 should mention 'articulos'"
        
        print("✓ PASO 5 correctly says 'DATOS PERSONALES UNICAMENTE despues de entender cuales articulos'")
    
    def test_paso_2_producto_before_paso_3_nombre(self):
        """Rule 4: PASO 2 is PRODUCTO before PASO 3 NOMBRE (product first, name after)"""
        from bot_service import SYSTEM_PROMPT
        
        # Find positions of PASO 2 and PASO 3
        paso2_pos = SYSTEM_PROMPT.find("PASO 2")
        paso3_pos = SYSTEM_PROMPT.find("PASO 3")
        
        assert paso2_pos != -1, "PASO 2 not found in SYSTEM_PROMPT"
        assert paso3_pos != -1, "PASO 3 not found in SYSTEM_PROMPT"
        assert paso2_pos < paso3_pos, "PASO 2 should come BEFORE PASO 3"
        
        # Verify PASO 2 is about PRODUCTO
        paso2_match = re.search(r'PASO 2[^:]*:(.*?)(?=PASO 3|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso2_match, "Could not extract PASO 2 section"
        paso2_text = paso2_match.group(0)
        assert "producto" in paso2_text.lower(), "PASO 2 should be about PRODUCTO"
        
        # Verify PASO 3 is about NOMBRE
        paso3_match = re.search(r'PASO 3[^:]*:(.*?)(?=PASO 4|$)', SYSTEM_PROMPT, re.DOTALL | re.IGNORECASE)
        assert paso3_match, "Could not extract PASO 3 section"
        paso3_text = paso3_match.group(0)
        assert "nombre" in paso3_text.lower(), "PASO 3 should be about NOMBRE"
        
        print("✓ PASO 2 (PRODUCTO) correctly comes BEFORE PASO 3 (NOMBRE)")


class TestFollowupCheckReminderMessages:
    """Test run_followup_check reminder messages in server.py"""
    
    def test_reminder_1_msg_exact_text(self):
        """Rule 5: REMINDER_1_MSG exact text matches user requirement"""
        # Read server.py to extract REMINDER_1_MSG
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find REMINDER_1_MSG definition
        match = re.search(r'REMINDER_1_MSG\s*=\s*["\'](.+?)["\']', server_content)
        assert match, "REMINDER_1_MSG not found in server.py"
        actual_msg = match.group(1)
        
        # Verify exact match
        assert actual_msg == EXPECTED_REMINDER_1_MSG, f"REMINDER_1_MSG mismatch.\nExpected: {EXPECTED_REMINDER_1_MSG}\nActual: {actual_msg}"
        
        print(f"✓ REMINDER_1_MSG exact text matches: '{actual_msg[:50]}...'")
    
    def test_reminder_2_msg_exact_text(self):
        """Rule 6: REMINDER_2_MSG exact text matches user requirement"""
        # Read server.py to extract REMINDER_2_MSG
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find REMINDER_2_MSG definition
        match = re.search(r'REMINDER_2_MSG\s*=\s*["\'](.+?)["\']', server_content)
        assert match, "REMINDER_2_MSG not found in server.py"
        actual_msg = match.group(1)
        
        # Verify exact match
        assert actual_msg == EXPECTED_REMINDER_2_MSG, f"REMINDER_2_MSG mismatch.\nExpected: {EXPECTED_REMINDER_2_MSG}\nActual: {actual_msg}"
        
        print(f"✓ REMINDER_2_MSG exact text matches: '{actual_msg[:50]}...'")


class TestFollowupCheckTimingAndStages:
    """Test run_followup_check timing and stage filtering logic"""
    
    def test_first_reminder_at_4h_with_stage_filter(self):
        """Rule 7: first reminder only triggers at 4h AND lead_stage in ('lead','cliente_potencial')"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find the first reminder condition
        # Looking for: if 4 <= hours_inactive and reminder_count == 0 and lead_stage in REMINDER_ELIGIBLE_STAGES
        first_reminder_pattern = r'if\s+4\s*<=\s*hours_inactive.*?reminder_count\s*==\s*0.*?lead_stage\s+in\s+REMINDER_ELIGIBLE_STAGES'
        match = re.search(first_reminder_pattern, server_content, re.DOTALL)
        assert match, "First reminder condition not found with 4h timing and stage filter"
        
        # Verify REMINDER_ELIGIBLE_STAGES is defined correctly
        stages_match = re.search(r'REMINDER_ELIGIBLE_STAGES\s*=\s*\(([^)]+)\)', server_content)
        assert stages_match, "REMINDER_ELIGIBLE_STAGES not found"
        stages_text = stages_match.group(1)
        assert "lead" in stages_text, "REMINDER_ELIGIBLE_STAGES should include 'lead'"
        assert "cliente_potencial" in stages_text, "REMINDER_ELIGIBLE_STAGES should include 'cliente_potencial'"
        
        print("✓ First reminder triggers at 4h AND lead_stage in ('lead','cliente_potencial')")
    
    def test_second_reminder_at_23h_with_stage_filter(self):
        """Rule 8: second reminder triggers at 23h of inactivity AND lead_stage in ('lead','cliente_potencial')"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find the second reminder condition
        # Looking for: elif reminder_count == 1 and hours_inactive >= 23 and lead_stage in REMINDER_ELIGIBLE_STAGES
        second_reminder_pattern = r'elif\s+reminder_count\s*==\s*1\s+and\s+hours_inactive\s*>=\s*23.*?lead_stage\s+in\s+REMINDER_ELIGIBLE_STAGES'
        match = re.search(second_reminder_pattern, server_content, re.DOTALL)
        assert match, "Second reminder condition not found with 23h timing and stage filter"
        
        print("✓ Second reminder triggers at 23h AND lead_stage in ('lead','cliente_potencial')")
    
    def test_reminders_not_sent_for_excluded_stages(self):
        """Rule 9: reminders do NOT send for 'cotizacion_generada', 'pedido', 'perdido' stages"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Verify REMINDER_ELIGIBLE_STAGES only includes 'lead' and 'cliente_potencial'
        stages_match = re.search(r'REMINDER_ELIGIBLE_STAGES\s*=\s*\(([^)]+)\)', server_content)
        assert stages_match, "REMINDER_ELIGIBLE_STAGES not found"
        stages_text = stages_match.group(1).lower()
        
        # Verify excluded stages are NOT in REMINDER_ELIGIBLE_STAGES
        assert "cotizacion_generada" not in stages_text, "cotizacion_generada should NOT be in REMINDER_ELIGIBLE_STAGES"
        assert "pedido" not in stages_text, "pedido should NOT be in REMINDER_ELIGIBLE_STAGES"
        assert "perdido" not in stages_text, "perdido should NOT be in REMINDER_ELIGIBLE_STAGES"
        
        # Verify only 'lead' and 'cliente_potencial' are included
        assert "lead" in stages_text, "lead should be in REMINDER_ELIGIBLE_STAGES"
        assert "cliente_potencial" in stages_text, "cliente_potencial should be in REMINDER_ELIGIBLE_STAGES"
        
        print("✓ Reminders do NOT send for 'cotizacion_generada', 'pedido', 'perdido' stages")


class TestBackendHealthAndAuth:
    """Test backend health and authentication endpoints"""
    
    def test_health_endpoint_returns_200(self):
        """Rule 10: Backend /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health endpoint returned {response.status_code}"
        print("✓ GET /api/health returns 200")
    
    def test_auth_login_works(self):
        """Rule 11: Backend /api/auth/login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@gimmicks.com", "password": "admin123456"},
            timeout=10
        )
        assert response.status_code == 200, f"Login returned {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data, "Login response missing access_token"
        assert "user" in data, "Login response missing user"
        print("✓ POST /api/auth/login works correctly")
    
    def test_auth_login_rejects_invalid_credentials(self):
        """Test that login rejects invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"},
            timeout=10
        )
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        print("✓ POST /api/auth/login correctly rejects invalid credentials (401)")


class TestFollowupCheckFunctionStructure:
    """Test run_followup_check function structure and logic"""
    
    def test_run_followup_check_function_exists(self):
        """Verify run_followup_check function exists in server.py"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        assert "async def run_followup_check" in server_content, "run_followup_check function not found"
        print("✓ run_followup_check function exists in server.py")
    
    def test_lead_stage_check_before_reminders(self):
        """Verify lead_stage is checked before sending reminders"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find the run_followup_check function
        func_match = re.search(r'async def run_followup_check\(\):(.*?)(?=\nasync def|\nclass|\n@api_router|\Z)', server_content, re.DOTALL)
        assert func_match, "Could not extract run_followup_check function"
        func_content = func_match.group(1)
        
        # Verify lead_stage is fetched from leads collection
        assert "lead_stage" in func_content, "lead_stage variable not found in run_followup_check"
        assert "funnel_stage" in func_content, "funnel_stage lookup not found in run_followup_check"
        
        # Verify lead_stage is checked in both reminder conditions
        assert "lead_stage in REMINDER_ELIGIBLE_STAGES" in func_content, "lead_stage check not found in reminder conditions"
        
        print("✓ lead_stage is checked before sending reminders")
    
    def test_quote_generated_skip_logic(self):
        """Verify conversations with quote_generated are skipped"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Find the run_followup_check function
        func_match = re.search(r'async def run_followup_check\(\):(.*?)(?=\nasync def|\nclass|\n@api_router|\Z)', server_content, re.DOTALL)
        assert func_match, "Could not extract run_followup_check function"
        func_content = func_match.group(1)
        
        # Verify quote_generated check exists
        assert "quote_generated" in func_content, "quote_generated check not found in run_followup_check"
        
        print("✓ Conversations with quote_generated are skipped")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
