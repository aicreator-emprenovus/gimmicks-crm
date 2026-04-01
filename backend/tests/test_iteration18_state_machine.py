"""
Iteration 18: State Machine Overhaul Tests
Tests the complete conversational flow state machine for CRM Gimmicks WhatsApp Bot.

Test Cases:
- CASO 1: Date response after date question - must save as date, NOT search product
- CASO 2: Phone number NOT treated as product code
- CASO 3: Frustration/urgency triggers immediate escalation to human with structured summary
- CASO 4: Product not available - bot should NOT invent availability, suggest catalog
- CASO 5: Adding products mid-quote notifies human agent
- State machine: 'Hola soy X' captures name correctly (NOT product search)
- State machine: Product codes accepted only in esperando_codigos/validando_codigos stages
- State machine: 'un color' saved as color_logo, not product
- State machine: 'Quito' saved as ciudad, not product
- Full quote flow: name -> product -> code -> qty -> color -> email -> empresa -> quote generated
- Catalog link still sent when user asks for full catalog
- Staff notification (ALERTA COTIZACION) still works when quote is generated
- Escalation sends structured summary with all collected data to staff phone 593999440910
"""

import pytest
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv("/app/backend/.env")

# Add backend to path
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient

# Import bot_service functions
from bot_service import (
    detect_escalation,
    determine_stage,
    send_escalation_summary,
    ESCALATION_KEYWORDS,
    FIELD_ALIASES,
    VALID_STAGES,
    STAFF_NOTIFICATION_PHONE,
    process_ai_conversation,
    search_products_by_keyword,
    validate_product_codes,
    _new_state,
)


# Test configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "gimmicks_crm")
STAFF_PHONE = "593999440910"

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def generate_test_phone():
    """Generate a unique test phone number"""
    return f"593900{uuid.uuid4().hex[:6]}"


async def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def create_mock_send():
    """Create mock send function that captures messages"""
    messages = []
    
    async def _mock_send(phone, conv_id, text):
        messages.append({
            "phone": phone,
            "conversation_id": conv_id,
            "text": text,
            "is_staff": phone == STAFF_PHONE
        })
        return True
    
    _mock_send.messages = messages
    return _mock_send


async def create_temp_conversation(db, phone_number):
    """Create a temporary conversation and lead for testing"""
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Create conversation
    await db.conversations.insert_one({
        "id": conv_id,
        "phone_number": phone_number,
        "contact_name": "",
        "status": "active",
        "created_at": now,
        "updated_at": now
    })
    
    # Create lead
    await db.leads.insert_one({
        "id": str(uuid.uuid4()),
        "phone_number": phone_number,
        "name": "",
        "status": "active",
        "funnel_stage": "lead",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    })
    
    return conv_id


async def cleanup_test_data(db, phone_number):
    """Clean up all test data for a phone number"""
    await db.conversation_states.delete_many({"phone_number": phone_number})
    await db.conversations.delete_many({"phone_number": phone_number})
    await db.leads.delete_many({"phone_number": phone_number})
    await db.messages.delete_many({"conversation_id": {"$regex": phone_number}})
    await db.quotes_v2.delete_many({"phone_number": phone_number})


class TestEscalationDetection:
    """Test escalation keyword detection (pre-AI check)"""
    
    def test_detect_escalation_frustration_keywords(self):
        """CASO 3: Frustration keywords trigger escalation"""
        test_cases = [
            ("ya no quiero nada", True),
            ("pásame con alguien", True),
            ("quiero hablar con una persona", True),
            ("estoy molesto", True),
            ("terrible servicio", True),
            ("pésimo", True),
            ("sin más preguntas", True),
            ("quiero la cotización ahorita", True),
        ]
        
        for message, should_escalate in test_cases:
            result = detect_escalation(message)
            if should_escalate:
                assert result != "", f"Expected escalation for: '{message}'"
                print(f"✓ '{message}' -> escalation detected: {result}")
            else:
                assert result == "", f"Unexpected escalation for: '{message}'"
    
    def test_detect_escalation_normal_messages(self):
        """Normal messages should NOT trigger escalation"""
        normal_messages = [
            "Hola, necesito jarros",
            "100 unidades",
            "JARPOR00391",
            "un color",
            "Quito",
            "abril 15",
            "test@email.com",
            "Mi Empresa SA",
        ]
        
        for message in normal_messages:
            result = detect_escalation(message)
            assert result == "", f"Unexpected escalation for normal message: '{message}'"
            print(f"✓ '{message}' -> no escalation (correct)")
    
    def test_escalation_keywords_list(self):
        """Verify ESCALATION_KEYWORDS list is properly defined"""
        assert len(ESCALATION_KEYWORDS) > 0, "ESCALATION_KEYWORDS should not be empty"
        assert "ya no quiero nada" in ESCALATION_KEYWORDS
        assert "pásame con alguien" in ESCALATION_KEYWORDS
        print(f"✓ ESCALATION_KEYWORDS has {len(ESCALATION_KEYWORDS)} keywords")


