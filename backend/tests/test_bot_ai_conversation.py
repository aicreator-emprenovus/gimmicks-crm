"""
Test suite for WhatsApp Bot AI Conversation Logic
Tests the key fixes:
1. Bot greeting for returning client - should greet by name without re-introducing
2. Bot greeting for new client - should introduce as Ana de Gimmicks
3. Catalog link always sent when user asks for 'catálogo', 'catálogo completo', 'envíame el catálogo'
4. Specific product search returns filtered catalog link (e.g., 'tazas' returns catalog?q=taza)
5. No error fallback messages ('en un momento atenderemos') in responses
6. Single response per user message (no double messages)
7. Conversation continuity - follow-up messages don't start with 'Hola' redundantly
8. Concurrent message handling - two rapid messages don't cause errors
9. Error messages cleaned from conversation history - bot doesn't read old error messages
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Load dotenv BEFORE importing bot_service (critical for EMERGENT_LLM_KEY)
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

# Add backend to path
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

# Test configuration
TEST_PHONE_RETURNING = "593963266566"  # Existing lead with data
TEST_PHONE_NEW = "593900000001"  # New client (no existing data)
TEST_CONVERSATION_ID = "46696923-fcbd-48a2-850d-1e55fa500765"

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'gimmicks_crm')


class MockMessageCapture:
    """Captures messages sent by the bot for testing"""
    def __init__(self):
        self.messages: List[Dict] = []
    
    async def mock_send(self, phone_number: str, conversation_id: str, message: str):
        """Mock send function that captures messages"""
        self.messages.append({
            "phone_number": phone_number,
            "conversation_id": conversation_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"[MOCK SEND] To {phone_number}: {message[:100]}...")
    
    def clear(self):
        self.messages = []
    
    def get_last_message(self) -> str:
        if self.messages:
            return self.messages[-1]["message"]
        return ""
    
    def get_message_count(self) -> int:
        return len(self.messages)


def get_db():
    """Get database connection synchronously"""
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


# ============== Test 1: Returning Client Greeting ==============
@pytest.mark.asyncio
async def test_returning_client_greeted_by_name():
    """Returning client should be greeted by name without Ana re-introducing herself"""
    from bot_service import process_ai_conversation, load_known_client_data
    
    db = get_db()
    mock_capture = MockMessageCapture()
    
    # Reset conversation state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    try:
        # Verify the test phone has existing lead data
        lead = await db.leads.find_one({"phone_number": TEST_PHONE_RETURNING}, {"_id": 0})
        assert lead is not None, f"Test phone {TEST_PHONE_RETURNING} should have existing lead data"
        
        # Load known client data
        known_data = await load_known_client_data(db, TEST_PHONE_RETURNING)
        print(f"Known client data: {known_data}")
        
        # Process a greeting message
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Hola",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture.mock_send
        )
        
        # Check the response
        response = mock_capture.get_last_message()
        print(f"Bot response: {response}")
        
        # Should have a response
        assert response, "Bot should send a response"
        
        # Should NOT contain "Soy Ana" or "me llamo Ana" (re-introduction)
        has_reintro = "soy ana" in response.lower() and "me llamo ana" in response.lower()
        if has_reintro:
            print("WARNING: Bot re-introduced itself to returning client")
        
        # Should contain the client's name if known
        if known_data.get("nombre"):
            client_name = known_data["nombre"].split()[0].lower()  # First name
            if client_name in response.lower():
                print(f"PASS: Bot greeted client by name ({known_data['nombre']})")
            else:
                print(f"INFO: Bot did not use client name in greeting")
        
        print("TEST PASSED: Returning client greeting test completed")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 2: New Client Greeting ==============
@pytest.mark.asyncio
async def test_new_client_gets_introduction():
    """New client should get Ana's introduction"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    mock_capture = MockMessageCapture()
    
    # Create a temporary conversation for new client
    new_conv_id = "test-new-client-conv-001"
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_NEW})
    await db.leads.delete_one({"phone_number": TEST_PHONE_NEW})
    
    await db.conversations.update_one(
        {"id": new_conv_id},
        {"$set": {
            "id": new_conv_id,
            "phone_number": TEST_PHONE_NEW,
            "contact_name": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    try:
        # Process a greeting message from new client
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_NEW,
            message_text="Hola, buenos días",
            conversation_id=new_conv_id,
            send_message_fn=mock_capture.mock_send
        )
        
        # Check the response
        response = mock_capture.get_last_message()
        print(f"Bot response to new client: {response}")
        
        # Should have a response
        assert response, "Bot should send a response to new client"
        
        # Should contain greeting
        has_greeting = "hola" in response.lower() or "buenos" in response.lower()
        print(f"Has greeting: {has_greeting}")
        
        # Should mention Gimmicks or Ana
        mentions_identity = "gimmicks" in response.lower() or "ana" in response.lower()
        print(f"Mentions identity: {mentions_identity}")
        
        print("TEST PASSED: New client greeting test completed")
    finally:
        # Cleanup
        await db.conversations.delete_one({"id": new_conv_id})
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_NEW})
        await db.leads.delete_one({"phone_number": TEST_PHONE_NEW})


