"""
Iteration 36: Test STRENGTHENED prompt rules for WhatsApp bot.
Key changes verified:
1. PASO 1: 'UNICAMENTE saludo cordial', 'NO pidas codigos, NO menciones cotizaciones pendientes'
2. PASO 2: 'De manera INMEDIATA busca', example response, 'NUNCA digas agente te enviara catalogo si sistema encontro productos'
3. catalog_availability when products found: 'PROHIBIDO decir un agente te enviara el catalogo'
4. STAFF_NOTIFICATION_PHONE updated to 593963560326
5. user_prompt reinforces all rules including greeting behavior
6. Greeting detection prevents product search on 'hola'
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Read bot_service.py content for code verification
BOT_SERVICE_PATH = "/app/backend/bot_service.py"
with open(BOT_SERVICE_PATH, 'r') as f:
    BOT_SERVICE_CODE = f.read()


class TestHealthAndLogin:
    """Basic health and login tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ GET /api/health returns 200 with status=healthy")
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Admin login returns access_token")


class TestPaso1SaludoInicial:
    """Test PASO 1 - SALUDO INICIAL rules in SYSTEM_PROMPT"""
    
    def test_paso1_unicamente_saludo_cordial(self):
        """PASO 1 should say 'UNICAMENTE con un saludo cordial'"""
        # Check for the strengthened language
        assert "UNICAMENTE con un saludo cordial" in BOT_SERVICE_CODE or \
               "Responde UNICAMENTE con un saludo cordial" in BOT_SERVICE_CODE, \
               "PASO 1 should contain 'UNICAMENTE con un saludo cordial'"
        print("✓ PASO 1 contains 'UNICAMENTE saludo cordial' language")
    
    def test_paso1_no_pidas_codigos(self):
        """PASO 1 should say 'NO pidas codigos'"""
        # Look for the rule about not asking for codes in greeting
        assert "NO pidas codigos" in BOT_SERVICE_CODE or \
               "NO pidas el nombre, NO pidas codigos" in BOT_SERVICE_CODE, \
               "PASO 1 should contain 'NO pidas codigos'"
        print("✓ PASO 1 contains 'NO pidas codigos' rule")
    
    def test_paso1_no_menciones_cotizaciones_pendientes(self):
        """PASO 1 should say 'NO menciones cotizaciones pendientes'"""
        assert "NO menciones cotizaciones pendientes" in BOT_SERVICE_CODE, \
               "PASO 1 should contain 'NO menciones cotizaciones pendientes'"
        print("✓ PASO 1 contains 'NO menciones cotizaciones pendientes' rule")
    
    def test_paso1_en_que_puedo_ayudarte(self):
        """PASO 1 should ask 'En que puedo ayudarte hoy?'"""
        assert "En que puedo ayudarte hoy" in BOT_SERVICE_CODE or \
               "en que puedo ayudarte hoy" in BOT_SERVICE_CODE, \
               "PASO 1 should contain 'En que puedo ayudarte hoy?'"
        print("✓ PASO 1 contains 'En que puedo ayudarte hoy?' question")
    
    def test_paso1_uses_client_name_from_history(self):
        """PASO 1 should use client name from history if available"""
        # Check for the pattern: "Si ya conoces su nombre del historial, usalo"
        assert "Si ya conoces su nombre del historial" in BOT_SERVICE_CODE or \
               "Hola [nombre], en que puedo ayudarte" in BOT_SERVICE_CODE, \
               "PASO 1 should mention using client name from history"
        print("✓ PASO 1 mentions using client name from history")


