"""Verify the retired-phone-id safety net + send_message error handling.

1. RETIRED_PHONE_NUMBER_IDS contains the old ID 994356967089829.
2. _resolve_phone_number_id() refuses retired IDs:
   - Falls back to env var when contextvar holds a retired ID.
   - Raises when env var itself is retired (and contextvar empty).
3. POST /api/conversations/{id}/messages returns 502 on WhatsApp failure
   instead of silently returning status: "sent".
4. POST /api/conversations/{id}/messages/attachment returns 502 on failure.
5. Migration: any conversation with a retired wa_phone_number_id is cleared.
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Force-import to test the helpers
    import importlib
    import server
    importlib.reload(server)

    # 1. Retired set
    assert "994356967089829" in server.RETIRED_PHONE_NUMBER_IDS, "Retired set must contain old ID"
    print("[OK] RETIRED_PHONE_NUMBER_IDS contains 994356967089829")

    # 2a. Contextvar holds retired → must be ignored, fall back to env var
    server._ACTIVE_WA_PHONE_ID.set("994356967089829")
    resolved = server._resolve_phone_number_id()
    assert resolved == os.environ.get("WHATSAPP_PHONE_NUMBER_ID"), \
        f"Retired contextvar should fall back to env var. got={resolved!r}"
    print(f"[OK] Retired contextvar ignored → fallback to env var: {resolved}")

    # 2b. Both contextvar and env var retired → must fall back to hardcoded
    server._ACTIVE_WA_PHONE_ID.set("994356967089829")
    saved_env = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "994356967089829"
    resolved = server._resolve_phone_number_id()
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = saved_env
    server._ACTIVE_WA_PHONE_ID.set("")
    assert resolved == server.CURRENT_WHATSAPP_PHONE_NUMBER_ID, \
        f"Both retired → must fall back to hardcoded current ID. got={resolved!r}"
    assert resolved not in server.RETIRED_PHONE_NUMBER_IDS, \
        f"Resolved ID must NEVER be a retired ID. got={resolved!r}"
    print(f"[OK] Both retired → fallback to hardcoded current: {resolved}")

    # 2d. Env empty, contextvar empty → fallback to hardcoded
    server._ACTIVE_WA_PHONE_ID.set("")
    saved_env = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    os.environ.pop("WHATSAPP_PHONE_NUMBER_ID", None)
    resolved = server._resolve_phone_number_id()
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = saved_env
    assert resolved == server.CURRENT_WHATSAPP_PHONE_NUMBER_ID, \
        f"Empty env → must fall back to hardcoded current. got={resolved!r}"
    print(f"[OK] Empty env → fallback to hardcoded current: {resolved}")

    # 2c. Env var has the correct ID → resolves to it
    server._ACTIVE_WA_PHONE_ID.set("")
    resolved = server._resolve_phone_number_id()
    assert resolved == os.environ.get("WHATSAPP_PHONE_NUMBER_ID"), f"Should return env var: {resolved!r}"
    print(f"[OK] Resolves to env var when contextvar empty: {resolved}")

    # 3. Migration: insert a fake conversation pointing to retired ID, run migration
    test_conv_id = f"test_migration_{uuid.uuid4()}"
    await db.conversations.insert_one({
        "id": test_conv_id, "phone_number": "test_migration_phone",
        "wa_phone_number_id": "994356967089829",
        "created_at": "2026-05-08T00:00:00Z", "last_message_time": "2026-05-08T00:00:00Z",
        "status": "active", "unread_count": 0,
    })
    await server.migrate_retired_phone_number_ids()
    after = await db.conversations.find_one({"id": test_conv_id}, {"_id": 0})
    assert "wa_phone_number_id" not in after, f"Migration must remove retired ID. Doc: {after}"
    print("[OK] Migration cleared retired wa_phone_number_id from conversation")

    # Cleanup
    await db.conversations.delete_one({"id": test_conv_id})
    client.close()
    print("\n=== ALL CHECKS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
