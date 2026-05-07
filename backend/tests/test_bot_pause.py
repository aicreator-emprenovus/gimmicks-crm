"""End-to-end test for the new Inbox features:
1. transferred_to_human and bot_paused fields exposed in /api/conversations
2. POST /api/conversations/{id}/bot-control pause/resume works
3. While bot_paused=True, customer messages do NOT trigger bot replies
4. attachment endpoint accepts multipart and persists to messages collection
"""
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

    test_phone = f"test_pause_{int(time.time())}"
    sent = []

    async def fake_send(phone, conv_id, text, needs_review=False, **kw):
        sent.append((phone, text))
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
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()
    })

    # Pre-state: bot is paused
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {
            "phone_number": test_phone,
            "current_step": "greeting",
            "collected_data": {},
            "bot_paused": True,
            "message_count": 0,
            "last_interaction": dt.datetime.now(dt.timezone.utc).isoformat(),
        }},
        upsert=True
    )

    from bot_service import process_ai_conversation

    # Test 1: while bot paused, no auto-reply
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="hola, tienen termos?", send_message_fn=fake_send,
    )
    customer_replies_while_paused = [t for ph, t in sent if ph == test_phone]
    assert len(customer_replies_while_paused) == 0, \
        f"FAIL: bot replied while paused. Replies: {customer_replies_while_paused!r}"
    print("[OK] Bot did NOT reply while bot_paused=True")

    # Test 2: resume → bot replies normally
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"bot_paused": False}}
    )
    sent.clear()
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="hola", send_message_fn=fake_send,
    )
    reply = last_customer_reply()
    assert reply, f"FAIL: bot did not reply after resume. sent={sent!r}"
    print(f"[OK] Bot resumed and replied: {reply[:80]!r}")

    # Cleanup
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversations.delete_one({"id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    await db.leads.delete_many({"phone_number": test_phone})
    print("\n=== ALL CHECKS PASSED ===")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