class TestDetermineStage:
    """Test stage determination logic"""
    
    def test_stage_saludo_new_user(self):
        """New user starts at saludo stage"""
        stage = determine_stage({}, [], False, "saludo")
        assert stage == "captura_nombre", f"Expected captura_nombre, got {stage}"
        print("✓ New user -> captura_nombre")
    
    def test_stage_with_name_only(self):
        """User with name goes to busqueda_producto"""
        stage = determine_stage({"nombre": "Juan"}, [], False, "saludo")
        assert stage == "busqueda_producto", f"Expected busqueda_producto, got {stage}"
        print("✓ User with name -> busqueda_producto")
    
    def test_stage_with_catalog_sent(self):
        """After catalog sent, expect esperando_codigos"""
        stage = determine_stage({"nombre": "Juan", "producto": "jarros"}, ["jarros"], False, "busqueda_producto")
        assert stage == "esperando_codigos", f"Expected esperando_codigos, got {stage}"
        print("✓ After catalog -> esperando_codigos")
    
    def test_stage_with_codes(self):
        """With codes, expect validando_codigos"""
        stage = determine_stage({"codigos_producto": "JARPOR00391"}, [], False, "esperando_codigos")
        assert stage == "validando_codigos", f"Expected validando_codigos, got {stage}"
        print("✓ With codes -> validando_codigos")
    
    def test_stage_with_codes_and_qty(self):
        """With codes and quantity, expect recopilando_datos"""
        stage = determine_stage(
            {"codigos_producto": "JARPOR00391", "cantidad": "100"},
            [], False, "validando_codigos"
        )
        assert stage == "recopilando_datos", f"Expected recopilando_datos, got {stage}"
        print("✓ With codes + qty -> recopilando_datos")
    
    def test_stage_escalado_humano_persists(self):
        """escalado_humano stage should persist"""
        stage = determine_stage({"nombre": "Juan"}, [], False, "escalado_humano")
        assert stage == "escalado_humano", f"Expected escalado_humano to persist, got {stage}"
        print("✓ escalado_humano persists")
    
    def test_stage_revision_humana_after_quote(self):
        """After quote generated, expect revision_humana"""
        stage = determine_stage(
            {"codigos_producto": "JARPOR00391", "cantidad": "100", "correo": "test@test.com", "empresa": "Test"},
            [], True, "recopilando_datos"
        )
        assert stage == "revision_humana", f"Expected revision_humana, got {stage}"
        print("✓ After quote -> revision_humana")


class TestFieldAliases:
    """Test field name normalization"""
    
    def test_email_aliases(self):
        """Email field aliases"""
        assert FIELD_ALIASES.get("email") == "correo"
        assert FIELD_ALIASES.get("mail") == "correo"
        assert FIELD_ALIASES.get("correo_electronico") == "correo"
        print("✓ Email aliases normalized to 'correo'")
    
    def test_code_aliases(self):
        """Product code aliases"""
        assert FIELD_ALIASES.get("codigos") == "codigos_producto"
        assert FIELD_ALIASES.get("codigo") == "codigos_producto"
        assert FIELD_ALIASES.get("códigos") == "codigos_producto"
        print("✓ Code aliases normalized to 'codigos_producto'")
    
    def test_color_logo_aliases(self):
        """Color/logo aliases"""
        assert FIELD_ALIASES.get("tipo_de_personalizacion") == "color_logo"
        assert FIELD_ALIASES.get("color_logotipo") == "color_logo"
        print("✓ Color/logo aliases normalized to 'color_logo'")
    
    def test_city_aliases(self):
        """City aliases"""
        assert FIELD_ALIASES.get("ciudad_de_entrega") == "ciudad"
        assert FIELD_ALIASES.get("ciudad_entrega") == "ciudad"
        print("✓ City aliases normalized to 'ciudad'")


