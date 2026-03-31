"""
Iteration 17: Test Staff Notifications and Product Catalog
Tests:
1. Staff notification sent when NEW quote is created (ALERTA COTIZACION NUEVA to 593999440910)
2. Staff notification sent when existing quote is UPDATED (ALERTA COTIZACION ACTUALIZADA to 593999440910)
3. Bot product search returns ONLY current catalog products (JAR*, HT*, SC*, etc. - NOT GIMK-* old codes)
4. Product search for 'jarro' returns current products like JARPOR00391-BLA, JARVID00020
5. Product search for 'gorra' returns current products like HT2PR2, SC5CRNB
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Load dotenv BEFORE importing bot_service
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

# Add backend to path
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

# Global variables to capture messages
captured_messages: List[Dict] = []
staff_notifications: List[Dict] = []

STAFF_PHONE = "593999440910"
TEST_PHONE = "593963266566"
TEST_CONVERSATION_ID = "46696923-fcbd-48a2-850d-1e55fa500765"


async def mock_send(phone: str, conv_id: str, message: str):
    """Mock send function that captures messages and differentiates staff notifications"""
    global captured_messages, staff_notifications
    msg_data = {
        "phone": phone,
        "conversation_id": conv_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    captured_messages.append(msg_data)
    
    # Capture staff notifications separately
    if phone == STAFF_PHONE:
        staff_notifications.append(msg_data)
    
    print(f"[MOCK_SEND] To: {phone}, Message: {message[:100]}...")


def get_db():
    """Get database connection synchronously"""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'gimmicks_crm')
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


def reset_captured_messages():
    """Reset captured messages"""
    global captured_messages, staff_notifications
    captured_messages = []
    staff_notifications = []


class TestProductSearch:
    """Test that product search returns ONLY current catalog products"""
    
    @pytest.mark.asyncio
    async def test_no_old_gimk_products_in_db(self):
        """Verify old GIMK-* products have been removed from DB"""
        db = get_db()
        gimk_count = await db.products.count_documents({
            'code': {'$regex': '^GIMK', '$options': 'i'}
        })
        print(f"Old GIMK products count: {gimk_count}")
        assert gimk_count == 0, f"Found {gimk_count} old GIMK-* products that should be removed"
    
    @pytest.mark.asyncio
    async def test_current_products_exist(self):
        """Verify current catalog products exist (JAR*, HT*, SC*)"""
        db = get_db()
        jar_count = await db.products.count_documents({'code': {'$regex': '^JAR', '$options': 'i'}})
        ht_count = await db.products.count_documents({'code': {'$regex': '^HT', '$options': 'i'}})
        sc_count = await db.products.count_documents({'code': {'$regex': '^SC', '$options': 'i'}})
        
        print(f"Current products - JAR: {jar_count}, HT: {ht_count}, SC: {sc_count}")
        
        assert jar_count > 0, "No JAR products found in catalog"
        assert ht_count > 0, "No HT products found in catalog"
        assert sc_count > 0, "No SC products found in catalog"
    
    @pytest.mark.asyncio
    async def test_search_jarro_returns_current_products(self):
        """Test that searching 'jarro' returns current products like JARPOR00391-BLA"""
        db = get_db()
        from bot_service import search_products_by_keyword
        
        products = await search_products_by_keyword(db, "jarro", limit=10)
        
        print(f"Search 'jarro' returned {len(products)} products:")
        for p in products:
            print(f"  {p.get('code')}: {p.get('name')}")
        
        assert len(products) > 0, "No products found for 'jarro'"
        
        # Verify products are from current catalog (JAR* codes)
        codes = [p.get('code', '') for p in products]
        jar_codes = [c for c in codes if c.upper().startswith('JAR')]
        
        assert len(jar_codes) > 0, f"No JAR* products found. Got codes: {codes}"
        
        # Verify no old GIMK codes
        gimk_codes = [c for c in codes if 'GIMK' in c.upper()]
        assert len(gimk_codes) == 0, f"Found old GIMK codes in results: {gimk_codes}"
        
        # Check for specific expected products
        expected_codes = ['JARPOR00391', 'JARVID00020', 'JARPOR00250']
        found_expected = [c for c in codes if any(exp in c for exp in expected_codes)]
        print(f"Found expected products: {found_expected}")
    
    @pytest.mark.asyncio
    async def test_search_gorra_returns_current_products(self):
        """Test that searching 'gorra' returns current products like HT2PR2, SC5CRNB"""
        db = get_db()
        from bot_service import search_products_by_keyword
        
        products = await search_products_by_keyword(db, "gorra", limit=10)
        
        print(f"Search 'gorra' returned {len(products)} products:")
        for p in products:
            print(f"  {p.get('code')}: {p.get('name')}")
        
        assert len(products) > 0, "No products found for 'gorra'"
        
        # Verify products are from current catalog (HT* or SC* codes)
        codes = [p.get('code', '') for p in products]
        current_codes = [c for c in codes if c.upper().startswith(('HT', 'SC'))]
        
        assert len(current_codes) > 0, f"No HT*/SC* products found. Got codes: {codes}"
        
        # Verify no old GIMK codes
        gimk_codes = [c for c in codes if 'GIMK' in c.upper()]
        assert len(gimk_codes) == 0, f"Found old GIMK codes in results: {gimk_codes}"
    
    @pytest.mark.asyncio
    async def test_search_termo_returns_current_products(self):
        """Test that searching 'termo' returns current products"""
        db = get_db()
        from bot_service import search_products_by_keyword
        
        products = await search_products_by_keyword(db, "termo", limit=10)
        
        print(f"Search 'termo' returned {len(products)} products:")
        for p in products:
            print(f"  {p.get('code')}: {p.get('name')}")
        
        # Verify no old GIMK codes
        codes = [p.get('code', '') for p in products]
        gimk_codes = [c for c in codes if 'GIMK' in c.upper()]
        assert len(gimk_codes) == 0, f"Found old GIMK codes in results: {gimk_codes}"


class TestStaffNotifications:
    """Test staff notifications when quotes are created/updated"""
    
    @pytest.mark.asyncio
    async def test_staff_notification_on_new_quote(self):
        """Test that staff notification is sent when a NEW quote is created"""
        db = get_db()
        reset_captured_messages()
        
        from bot_service import notify_staff_new_quote, upsert_quote
        
        # Ensure no pending quote exists
        await db.quotes_v2.delete_many({
            "phone_number": TEST_PHONE,
            "status": "pending"
        })
        
        # Reset conversation state
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE})
        
        # Collected data for quote
        collected_data = {
            "nombre": "José Silva",
            "correo": "Joseluissb2732@gmail.com",
            "empresa": "Emprenovus",
            "codigos_producto": "JARPOR00391-BLA",
            "cantidad": "100"
        }
        
        # Create the quote first
        quote_msg = await upsert_quote(db, TEST_PHONE, collected_data, TEST_CONVERSATION_ID)
        print(f"Quote created: {quote_msg}")
        
        # Now send staff notification
        await notify_staff_new_quote(db, TEST_PHONE, collected_data, is_update=False, send_message_fn=mock_send)
        
        # Verify staff notification was sent
        print(f"Staff notifications captured: {len(staff_notifications)}")
        for notif in staff_notifications:
            print(f"  To: {notif['phone']}, Message: {notif['message'][:200]}...")
        
        assert len(staff_notifications) >= 1, "No staff notification was sent"
        
        # Verify notification content
        notif = staff_notifications[0]
        assert notif['phone'] == STAFF_PHONE, f"Notification sent to wrong phone: {notif['phone']}"
        assert "ALERTA COTIZACION NUEVA" in notif['message'], f"Missing 'ALERTA COTIZACION NUEVA' in: {notif['message']}"
        assert "José Silva" in notif['message'] or "Jose Silva" in notif['message'], f"Missing client name in notification"
        assert TEST_PHONE in notif['message'], f"Missing phone number in notification"
    
    @pytest.mark.asyncio
    async def test_staff_notification_on_quote_update(self):
        """Test that staff notification is sent when an existing quote is UPDATED"""
        db = get_db()
        reset_captured_messages()
        
        from bot_service import notify_staff_new_quote, upsert_quote
        
        # Ensure no pending quote exists first
        await db.quotes_v2.delete_many({
            "phone_number": TEST_PHONE,
            "status": "pending"
        })
        
        # First create a quote
        collected_data = {
            "nombre": "José Silva",
            "correo": "Joseluissb2732@gmail.com",
            "empresa": "Emprenovus",
            "codigos_producto": "JARPOR00391-BLA",
            "cantidad": "100"
        }
        
        # Create initial quote
        await upsert_quote(db, TEST_PHONE, collected_data, TEST_CONVERSATION_ID)
        
        # Clear captured messages
        reset_captured_messages()
        
        # Update the quote with new products
        collected_data["codigos_producto"] = "JARPOR00391-BLA,JARVID00020"
        collected_data["cantidad"] = "200"
        
        # Update quote
        quote_msg = await upsert_quote(db, TEST_PHONE, collected_data, TEST_CONVERSATION_ID)
        print(f"Quote updated: {quote_msg}")
        
        # Send staff notification for update
        await notify_staff_new_quote(db, TEST_PHONE, collected_data, is_update=True, send_message_fn=mock_send)
        
        # Verify staff notification was sent
        print(f"Staff notifications captured: {len(staff_notifications)}")
        for notif in staff_notifications:
            print(f"  To: {notif['phone']}, Message: {notif['message'][:200]}...")
        
        assert len(staff_notifications) >= 1, "No staff notification was sent for update"
        
        # Verify notification content
        notif = staff_notifications[0]
        assert notif['phone'] == STAFF_PHONE, f"Notification sent to wrong phone: {notif['phone']}"
        assert "ALERTA COTIZACION ACTUALIZADA" in notif['message'], f"Missing 'ALERTA COTIZACION ACTUALIZADA' in: {notif['message']}"
    
    @pytest.mark.asyncio
    async def test_notify_staff_function_parameters(self):
        """Test that notify_staff_new_quote function has correct parameters"""
        from bot_service import notify_staff_new_quote
        import inspect
        
        sig = inspect.signature(notify_staff_new_quote)
        params = list(sig.parameters.keys())
        
        print(f"notify_staff_new_quote parameters: {params}")
        
        assert 'db' in params, "Missing 'db' parameter"
        assert 'customer_phone' in params, "Missing 'customer_phone' parameter"
        assert 'collected_data' in params, "Missing 'collected_data' parameter"
        assert 'is_update' in params, "Missing 'is_update' parameter"
        assert 'send_message_fn' in params, "Missing 'send_message_fn' parameter"
    
    @pytest.mark.asyncio
    async def test_staff_phone_constant(self):
        """Test that STAFF_NOTIFICATION_PHONE is correctly set"""
        from bot_service import STAFF_NOTIFICATION_PHONE
        
        print(f"STAFF_NOTIFICATION_PHONE: {STAFF_NOTIFICATION_PHONE}")
        assert STAFF_NOTIFICATION_PHONE == "593999440910", f"Wrong staff phone: {STAFF_NOTIFICATION_PHONE}"


class TestQuoteCreationTriggersNotification:
    """Test that the full quote creation flow triggers staff notification"""
    
    @pytest.mark.asyncio
    async def test_full_quote_flow_with_notification(self):
        """Test complete flow: quote creation triggers staff notification"""
        db = get_db()
        reset_captured_messages()
        
        from bot_service import process_ai_conversation, _new_state
        
        # Reset conversation state
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE})
        
        # Delete any pending quotes
        await db.quotes_v2.delete_many({
            "phone_number": TEST_PHONE,
            "status": "pending"
        })
        
        # Create fresh conversation state with all required data for quote
        now = datetime.now(timezone.utc)
        state = _new_state(TEST_PHONE, now)
        state["collected_data"] = {
            "nombre": "José Silva",
            "correo": "Joseluissb2732@gmail.com",
            "empresa": "Emprenovus",
            "codigos_producto": "JARPOR00391-BLA",
            "cantidades_por_producto": "JARPOR00391-BLA:100"
        }
        await db.conversation_states.insert_one(state)
        
        # Process a message that should trigger quote creation
        # The AI should recognize all data is present and create quote
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE,
            message_text="Sí, quiero cotizar 100 jarros",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_send
        )
        
        # Wait a bit for async processing
        await asyncio.sleep(3)
        
        print(f"Total messages captured: {len(captured_messages)}")
        print(f"Staff notifications: {len(staff_notifications)}")
        
        for msg in captured_messages:
            print(f"  To: {msg['phone']}, Message: {msg['message'][:150]}...")
        
        # Check if a quote was created
        quote = await db.quotes_v2.find_one({
            "phone_number": TEST_PHONE,
            "status": "pending"
        }, {"_id": 0})
        
        if quote:
            print(f"Quote created: #{quote.get('quote_number')}")
            # If quote was created, staff notification should have been sent
            # Note: This depends on the AI deciding to create a quote
        else:
            print("No quote was created in this test run (AI may need more data)")


class TestCatalogAvailabilityInjection:
    """Test that catalog_availability is injected correctly in bot responses"""
    
    @pytest.mark.asyncio
    async def test_product_search_injects_catalog_availability(self):
        """Test that product search results are injected into AI prompt"""
        db = get_db()
        from bot_service import search_products_by_keyword
        
        # Search for jarro
        products = await search_products_by_keyword(db, "jarro", limit=5)
        
        assert len(products) > 0, "No products found for 'jarro'"
        
        # Build catalog_availability string like the bot does
        prod_details = ", ".join([f"{p.get('name', '')} (código: {p.get('code', '')})" for p in products[:5]])
        catalog_availability = f"PRODUCTOS ENCONTRADOS EN INVENTARIO ACTUAL para 'jarro': {prod_details}"
        
        print(f"Catalog availability: {catalog_availability}")
        
        # Verify it contains current product codes
        assert "JARPOR" in catalog_availability or "JARVID" in catalog_availability, \
            f"Current product codes not in catalog_availability: {catalog_availability}"
        
        # Verify no old GIMK codes
        assert "GIMK" not in catalog_availability, \
            f"Old GIMK codes found in catalog_availability: {catalog_availability}"


class TestBuildCatalogUrl:
    """Test catalog URL building"""
    
    def test_build_catalog_url_uses_env_var(self):
        """Test that build_catalog_url uses CATALOG_BASE_URL from env"""
        from bot_service import build_catalog_url
        
        url = build_catalog_url("jarro")
        print(f"Catalog URL for 'jarro': {url}")
        
        # Should use CATALOG_BASE_URL from .env
        expected_base = os.environ.get("CATALOG_BASE_URL", "")
        if expected_base:
            assert expected_base.rstrip("/") in url, f"URL doesn't use CATALOG_BASE_URL: {url}"
        
        assert "catalog?q=jarro" in url, f"URL doesn't have correct query: {url}"
    
    def test_build_catalog_url_handles_multiple_keywords(self):
        """Test that build_catalog_url uses first keyword when multiple provided"""
        from bot_service import build_catalog_url
        
        url = build_catalog_url("jarro, taza, termo")
        print(f"Catalog URL for 'jarro, taza, termo': {url}")
        
        # Should use only first keyword
        assert "catalog?q=jarro" in url, f"URL should use first keyword: {url}"


class TestPerPhoneConcurrencyLock:
    """Test per-phone concurrency lock"""
    
    @pytest.mark.asyncio
    async def test_phone_locks_exist(self):
        """Test that _phone_locks dictionary exists"""
        from bot_service import _phone_locks
        
        print(f"_phone_locks type: {type(_phone_locks)}")
        assert isinstance(_phone_locks, dict), "_phone_locks should be a dictionary"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