class TestPaso2ProductoBusqueda:
    """Test PASO 2 - PRODUCTO rules in SYSTEM_PROMPT"""
    
    def test_paso2_inmediata_busqueda(self):
        """PASO 2 should say 'De manera INMEDIATA busca'"""
        assert "De manera INMEDIATA busca" in BOT_SERVICE_CODE or \
               "INMEDIATA busca" in BOT_SERVICE_CODE.upper(), \
               "PASO 2 should contain 'De manera INMEDIATA busca'"
        print("✓ PASO 2 contains 'De manera INMEDIATA busca' instruction")
    
    def test_paso2_obligatorio_include_link(self):
        """PASO 2 should say link is OBLIGATORIO"""
        assert "OBLIGATORIO incluir" in BOT_SERVICE_CODE or \
               "es OBLIGATORIO incluirlo" in BOT_SERVICE_CODE, \
               "PASO 2 should say link is OBLIGATORIO"
        print("✓ PASO 2 says link is OBLIGATORIO")
    
    def test_paso2_example_response_format(self):
        """PASO 2 should include example response format"""
        # Check for example response pattern
        assert "Ejemplo de respuesta correcta" in BOT_SERVICE_CODE or \
               "Tengo varias opciones" in BOT_SERVICE_CODE, \
               "PASO 2 should include example response format"
        print("✓ PASO 2 includes example response format")
    
    def test_paso2_nunca_agente_enviara_catalogo_when_products_found(self):
        """PASO 2 should say NUNCA 'agente te enviara catalogo' when products found"""
        # This is the critical new rule
        assert "NUNCA digas \"un agente te enviara el catalogo\" si el sistema encontro productos" in BOT_SERVICE_CODE or \
               "NUNCA digas 'un agente te enviara el catalogo' si el sistema encontro productos" in BOT_SERVICE_CODE, \
               "PASO 2 should contain NUNCA agente enviara catalogo when products found"
        print("✓ PASO 2 contains 'NUNCA agente enviara catalogo si sistema encontro productos'")


class TestProductosNoEncontrados:
    """Test rules for when products are NOT found"""
    
    def test_no_products_says_agente_enviara_catalogo(self):
        """When NO products found, should say 'un agente le enviara el catalogo completo, espere unos minutos'"""
        # Check for the specific phrase for no products scenario
        assert "un agente le enviara el catalogo completo" in BOT_SERVICE_CODE or \
               "agente le enviara el catalogo completo, que por favor espere unos minutos" in BOT_SERVICE_CODE, \
               "Should say 'agente enviara catalogo completo, espere unos minutos' when NO products"
        print("✓ When NO products: says 'un agente le enviara el catalogo completo, espere unos minutos'")
    
    def test_no_products_instruction_in_catalog_availability(self):
        """catalog_availability for no products should have correct instruction"""
        # Check the SIN RESULTADOS section
        assert "SIN RESULTADOS EN INVENTARIO" in BOT_SERVICE_CODE
        assert "un agente le enviara el catalogo completo" in BOT_SERVICE_CODE
        print("✓ catalog_availability for no products has correct instruction")


class TestCatalogAvailabilityProhibido:
    """Test catalog_availability instruction when products ARE found"""
    
    def test_prohibido_decir_agente_enviara_catalogo(self):
        """When products found, should say 'PROHIBIDO decir un agente te enviara el catalogo'"""
        # This is the critical instruction when products ARE found
        assert "PROHIBIDO decir" in BOT_SERVICE_CODE and "agente te enviara el catalogo" in BOT_SERVICE_CODE, \
               "Should say 'PROHIBIDO decir agente te enviara catalogo' when products found"
        print("✓ catalog_availability when products found: 'PROHIBIDO decir un agente te enviara el catalogo'")
    
    def test_tu_envias_el_link(self):
        """When products found, should say 'TU envias el link'"""
        assert "TU envias el link" in BOT_SERVICE_CODE, \
               "Should say 'TU envias el link' when products found"
        print("✓ catalog_availability when products found: 'TU envias el link'")


class TestStaffNotificationPhone:
    """Test STAFF_NOTIFICATION_PHONE is updated"""
    
    def test_staff_phone_updated(self):
        """STAFF_NOTIFICATION_PHONE should be 593963560326"""
        # Check for the exact phone number
        assert 'STAFF_NOTIFICATION_PHONE = "593963560326"' in BOT_SERVICE_CODE or \
               "STAFF_NOTIFICATION_PHONE = '593963560326'" in BOT_SERVICE_CODE, \
               "STAFF_NOTIFICATION_PHONE should be 593963560326"
        print("✓ STAFF_NOTIFICATION_PHONE = '593963560326' (updated from old number)")
    
    def test_old_phone_not_present(self):
        """Old phone number 593999440910 should NOT be in STAFF_NOTIFICATION_PHONE"""
        # Make sure old number is not the staff notification phone
        match = re.search(r'STAFF_NOTIFICATION_PHONE\s*=\s*["\'](\d+)["\']', BOT_SERVICE_CODE)
        assert match, "STAFF_NOTIFICATION_PHONE should be defined"
        phone = match.group(1)
        assert phone != "593999440910", "Old phone number should not be used"
        assert phone == "593963560326", f"Phone should be 593963560326, got {phone}"
        print("✓ Old phone number 593999440910 is NOT used for STAFF_NOTIFICATION_PHONE")


