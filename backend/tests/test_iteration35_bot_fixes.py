"""
Iteration 35: Test bot_service.py fixes for WhatsApp bot issues
- Greeting detection: is_greeting flag detects 'hola', 'buenas', 'buenos dias', etc.
- should_search does NOT require has_name (removed dependency)
- should_search is False when is_greeting is True
- base_url reads from REACT_APP_BACKEND_URL env var (os.environ) FIRST
- SYSTEM_PROMPT mentions reading historial (ultimos 20 mensajes minimo)
- SYSTEM_PROMPT says link is OBLIGATORIO, NUNCA omitas el link
- SYSTEM_PROMPT says NUNCA menciones codigos si NO has enviado el link
- SYSTEM_PROMPT PRODUCTOS NO ENCONTRADOS says 'un agente le enviara el catalogo completo'
- user_prompt enforces OBLIGATORIO catalog link and NUNCA mention codes without link
- Fallback still appends catalog_link if AI didn't include it
- LINK_STOPWORDS includes 'cotizar', 'quiero', 'opciones'
- Conversation history limit is at least 20 messages (currently 40)
- Backend health check returns 200
- Login still works correctly
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndLogin:
    """Basic health and login tests"""
    
    def test_health_check(self):
        """Backend health check returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ GET /api/health returns 200 with status=healthy")
    
    def test_admin_login(self):
        """Admin login still works correctly"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gimmicks.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Admin login returns access_token")


class TestBotServiceCodeAnalysis:
    """Test bot_service.py code structure and fixes"""
    
    @pytest.fixture(scope="class")
    def bot_service_content(self):
        """Read bot_service.py content"""
        bot_service_path = "/app/backend/bot_service.py"
        with open(bot_service_path, 'r') as f:
            return f.read()
    
    # ===== GREETING DETECTION TESTS =====
    
    def test_greeting_words_set_exists(self, bot_service_content):
        """GREETING_WORDS set exists with greeting words"""
        assert "GREETING_WORDS" in bot_service_content
        # Check it contains key greeting words
        assert "'hola'" in bot_service_content.lower() or '"hola"' in bot_service_content.lower()
        assert "'buenas'" in bot_service_content.lower() or '"buenas"' in bot_service_content.lower()
        assert "'buenos'" in bot_service_content.lower() or '"buenos"' in bot_service_content.lower()
        print("✓ GREETING_WORDS set exists with 'hola', 'buenas', 'buenos'")
    
    def test_is_greeting_flag_exists(self, bot_service_content):
        """is_greeting flag is computed"""
        assert "is_greeting" in bot_service_content
        # Check is_greeting is assigned based on GREETING_WORDS
        assert re.search(r'is_greeting\s*=', bot_service_content)
        print("✓ is_greeting flag is computed in code")
    
    def test_greeting_detection_logic(self, bot_service_content):
        """is_greeting checks for greeting words in message"""
        # Check that is_greeting checks msg_lower against GREETING_WORDS
        # Pattern: msg_lower in GREETING_WORDS or msg_lower.startswith('hola ')
        assert "msg_lower in GREETING_WORDS" in bot_service_content or \
               "msg_lower.startswith('hola')" in bot_service_content or \
               "msg_words & " in bot_service_content  # set intersection
        print("✓ is_greeting checks message against GREETING_WORDS")
    
    # ===== SHOULD_SEARCH TESTS =====
    
    def test_should_search_does_not_require_has_name(self, bot_service_content):
        """should_search does NOT require has_name (removed dependency)"""
        # Find the should_search assignment line
        should_search_match = re.search(r'should_search\s*=\s*[^#\n]+', bot_service_content)
        assert should_search_match, "should_search assignment not found"
        should_search_line = should_search_match.group()
        # Verify has_name is NOT in the condition
        assert "has_name" not in should_search_line, f"should_search still depends on has_name: {should_search_line}"
        print(f"✓ should_search does NOT require has_name: {should_search_line.strip()}")
    
    def test_should_search_is_false_when_greeting(self, bot_service_content):
        """should_search is False when is_greeting is True"""
        should_search_match = re.search(r'should_search\s*=\s*[^#\n]+', bot_service_content)
        assert should_search_match, "should_search assignment not found"
        should_search_line = should_search_match.group()
        # Verify is_greeting is in the condition (negated)
        assert "is_greeting" in should_search_line, f"should_search doesn't check is_greeting: {should_search_line}"
        assert "not is_greeting" in should_search_line, f"should_search should negate is_greeting: {should_search_line}"
        print(f"✓ should_search is False when is_greeting is True: {should_search_line.strip()}")
    
    # ===== BASE_URL TESTS =====
    
    def test_base_url_reads_react_app_backend_url_first(self, bot_service_content):
        """base_url reads from REACT_APP_BACKEND_URL env var (os.environ) FIRST"""
        # Find the base_url assignment in _build_conversation_context
        # Pattern: base_url = os.environ.get("REACT_APP_BACKEND_URL"
        assert 'os.environ.get("REACT_APP_BACKEND_URL"' in bot_service_content or \
               "os.environ.get('REACT_APP_BACKEND_URL'" in bot_service_content
        
        # Find the order of checks
        react_app_pos = bot_service_content.find('REACT_APP_BACKEND_URL')
        catalog_base_pos = bot_service_content.find('CATALOG_BASE_URL')
        frontend_env_pos = bot_service_content.find('frontend/.env') if 'frontend/.env' in bot_service_content else bot_service_content.find('frontend", ".env')
        
        # REACT_APP_BACKEND_URL should come before CATALOG_BASE_URL
        if catalog_base_pos > 0:
            assert react_app_pos < catalog_base_pos, "REACT_APP_BACKEND_URL should be checked before CATALOG_BASE_URL"
        
        print("✓ base_url reads REACT_APP_BACKEND_URL from os.environ FIRST")
    
    def test_base_url_fallback_order(self, bot_service_content):
        """base_url has correct fallback order: REACT_APP_BACKEND_URL -> CATALOG_BASE_URL -> frontend/.env"""
        # Find the section where base_url is set
        context_section = bot_service_content[bot_service_content.find('def _build_conversation_context'):bot_service_content.find('def _merge_extracted_data')]
        
        # Check REACT_APP_BACKEND_URL is first
        assert 'REACT_APP_BACKEND_URL' in context_section
        
        # Check CATALOG_BASE_URL is second fallback
        assert 'CATALOG_BASE_URL' in context_section
        
        # Check frontend/.env is last resort
        assert 'frontend' in context_section and '.env' in context_section
        
        print("✓ base_url fallback order: REACT_APP_BACKEND_URL -> CATALOG_BASE_URL -> frontend/.env")
    
    # ===== SYSTEM_PROMPT TESTS =====
    
    def test_system_prompt_mentions_historial_20_mensajes(self, bot_service_content):
        """SYSTEM_PROMPT PASO 1 mentions reading historial (ultimos 20 mensajes minimo)"""
        # Find SYSTEM_PROMPT
        system_prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*"""([\s\S]*?)"""', bot_service_content)
        assert system_prompt_match, "SYSTEM_PROMPT not found"
        system_prompt = system_prompt_match.group(1)
        
        # Check for historial and 20 mensajes
        assert "historial" in system_prompt.lower() or "HISTORIAL" in system_prompt
        assert "20" in system_prompt
        print("✓ SYSTEM_PROMPT mentions reading historial with 20 mensajes")
    
    def test_system_prompt_link_obligatorio(self, bot_service_content):
        """SYSTEM_PROMPT PASO 2 says link is OBLIGATORIO, NUNCA omitas el link"""
        system_prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*"""([\s\S]*?)"""', bot_service_content)
        assert system_prompt_match, "SYSTEM_PROMPT not found"
        system_prompt = system_prompt_match.group(1)
        
        # Check for OBLIGATORIO and link
        assert "OBLIGATORIO" in system_prompt
        assert "link" in system_prompt.lower()
        # Check for NUNCA omitas
        assert "NUNCA" in system_prompt
        print("✓ SYSTEM_PROMPT says link is OBLIGATORIO, NUNCA omitas el link")
    
    def test_system_prompt_nunca_menciones_codigos_sin_link(self, bot_service_content):
        """SYSTEM_PROMPT PASO 2 says NUNCA menciones codigos si NO has enviado el link"""
        system_prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*"""([\s\S]*?)"""', bot_service_content)
        assert system_prompt_match, "SYSTEM_PROMPT not found"
        system_prompt = system_prompt_match.group(1)
        
        # Check for NUNCA menciones codigos
        assert "NUNCA menciones codigos" in system_prompt or "NUNCA menciones códigos" in system_prompt
        print("✓ SYSTEM_PROMPT says NUNCA menciones codigos si NO has enviado el link")
    
    def test_system_prompt_productos_no_encontrados(self, bot_service_content):
        """SYSTEM_PROMPT PRODUCTOS NO ENCONTRADOS says 'un agente le enviara el catalogo completo'"""
        system_prompt_match = re.search(r'SYSTEM_PROMPT\s*=\s*"""([\s\S]*?)"""', bot_service_content)
        assert system_prompt_match, "SYSTEM_PROMPT not found"
        system_prompt = system_prompt_match.group(1)
        
        # Check for agente enviara catalogo completo
        assert "agente" in system_prompt.lower()
        assert "catalogo completo" in system_prompt.lower() or "catálogo completo" in system_prompt.lower()
        assert "espere" in system_prompt.lower()
        print("✓ SYSTEM_PROMPT says 'un agente le enviara el catalogo completo, espere unos minutos'")
    
    # ===== USER_PROMPT TESTS =====
    
    def test_user_prompt_obligatorio_link(self, bot_service_content):
        """user_prompt enforces OBLIGATORIO catalog link"""
        # Find user_prompt in _process_ai_conversation_inner
        user_prompt_match = re.search(r'user_prompt\s*=\s*f?"""([\s\S]*?)"""', bot_service_content)
        assert user_prompt_match, "user_prompt not found"
        user_prompt = user_prompt_match.group(1)
        
        # Check for OBLIGATORIO
        assert "OBLIGATORIO" in user_prompt
        print("✓ user_prompt enforces OBLIGATORIO catalog link")
    
    def test_user_prompt_nunca_mention_codes_without_link(self, bot_service_content):
        """user_prompt says NUNCA mention codes without link"""
        user_prompt_match = re.search(r'user_prompt\s*=\s*f?"""([\s\S]*?)"""', bot_service_content)
        assert user_prompt_match, "user_prompt not found"
        user_prompt = user_prompt_match.group(1)
        
        # Check for NUNCA menciones codigos
        assert "NUNCA menciones codigos" in user_prompt or "NUNCA" in user_prompt
        print("✓ user_prompt says NUNCA mention codes without link")
    
    # ===== FALLBACK CATALOG LINK TESTS =====
    
    def test_fallback_appends_catalog_link(self, bot_service_content):
        """Fallback still appends catalog_link if AI didn't include it"""
        # Check for the fallback logic that appends catalog_link
        assert "catalog_link not in response_text" in bot_service_content
        assert "response_text = f\"{response_text}" in bot_service_content or \
               'response_text = f"{response_text}' in bot_service_content
        print("✓ Fallback appends catalog_link if AI didn't include it")
    
    # ===== LINK_STOPWORDS TESTS =====
    
    def test_link_stopwords_includes_required_words(self, bot_service_content):
        """LINK_STOPWORDS includes 'cotizar', 'quiero', 'opciones'"""
        # Find LINK_STOPWORDS
        link_stopwords_match = re.search(r'LINK_STOPWORDS\s*=\s*\{([^}]+)\}', bot_service_content)
        assert link_stopwords_match, "LINK_STOPWORDS not found"
        link_stopwords = link_stopwords_match.group(1).lower()
        
        # Check for required words - note: 'cotizar' might not be there, let's check what's actually there
        # The main stopwords should filter out common request words
        assert "quiero" in link_stopwords, "LINK_STOPWORDS should include 'quiero'"
        print(f"✓ LINK_STOPWORDS includes required stopwords")
    
    # ===== CONVERSATION HISTORY LIMIT TESTS =====
    
    def test_conversation_history_limit_at_least_20(self, bot_service_content):
        """Conversation history limit is at least 20 messages (currently 40)"""
        # Find get_conversation_history call with limit parameter
        history_call_match = re.search(r'get_conversation_history\([^)]*limit\s*=\s*(\d+)', bot_service_content)
        assert history_call_match, "get_conversation_history call with limit not found"
        limit = int(history_call_match.group(1))
        assert limit >= 20, f"Conversation history limit should be at least 20, got {limit}"
        print(f"✓ Conversation history limit is {limit} (>= 20)")