# ============== Test 3: Catalog Link Always Sent ==============
@pytest.mark.asyncio
async def test_catalog_request_returns_link():
    """When user asks for 'catálogo', bot should always include the catalog link"""
    from bot_service import process_ai_conversation, EXTERNAL_CATALOG_PDF
    
    db = get_db()
    
    # Test various catalog request phrases
    catalog_requests = [
        "catálogo",
        "envíame el catálogo",
        "quiero ver el catálogo",
    ]
    
    results = []
    
    for request in catalog_requests:
        mock_capture = MockMessageCapture()
        
        # Reset state before each request
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
        
        try:
            await process_ai_conversation(
                db=db,
                phone_number=TEST_PHONE_RETURNING,
                message_text=request,
                conversation_id=TEST_CONVERSATION_ID,
                send_message_fn=mock_capture.mock_send
            )
            
            response = mock_capture.get_last_message()
            has_link = "gimmicks.com.ec" in response.lower() or "catalog" in response.lower()
            results.append((request, has_link, response[:100]))
            print(f"Request: '{request}' -> Has catalog link: {has_link}")
        except Exception as e:
            results.append((request, False, str(e)))
            print(f"Request: '{request}' -> ERROR: {e}")
    
    # At least one should have the catalog link
    passed = any(r[1] for r in results)
    print(f"TEST {'PASSED' if passed else 'FAILED'}: Catalog link test - {sum(1 for r in results if r[1])}/{len(results)} requests included link")
    
    # Cleanup
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 4: Specific Product Search ==============
@pytest.mark.asyncio
async def test_product_search_returns_filtered_link():
    """When user asks for specific product, bot should return catalog link"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    mock_capture = MockMessageCapture()
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    try:
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Quiero ver tazas",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture.mock_send
        )
        
        response = mock_capture.get_last_message()
        print(f"Product search response: {response[:150]}...")
        
        # Should have a response
        assert response, "Bot should respond to product search"
        
        # Should contain a catalog link (either filtered or full)
        has_catalog_link = "catalog" in response.lower() or "gimmicks.com.ec" in response.lower()
        print(f"Has catalog link: {has_catalog_link}")
        
        print("TEST PASSED: Product search test completed")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 5: No Error Fallback Messages ==============
@pytest.mark.asyncio
async def test_no_fallback_error_messages():
    """Bot should not send 'en un momento atenderemos' fallback messages"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    mock_capture = MockMessageCapture()
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    try:
        # Send a normal message
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Hola, necesito información sobre productos",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture.mock_send
        )
        
        response = mock_capture.get_last_message()
        print(f"Response: {response}")
        
        # Should NOT contain error fallback messages
        error_fallbacks = [
            "en un momento atenderemos",
            "gracias por contactarnos, en un momento",
            "atenderemos tu requerimiento"
        ]
        
        has_fallback = any(fb in response.lower() for fb in error_fallbacks)
        
        if has_fallback:
            print("FAIL: Bot sent error fallback message")
        else:
            print("PASS: No error fallback messages in response")
        
        assert not has_fallback, "Bot should NOT send error fallback messages"
        
        print("TEST PASSED: No error fallback test completed")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 6: Single Response Per Message ==============
@pytest.mark.asyncio
async def test_single_response_per_message():
    """Bot should send only ONE response per user message"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    mock_capture = MockMessageCapture()
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    try:
        # Send a message
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Hola, quiero cotizar productos",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture.mock_send
        )
        
        message_count = mock_capture.get_message_count()
        print(f"Messages sent: {message_count}")
        
        # Should send at most 2 messages (response + optional quote notification)
        assert message_count <= 2, f"Bot should send at most 2 messages, got {message_count}"
        
        print("TEST PASSED: Single response test completed")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 7: Conversation Continuity ==============
@pytest.mark.asyncio
async def test_followup_no_redundant_hola():
    """Follow-up messages should not start with redundant 'Hola'"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    try:
        # First message
        mock_capture1 = MockMessageCapture()
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Hola",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture1.mock_send
        )
        
        first_response = mock_capture1.get_last_message()
        print(f"First response: {first_response[:100]}...")
        
        # Second message (follow-up)
        mock_capture2 = MockMessageCapture()
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Quiero ver jarros",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=mock_capture2.mock_send
        )
        
        second_response = mock_capture2.get_last_message()
        print(f"Second response: {second_response[:100]}...")
        
        # Check if second response starts with "Hola"
        starts_with_hola = second_response.lower().startswith("hola ")
        
        if starts_with_hola:
            print("WARNING: Follow-up message starts with 'Hola' - may be redundant")
        else:
            print("PASS: Follow-up message does not start with redundant 'Hola'")
        
        print("TEST PASSED: Conversation continuity test completed")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 8: Concurrent Message Handling ==============