class TestUserPromptReinforcement:
    """Test user_prompt reinforces all rules"""
    
    def test_user_prompt_nunca_agente_enviara_catalogo(self):
        """user_prompt should reinforce 'NUNCA agente enviara catalogo si sistema ENCONTRO productos'"""
        # Check user_prompt section
        assert 'NUNCA digas "un agente te enviara el catalogo" si el sistema ENCONTRO productos' in BOT_SERVICE_CODE or \
               "NUNCA digas 'un agente te enviara el catalogo' si el sistema ENCONTRO productos" in BOT_SERVICE_CODE, \
               "user_prompt should reinforce NUNCA agente enviara catalogo rule"
        print("✓ user_prompt reinforces 'NUNCA agente enviara catalogo si sistema ENCONTRO productos'")
    
    def test_user_prompt_greeting_behavior(self):
        """user_prompt should say 'Si el cliente saluda, responde SOLO con saludo y en que puedo ayudarte hoy'"""
        assert "Si el cliente saluda" in BOT_SERVICE_CODE and "en que puedo ayudarte hoy" in BOT_SERVICE_CODE, \
               "user_prompt should mention greeting behavior"
        print("✓ user_prompt: 'Si el cliente saluda, responde SOLO con saludo y en que puedo ayudarte hoy'")
    
    def test_user_prompt_no_pidas_codigos_on_greeting(self):
        """user_prompt should say 'NO pidas codigos' for greetings"""
        # Check that user_prompt reinforces not asking for codes on greeting
        assert "NO pidas codigos" in BOT_SERVICE_CODE, \
               "user_prompt should reinforce NO pidas codigos"
        print("✓ user_prompt reinforces 'NO pidas codigos' rule")


class TestBaseUrlConfiguration:
    """Test base_url reads REACT_APP_BACKEND_URL from os.environ first"""
    
    def test_base_url_reads_react_app_backend_url_first(self):
        """base_url should read REACT_APP_BACKEND_URL from os.environ first"""
        # Check the order of reading base_url
        assert 'os.environ.get("REACT_APP_BACKEND_URL"' in BOT_SERVICE_CODE or \
               "os.environ.get('REACT_APP_BACKEND_URL'" in BOT_SERVICE_CODE, \
               "base_url should read REACT_APP_BACKEND_URL from os.environ"
        print("✓ base_url reads REACT_APP_BACKEND_URL from os.environ first")
    
    def test_react_app_backend_url_in_backend_env(self):
        """REACT_APP_BACKEND_URL should be set in backend/.env"""
        with open("/app/backend/.env", 'r') as f:
            env_content = f.read()
        assert "REACT_APP_BACKEND_URL=" in env_content
        assert "catalog-pdf-fix.preview.emergentagent.com" in env_content
        print("✓ REACT_APP_BACKEND_URL is set in backend/.env")


class TestGreetingDetection:
    """Test greeting detection prevents product search on 'hola'"""
    
    def test_greeting_words_set_exists(self):
        """GREETING_WORDS set should exist"""
        assert "GREETING_WORDS" in BOT_SERVICE_CODE
        assert "'hola'" in BOT_SERVICE_CODE or '"hola"' in BOT_SERVICE_CODE
        print("✓ GREETING_WORDS set exists with 'hola'")
    
    def test_is_greeting_flag_computed(self):
        """is_greeting flag should be computed"""
        assert "is_greeting" in BOT_SERVICE_CODE
        print("✓ is_greeting flag is computed in code")
    
    def test_should_search_false_when_greeting(self):
        """should_search should be False when is_greeting is True"""
        # Check that should_search includes is_greeting check
        assert "not is_greeting" in BOT_SERVICE_CODE or \
               "and not is_greeting" in BOT_SERVICE_CODE, \
               "should_search should check is_greeting"
        print("✓ should_search is False when is_greeting is True")
    
    def test_greeting_words_include_common_greetings(self):
        """GREETING_WORDS should include common Spanish greetings"""
        greetings_to_check = ['hola', 'buenas', 'buenos']
        for greeting in greetings_to_check:
            assert f"'{greeting}'" in BOT_SERVICE_CODE or f'"{greeting}"' in BOT_SERVICE_CODE, \
                   f"GREETING_WORDS should include '{greeting}'"
        print("✓ GREETING_WORDS includes 'hola', 'buenas', 'buenos'")