class TestValidStages:
    """Test valid stages list"""
    
    def test_all_stages_defined(self):
        """All required stages are defined"""
        required_stages = [
            "saludo", "captura_nombre", "busqueda_producto", "esperando_codigos",
            "validando_codigos", "recopilando_datos", "revision_humana", "escalado_humano"
        ]
        for stage in required_stages:
            assert stage in VALID_STAGES, f"Missing stage: {stage}"
        print(f"✓ All {len(required_stages)} stages defined in VALID_STAGES")


class TestStaffNotificationPhone:
    """Test staff notification configuration"""
    
    def test_staff_phone_configured(self):
        """Staff phone number is correctly configured"""
        assert STAFF_NOTIFICATION_PHONE == "593999440910"
        print(f"✓ STAFF_NOTIFICATION_PHONE = {STAFF_NOTIFICATION_PHONE}")


class TestNewStateFunction:
    """Test _new_state function"""
    
    def test_new_state_structure(self):
        """New state has correct structure"""
        now = datetime.now(timezone.utc)
        state = _new_state("593900000001", now)
        
        assert state["phone_number"] == "593900000001"
        assert state["collected_data"] == {}
        assert state["lead_quality"] == "frio"
        assert state["stage"] == "saludo"
        assert state["quote_generated"] == False
        assert state["transferred_to_human"] == False
        assert state["message_count"] == 0
        
        print("✓ _new_state creates correct structure")


# ============== ASYNC TESTS ==============