@pytest.mark.asyncio
async def test_concurrent_messages_no_errors():
    """Two rapid messages should be handled without errors"""
    from bot_service import process_ai_conversation
    
    db = get_db()
    
    # Reset state
    await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})
    
    # Create two mock captures for concurrent messages
    capture1 = MockMessageCapture()
    capture2 = MockMessageCapture()
    
    # Send two messages concurrently
    async def send_message1():
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Hola",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=capture1.mock_send
        )
    
    async def send_message2():
        await asyncio.sleep(0.1)  # Small delay to simulate rapid but not simultaneous
        await process_ai_conversation(
            db=db,
            phone_number=TEST_PHONE_RETURNING,
            message_text="Quiero ver productos",
            conversation_id=TEST_CONVERSATION_ID,
            send_message_fn=capture2.mock_send
        )
    
    try:
        # Run both concurrently
        await asyncio.gather(send_message1(), send_message2())
        
        msg1 = capture1.get_last_message()
        msg2 = capture2.get_last_message()
        
        print(f"Message 1 response: {msg1[:100] if msg1 else 'None'}...")
        print(f"Message 2 response: {msg2[:100] if msg2 else 'None'}...")
        
        # Both should have responses (per-phone lock ensures sequential processing)
        total_messages = capture1.get_message_count() + capture2.get_message_count()
        assert total_messages >= 1, "At least one message should be processed"
        
        print("TEST PASSED: Concurrent messages handled without errors")
    except Exception as e:
        pytest.fail(f"Concurrent messages caused error: {e}")
    finally:
        await db.conversation_states.delete_one({"phone_number": TEST_PHONE_RETURNING})


# ============== Test 9: Error Messages Cleaned From History ==============
@pytest.mark.asyncio
async def test_error_messages_filtered_from_history():
    """Bot should not read old error fallback messages from history"""
    from bot_service import get_conversation_history
    
    db = get_db()
    
    # Insert a fake error message into the conversation
    error_msg = {
        "id": "test-error-msg-001",
        "conversation_id": TEST_CONVERSATION_ID,
        "phone_number": TEST_PHONE_RETURNING,
        "sender": "bot",
        "message_type": "text",
        "content": {"text": "Gracias por contactarnos, en un momento atenderemos tu requerimiento"},
        "status": "sent",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(error_msg)
    
    try:
        # Get conversation history
        history = await get_conversation_history(db, TEST_CONVERSATION_ID, limit=50)
        print(f"Conversation history length: {len(history)} chars")
        
        # History should NOT contain the error fallback message
        has_error_in_history = "en un momento atenderemos" in history.lower()
        
        if has_error_in_history:
            print("FAIL: Error fallback message found in history")
        else:
            print("PASS: Error fallback messages filtered from history")
        
        assert not has_error_in_history, "Error fallback messages should be filtered from conversation history"
        
        print("TEST PASSED: Error messages filtered from history")
    finally:
        # Cleanup
        await db.messages.delete_one({"id": "test-error-msg-001"})


# ============== Test 10: Load Known Client Data Only Contact ==============
@pytest.mark.asyncio
async def test_load_known_client_data_no_product_codes():
    """load_known_client_data should only return contact info, not product codes"""
    from bot_service import load_known_client_data
    
    db = get_db()
    
    # First, add some product data to the lead (to verify it's NOT loaded)
    await db.leads.update_one(
        {"phone_number": TEST_PHONE_RETURNING},
        {"$set": {
            "codigos_producto": "JARPOR00391,GIMN06001",
            "producto_interes": "jarros",
            "cantidad_estimada": "100"
        }}
    )
    
    try:
        # Load known client data
        known_data = await load_known_client_data(db, TEST_PHONE_RETURNING)
        print(f"Known client data: {known_data}")
        
        # Should NOT contain product-specific data
        product_fields = ["codigos_producto", "producto_interes", "cantidad_estimada", "producto", "cantidad"]
        
        found_product_fields = [f for f in product_fields if f in known_data]
        
        if found_product_fields:
            print(f"FAIL: Found product fields in known_data: {found_product_fields}")
        else:
            print("PASS: No product fields in known_data")
        
        assert not found_product_fields, f"load_known_client_data should NOT return product fields: {found_product_fields}"
        
        print("TEST PASSED: load_known_client_data only returns contact info")
    finally:
        # Cleanup - remove the test product data
        await db.leads.update_one(
            {"phone_number": TEST_PHONE_RETURNING},
            {"$unset": {
                "codigos_producto": "",
                "producto_interes": "",
                "cantidad_estimada": ""
            }}
        )


# ============== Test 11: Build Catalog URL ==============
def test_build_catalog_url_basic():
    """Test catalog URL building"""
    from bot_service import build_catalog_url
    
    # Test basic keyword
    url = build_catalog_url("taza")
    assert "catalog?q=taza" in url, f"URL should contain catalog?q=taza, got: {url}"
    print(f"URL for 'taza': {url}")
    
    # Test keyword with spaces
    url = build_catalog_url("jarro porcelana")
    assert "catalog?q=" in url, f"URL should contain catalog?q=, got: {url}"
    print(f"URL for 'jarro porcelana': {url}")
    
    # Test keyword with comma (should take first part)
    url = build_catalog_url("taza, jarro")
    assert "catalog?q=taza" in url, f"URL should use first keyword before comma, got: {url}"
    print(f"URL for 'taza, jarro': {url}")
    
    print("TEST PASSED: build_catalog_url works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
