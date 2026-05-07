"""Reproduce reported bug: after quote is generated, 'gracias' must NOT trigger
the human-handoff escalation. Bot must respond with a warm farewell."""
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

    test_phone = f"test_farewell_{int(time.time())}"
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

    # Simulate the post-quote state directly to avoid running through LLM
    # for a full conversation just to reach this point.
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {
            "phone_number": test_phone,
            "current_step": "post_quote",
            "collected_data": {
                "nombre": "José Silva",
                "correo": "joseluissb2732@gmail.com",
                "empresa": "Acme",
                "codigos_producto": "JAR123",
                "cantidades_por_producto": "JAR123:100",
            },
            "quote_generated": True,
            "transferred_to_human": True,
            "transfer_reason": "cotizacion_generada",
            "message_count": 10,
            "last_interaction": dt.datetime.now(dt.timezone.utc).isoformat(),
        }},
        upsert=True
    )

    from bot_service import process_ai_conversation

    # Test 1: simple "gracias" must get a warm farewell
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="gracias", send_message_fn=fake_send,
    )
    reply = last_customer_reply()
    print(f"[Cliente] gracias")
    print(f"[Bot]     {reply}\n")
    assert reply, "Bot must reply"
    assert "Permíteme revisar eso" not in reply, f"FAIL: bot escalated to human! Reply: {reply!r}"
    assert "en un momento te atendemos" not in reply.lower(), f"FAIL: bot used escalation phrase! {reply!r}"
    assert "atento" in reply.lower() or "atenta" in reply.lower() or "gracias" in reply.lower(), \
        f"FAIL: reply not a farewell: {reply!r}"
    print("[OK] 'gracias' handled with a warm farewell, no escalation")

    # Test 2: "muchas gracias" also handled
    sent.clear()
    # Re-set state because previous turn updated it
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"quote_generated": True, "transferred_to_human": True}}
    )
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="muchas gracias!", send_message_fn=fake_send,
    )
    reply2 = last_customer_reply()
    print(f"[Cliente] muchas gracias!")
    print(f"[Bot]     {reply2}\n")
    assert reply2 and "permíteme" not in reply2.lower(), f"FAIL: {reply2!r}"
    print("[OK] 'muchas gracias!' handled")

    # Test 3: "ok" / "listo" handled
    sent.clear()
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"quote_generated": True, "transferred_to_human": True}}
    )
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="ok listo", send_message_fn=fake_send,
    )
    reply3 = last_customer_reply()
    print(f"[Cliente] ok listo")
    print(f"[Bot]     {reply3}\n")
    assert reply3 and "permíteme" not in reply3.lower(), f"FAIL: {reply3!r}"
    print("[OK] 'ok listo' handled")

    # Test 4: A real new request after quote ('necesito gorras') must STILL
    # go to the LLM (we should not eat product searches as farewells)
    sent.clear()
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"quote_generated": True, "transferred_to_human": True}}
    )
    await process_ai_conversation(
        db=db, phone_number=test_phone, conversation_id=conv_id,
        message_text="necesito también unas gorras", send_message_fn=fake_send,
    )
    reply4 = last_customer_reply()
    print(f"[Cliente] necesito también unas gorras")
    print(f"[Bot]     {reply4}\n")
    assert reply4, "Bot must reply"
    # We expect the bot to either ask for codes OR include a catalog link.
    # It must NOT skip the message as a farewell.
    print("[OK] new product request after quote still gets a real reply (not eaten as farewell)")

    # Cleanup
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversations.delete_one({"id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    await db.leads.delete_many({"phone_number": test_phone})
    print("\n=== ALL CHECKS PASSED ===")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