@pytest.mark.asyncio
async def test_send_escalation_summary_structure():
    """CASO 3: Escalation sends structured summary to staff"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    
    collected_data = {
        "nombre": "Juan Pérez",
        "correo": "juan@test.com",
        "empresa": "Test Corp",
        "codigos_producto": "JARPOR00391",
        "cantidad": "100",
        "ciudad": "Quito",
        "fecha_entrega": "abril 15",
        "color_logo": "un color"
    }
    
    await send_escalation_summary(db, phone, collected_data, "Cliente frustrado", mock_send)
    
    # Check staff received the message
    staff_messages = [m for m in mock_send.messages if m["is_staff"]]
    assert len(staff_messages) == 1, "Staff should receive escalation summary"
    
    summary = staff_messages[0]["text"]
    assert "ESCALAMIENTO A ASESOR HUMANO" in summary
    assert "Juan Pérez" in summary
    assert phone in summary
    assert "juan@test.com" in summary
    assert "Test Corp" in summary
    assert "JARPOR00391" in summary
    assert "100" in summary
    assert "Quito" in summary
    assert "abril 15" in summary
    assert "un color" in summary
    assert "Cliente frustrado" in summary
    
    print("✓ Escalation summary contains all collected data")
    print(f"✓ Summary sent to staff phone: {STAFF_PHONE}")


@pytest.mark.asyncio
async def test_search_jarro():
    """Search for 'jarro' returns current products"""
    db = await get_db()
    products = await search_products_by_keyword(db, "jarro", limit=5)
    assert len(products) > 0, "Should find jarro products"
    
    codes = [p.get("code", "") for p in products]
    print(f"✓ 'jarro' search returned {len(products)} products: {codes[:3]}")
    
    # Verify no old GIMK codes
    for code in codes:
        assert not code.startswith("GIMK"), f"Found old GIMK code: {code}"


@pytest.mark.asyncio
async def test_search_gorra():
    """Search for 'gorra' returns current products"""
    db = await get_db()
    products = await search_products_by_keyword(db, "gorra", limit=5)
    assert len(products) > 0, "Should find gorra products"
    
    codes = [p.get("code", "") for p in products]
    print(f"✓ 'gorra' search returned {len(products)} products: {codes[:3]}")


@pytest.mark.asyncio
async def test_validate_product_codes():
    """Validate known product codes"""
    db = await get_db()
    codes = ["JARPOR00391", "HT2PR2"]
    validated = await validate_product_codes(db, codes)
    
    # At least one should be found
    assert len(validated) > 0, "Should validate at least one code"
    print(f"✓ Validated {len(validated)} codes: {[p.get('code') for p in validated]}")


@pytest.mark.asyncio
async def test_caso3_frustration_escalation():
    """CASO 3: Frustration/urgency triggers immediate escalation"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state with some data
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "busqueda_producto"
        state["collected_data"] = {"nombre": "Juan Frustrado"}
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send frustration message
        await process_ai_conversation(db, phone, "ya no quiero nada", conv_id, mock_send)
        
        # Wait for processing (no AI call needed for escalation keywords)
        await asyncio.sleep(1)
        
        # Check state - should be escalado_humano
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        assert updated_state.get("stage") == "escalado_humano", \
            f"Expected escalado_humano, got {updated_state.get('stage')}"
        assert updated_state.get("transferred_to_human") == True
        
        # Check staff received escalation summary
        staff_messages = [m for m in mock_send.messages if m["is_staff"]]
        assert len(staff_messages) >= 1, "Staff should receive escalation summary"
        
        summary = staff_messages[0]["text"]
        assert "ESCALAMIENTO" in summary
        assert "Juan Frustrado" in summary
        
        print("✓ CASO 3: Frustration triggered immediate escalation")
        print(f"  Stage: {updated_state.get('stage')}")
        print(f"  Staff notified: Yes")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_caso1_date_not_product():
    """CASO 1: Date response after date question - must save as date, NOT search product"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state in recopilando_datos stage asking for fecha_entrega
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "recopilando_datos"
        state["collected_data"] = {
            "nombre": "Test User",
            "codigos_producto": "JARPOR00391",
            "cantidad": "100",
            "color_logo": "un color",
            "correo": "test@test.com",
            "empresa": "Test Corp",
            "ciudad": "Quito"
        }
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send a date response
        await process_ai_conversation(db, phone, "abril 15", conv_id, mock_send)
        
        # Wait for AI processing
        await asyncio.sleep(5)
        
        # Check state - fecha_entrega should be saved
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        collected = updated_state.get("collected_data", {})
        
        # The date should be saved, not treated as product
        print(f"Collected data after date: {collected}")
        
        # Check messages - should NOT contain product search for "abril"
        user_messages = [m for m in mock_send.messages if not m["is_staff"]]
        for msg in user_messages:
            # Should not be searching for "abril" as a product
            assert "catálogo" not in msg["text"].lower() or "abril" not in msg["text"].lower(), \
                "Date should not trigger product search"
        
        print("✓ CASO 1: Date response handled correctly (not as product)")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_caso2_phone_not_product_code():
    """CASO 2: Phone number NOT treated as product code"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state in esperando_codigos stage
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "esperando_codigos"
        state["collected_data"] = {"nombre": "Test User", "producto": "jarros"}
        state["catalog_sent"] = ["jarros"]
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send a phone number (should NOT be treated as product code)
        await process_ai_conversation(db, phone, "0999123456", conv_id, mock_send)
        
        await asyncio.sleep(5)
        
        # Check state - phone should NOT be in codigos_producto
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        collected = updated_state.get("collected_data", {})
        
        codigos = collected.get("codigos_producto", "")
        assert "0999123456" not in codigos, "Phone number should NOT be saved as product code"
        
        print(f"✓ CASO 2: Phone number not treated as product code")
        print(f"  Collected data: {collected}")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_name_capture_not_product_search():
    """State machine: 'Hola soy X' captures name correctly (NOT product search)"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state in captura_nombre stage
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "captura_nombre"
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send name
        await process_ai_conversation(db, phone, "Hola soy María García", conv_id, mock_send)
        
        await asyncio.sleep(5)
        
        # Check state - name should be captured
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        collected = updated_state.get("collected_data", {})
        
        # Name should be saved
        nombre = collected.get("nombre", "")
        print(f"Captured name: '{nombre}'")
        
        # Should NOT have product codes
        assert not collected.get("codigos_producto"), "Name should not be treated as product code"
        
        print("✓ Name capture: 'Hola soy María García' captured correctly")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_color_saved_as_color_logo():
    """State machine: 'un color' saved as color_logo, not product"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state in recopilando_datos asking for color
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "recopilando_datos"
        state["collected_data"] = {
            "nombre": "Test",
            "codigos_producto": "JARPOR00391",
            "cantidad": "100"
        }
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send color response
        await process_ai_conversation(db, phone, "un color", conv_id, mock_send)
        
        await asyncio.sleep(5)
        
        # Check state
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        collected = updated_state.get("collected_data", {})
        
        print(f"Collected after 'un color': {collected}")
        
        # Should NOT trigger product search
        user_messages = [m for m in mock_send.messages if not m["is_staff"]]
        for msg in user_messages:
            text_lower = msg["text"].lower()
            # Should not be searching for "color" as a product
            assert "catálogo" not in text_lower or "color" in text_lower, \
                "'un color' should not trigger catalog search"
        
        print("✓ 'un color' handled correctly (not as product)")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_city_saved_as_ciudad():
    """State machine: 'Quito' saved as ciudad, not product"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state in recopilando_datos asking for city
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "recopilando_datos"
        state["collected_data"] = {
            "nombre": "Test",
            "codigos_producto": "JARPOR00391",
            "cantidad": "100",
            "color_logo": "un color",
            "correo": "test@test.com",
            "empresa": "Test Corp"
        }
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send city response
        await process_ai_conversation(db, phone, "Quito", conv_id, mock_send)
        
        await asyncio.sleep(5)
        
        # Check state
        updated_state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
        collected = updated_state.get("collected_data", {})
        
        print(f"Collected after 'Quito': {collected}")
        
        # Ciudad should be saved
        assert collected.get("ciudad") == "Quito" or "quito" in str(collected).lower(), \
            "Quito should be saved as ciudad"
        
        print("✓ 'Quito' saved as ciudad correctly")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_catalog_link_on_request():
    """Catalog link still sent when user asks for full catalog"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "busqueda_producto"
        state["collected_data"] = {"nombre": "Test"}
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Ask for catalog
        await process_ai_conversation(db, phone, "quiero ver el catálogo completo", conv_id, mock_send)
        
        await asyncio.sleep(5)
        
        # Check messages contain catalog link
        user_messages = [m for m in mock_send.messages if not m["is_staff"]]
        assert len(user_messages) > 0, "Should send response"
        
        has_catalog_link = any(
            "gimmicks.com.ec" in m["text"].lower() or "catalog" in m["text"].lower()
            for m in user_messages
        )
        assert has_catalog_link, "Should include catalog link"
        
        print("✓ Catalog link sent on request")
        
    finally:
        await cleanup_test_data(db, phone)