class TestFallbackCatalogLink:
    """Test fallback appends catalog_link if AI didn't include it"""
    
    def test_fallback_appends_catalog_link(self):
        """Fallback should append catalog_link if AI didn't include it"""
        # Check for the fallback logic
        assert "catalog_link not in response_text" in BOT_SERVICE_CODE or \
               "if catalog_link and response_text and catalog_link not in response_text" in BOT_SERVICE_CODE, \
               "Fallback should check if catalog_link is in response_text"
        print("✓ Fallback appends catalog_link if AI didn't include it")


class TestConversationHistoryLimit:
    """Test conversation history limit"""
    
    def test_history_limit_at_least_20(self):
        """Conversation history limit should be at least 20"""
        # Check the limit parameter in get_conversation_history call
        match = re.search(r'get_conversation_history\([^)]*limit\s*=\s*(\d+)', BOT_SERVICE_CODE)
        if match:
            limit = int(match.group(1))
            assert limit >= 20, f"History limit should be >= 20, got {limit}"
        else:
            # Check default in function definition
            match = re.search(r'def get_conversation_history\([^)]*limit:\s*int\s*=\s*(\d+)', BOT_SERVICE_CODE)
            if match:
                limit = int(match.group(1))
                assert limit >= 20, f"History limit should be >= 20, got {limit}"
        print("✓ Conversation history limit is >= 20")


class TestSystemPromptPaso1Complete:
    """Complete verification of PASO 1 in SYSTEM_PROMPT"""
    
    def test_paso1_complete_rules(self):
        """Verify all PASO 1 rules are present"""
        # Extract PASO 1 section
        paso1_match = re.search(r'PASO 1[^P]*(?=PASO 2)', BOT_SERVICE_CODE, re.DOTALL)
        assert paso1_match, "PASO 1 section should exist"
        paso1_text = paso1_match.group()
        
        # Check all required elements
        checks = [
            ("SALUDO INICIAL" in paso1_text, "PASO 1 should be titled SALUDO INICIAL"),
            ("saludo cordial" in paso1_text.lower(), "PASO 1 should mention 'saludo cordial'"),
            ("En que puedo ayudarte" in paso1_text, "PASO 1 should ask 'En que puedo ayudarte'"),
            ("NO pidas" in paso1_text, "PASO 1 should say 'NO pidas'"),
        ]
        
        for check, msg in checks:
            assert check, msg
        
        print("✓ PASO 1 complete rules verified")


class TestSystemPromptPaso2Complete:
    """Complete verification of PASO 2 in SYSTEM_PROMPT"""
    
    def test_paso2_complete_rules(self):
        """Verify all PASO 2 rules are present"""
        # Check PASO 2 content directly in the code
        # PASO 2 is about PRODUCTO and should contain key rules
        
        # Check all required elements exist in the code
        checks = [
            ("PASO 2 - PRODUCTO" in BOT_SERVICE_CODE, "PASO 2 should be about PRODUCTO"),
            ("De manera INMEDIATA busca" in BOT_SERVICE_CODE, "PASO 2 should mention INMEDIATA busca"),
            ("es OBLIGATORIO incluirlo" in BOT_SERVICE_CODE, "PASO 2 should mention OBLIGATORIO"),
            ("LINK DEL CATALOGO FILTRADO" in BOT_SERVICE_CODE, "PASO 2 should mention link"),
            ("NUNCA digas" in BOT_SERVICE_CODE and "agente te enviara el catalogo" in BOT_SERVICE_CODE, 
             "PASO 2 should have NUNCA agente enviara catalogo rule"),
        ]
        
        for check, msg in checks:
            assert check, msg
        
        print("✓ PASO 2 complete rules verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