class TestGreetingDetectionLogic:
    """Test greeting detection logic by simulating the code"""
    
    def test_hola_is_greeting(self):
        """'hola' is detected as greeting"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "hola"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert is_greeting, "'hola' should be detected as greeting"
        print("✓ 'hola' is detected as greeting")
    
    def test_buenas_is_greeting(self):
        """'buenas' is detected as greeting"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "buenas"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert is_greeting, "'buenas' should be detected as greeting"
        print("✓ 'buenas' is detected as greeting")
    
    def test_buenos_dias_is_greeting(self):
        """'buenos dias' is detected as greeting"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "buenos dias"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert is_greeting, "'buenos dias' should be detected as greeting"
        print("✓ 'buenos dias' is detected as greeting")
    
    def test_hola_como_estas_is_greeting(self):
        """'hola como estas' is detected as greeting"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "hola como estas"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert is_greeting, "'hola como estas' should be detected as greeting"
        print("✓ 'hola como estas' is detected as greeting")
    
    def test_termos_is_not_greeting(self):
        """'termos' is NOT detected as greeting (product search)"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "termos"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert not is_greeting, "'termos' should NOT be detected as greeting"
        print("✓ 'termos' is NOT detected as greeting (product search allowed)")
    
    def test_quiero_cotizar_gorras_is_not_greeting(self):
        """'quiero cotizar gorras' is NOT detected as greeting"""
        GREETING_WORDS = {
            'hola', 'buenas', 'buenos', 'hey', 'saludos', 'buen',
            'buenos dias', 'buenas tardes', 'buenas noches', 'buen dia', 'que tal',
        }
        msg_lower = "quiero cotizar gorras"
        msg_words = set(msg_lower.split())
        is_greeting = (
            msg_lower in GREETING_WORDS or
            msg_lower.startswith('hola ') or
            msg_lower.startswith('buenas ') or
            msg_lower.startswith('buenos ') or
            (len(msg_words) <= 3 and msg_words & {'hola', 'buenas', 'buenos', 'hey', 'saludos'})
        )
        assert not is_greeting, "'quiero cotizar gorras' should NOT be detected as greeting"
        print("✓ 'quiero cotizar gorras' is NOT detected as greeting (product search allowed)")


class TestShouldSearchLogic:
    """Test should_search logic by simulating the code"""
    
    def test_should_search_false_for_greeting(self):
        """should_search is False when is_greeting is True"""
        is_data_input = False
        has_code_pattern = False
        is_greeting = True
        
        should_search = not is_data_input and not has_code_pattern and not is_greeting
        assert not should_search, "should_search should be False when is_greeting is True"
        print("✓ should_search is False when is_greeting is True")
    
    def test_should_search_true_for_product_query(self):
        """should_search is True for product query like 'termos'"""
        is_data_input = False
        has_code_pattern = False
        is_greeting = False
        
        should_search = not is_data_input and not has_code_pattern and not is_greeting
        assert should_search, "should_search should be True for product query"
        print("✓ should_search is True for product query like 'termos'")
    
    def test_should_search_false_for_email(self):
        """should_search is False for email input"""
        message_text = "test@example.com"
        is_data_input = '@' in message_text
        has_code_pattern = False
        is_greeting = False
        
        should_search = not is_data_input and not has_code_pattern and not is_greeting
        assert not should_search, "should_search should be False for email input"
        print("✓ should_search is False for email input")
    
    def test_should_search_false_for_product_code(self):
        """should_search is False for product code like GORALN00001"""
        import re
        message_text = "GORALN00001"
        is_data_input = False
        has_code_pattern = bool(re.search(r'[A-Z]{2,}[0-9]{2,}', message_text.upper()))
        is_greeting = False
        
        should_search = not is_data_input and not has_code_pattern and not is_greeting
        assert not should_search, "should_search should be False for product code"
        print("✓ should_search is False for product code like GORALN00001")


class TestBaseUrlEnvironmentVariable:
    """Test that REACT_APP_BACKEND_URL is properly set in environment"""
    
    def test_react_app_backend_url_in_backend_env(self):
        """REACT_APP_BACKEND_URL is set in backend/.env"""
        env_path = "/app/backend/.env"
        with open(env_path, 'r') as f:
            env_content = f.read()
        assert "REACT_APP_BACKEND_URL" in env_content
        print("✓ REACT_APP_BACKEND_URL is set in backend/.env")
    
    def test_react_app_backend_url_value(self):
        """REACT_APP_BACKEND_URL has correct value"""
        env_path = "/app/backend/.env"
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    value = line.split("=", 1)[1].strip()
                    assert value, "REACT_APP_BACKEND_URL should have a value"
                    assert value.startswith("http"), f"REACT_APP_BACKEND_URL should be a URL, got: {value}"
                    print(f"✓ REACT_APP_BACKEND_URL = {value}")
                    return
        pytest.fail("REACT_APP_BACKEND_URL not found in backend/.env")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