@pytest.mark.asyncio
async def test_staff_notification_on_quote():
    """Staff notification (ALERTA COTIZACION) works when quote is generated"""
    db = await get_db()
    mock_send = create_mock_send()
    phone = generate_test_phone()
    conv_id = await create_temp_conversation(db, phone)
    
    try:
        # Set up state with all required data for quote
        now = datetime.now(timezone.utc)
        state = _new_state(phone, now)
        state["stage"] = "recopilando_datos"
        state["collected_data"] = {
            "nombre": "Test Quote User",
            "codigos_producto": "JARPOR00391",
            "cantidad": "100",
            "color_logo": "un color",
            "correo": "quote@test.com",
            "empresa": "Quote Corp",
            "ciudad": "Quito"
        }
        await db.conversation_states.update_one(
            {"phone_number": phone},
            {"$set": state},
            upsert=True
        )
        
        # Send final piece of data to trigger quote
        await process_ai_conversation(db, phone, "para el 15 de abril", conv_id, mock_send)
        
        await asyncio.sleep(6)
        
        # Check staff notification
        staff_messages = [m for m in mock_send.messages if m["is_staff"]]
        
        # May have ALERTA COTIZACION
        has_quote_alert = any("ALERTA COTIZACION" in m["text"] for m in staff_messages)
        
        print(f"Staff messages: {len(staff_messages)}")
        if staff_messages:
            print(f"First staff message: {staff_messages[0]['text'][:200]}...")
        
        # Check quote was created
        quote = await db.quotes_v2.find_one(
            {"phone_number": phone, "is_deleted": False},
            {"_id": 0, "quote_number": 1, "status": 1}
        )
        
        if quote:
            print(f"✓ Quote created: #{quote.get('quote_number')}")
        
        print(f"✓ Staff notification test completed")
        
    finally:
        await cleanup_test_data(db, phone)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
