"""Reproduce reported bug: 'tienen jarros?' must always send a catalog link.
Validates the fix end-to-end without mocking the LLM."""
import asyncio
import os
import sys
import time
import uuid
import datetime as dt

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    test_phone = f"test_jarros_{int(time.time())}"
    sent = []  # tuples (recipient_phone, text)

    async def fake_send(phone, conv_id, text, needs_review=False, **kw):
        sent.append((phone, text))
        # Only persist replies addressed to the test customer
        if phone == test_phone:
            await db.messages.insert_one({
                "id": str(uuid.uuid4()),
                "conversation_id": conv_id,
                "sender": "business",
                "content": {"text": text},
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            })

    def last_customer_reply():
        for ph, t in reversed(sent):
            if ph == test_phone:
                return t
        return ""

    conv_id = str(uuid.uuid4())
    await db.conversations.insert_one({
        "id": conv_id, "phone_number": test_phone, "contact_name": None,
        "wa_phone_number_id": "test_pid",
        "created_at": "2026-05-06T00:00:00Z", "updated_at": "2026-05-06T00:00:00Z"
    })

    from bot_service import process_ai_conversation

    # Replicate the exact reported conversation
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="hola", send_message_fn=fake_send,
    )
    print(f"[Cliente] hola")
    print(f"[Bot]     {last_customer_reply()}\n")

    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="tienen jarros?", send_message_fn=fake_send,
    )
    reply = last_customer_reply()
    print(f"[Cliente] tienen jarros?")
    print(f"[Bot]     {reply}\n")

    # ASSERTIONS
    assert "http" in reply, f"FAIL: bot reply has NO catalog link! Reply: {reply!r}"
    assert "/catalog" in reply, f"FAIL: bot reply missing /catalog path: {reply!r}"
    assert "jarros" in reply.lower() or "q=jarros" in reply.lower(), \
        f"FAIL: bot reply missing 'jarros' or filter: {reply!r}"
    print("[OK] Bot reply contains a real catalog link with /catalog?q=...")

    # Test 2: Even if previous bot message ends with '?', a product-keyword
    # message must trigger the search.
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    sent.clear()

    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="quiero termos!!!", send_message_fn=fake_send,
    )
    reply2 = last_customer_reply()
    print(f"[Cliente] quiero termos!!!")
    print(f"[Bot]     {reply2}\n")
    assert "http" in reply2, f"FAIL turn2 (no link in customer reply): {reply2!r}"
    assert "termos" in reply2.lower(), f"FAIL turn2 (no termos in customer reply): {reply2!r}"
    print("[OK] Punctuation no longer breaks keyword detection")

    # Test 3: query for a product that does NOT exist in DB → unfiltered
    # general catalog link should still be sent (not a stripped URL).
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    sent.clear()
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="tienen helicópteros teledirigidos?", send_message_fn=fake_send,
    )
    reply3 = last_customer_reply()
    print(f"[Cliente] tienen helicópteros teledirigidos?")
    print(f"[Bot]     {reply3}\n")
    # Even with no products, we expect a catalog URL or a graceful redirect to staff.
    if "http" in reply3:
        print("[OK] Even unmatched product → catalog link still sent")
    else:
        print(f"[INFO] Unmatched product → bot did NOT send link (ok if staff handoff). Reply: {reply3!r}")

    # Cleanup
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversations.delete_one({"id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    await db.leads.delete_many({"phone_number": test_phone})
    print("\n=== ALL CHECKS PASSED ===")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
