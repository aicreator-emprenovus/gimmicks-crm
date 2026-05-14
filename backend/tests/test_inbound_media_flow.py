"""Inbound media flow test: simulate a WhatsApp webhook delivering an image,
and verify the message is persisted in the same format as outgoing attachments
(media_kind + storage_path), so AttachmentRenderer renders it instead of the
raw JSON.

We CANNOT call the real Graph API here (no creds/auth in preview), so we
monkey-patch `download_whatsapp_media` with a fake that returns a known PNG.
This validates ONLY the persistence/conversion layer; the real Graph download
is exercised by production traffic.
"""
import asyncio
import base64
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

    import server
    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )

    # Monkey-patch the WhatsApp download so we don't hit the real API
    async def fake_download(media_id):
        return tiny_png, "image/jpeg", f"{media_id}.jpg"

    original = server.download_whatsapp_media
    server.download_whatsapp_media = fake_download

    test_phone = f"test_inbound_{int(time.time())}"
    fake_webhook_msg = {
        "from": test_phone,
        "id": f"wamid.test_{uuid.uuid4()}",
        "timestamp": str(int(time.time())),
        "type": "image",
        "image": {
            "caption": "necesito cotizar 8 de estos exhibidores",
            "mime_type": "image/jpeg",
            "id": "test_media_id_12345",
        },
    }
    fake_metadata = {"phone_number_id": "965777766626628"}

    try:
        await server.process_incoming_message(fake_webhook_msg, fake_metadata)

        # Inspect what was persisted
        msg = await db.messages.find_one({"phone_number": test_phone}, {"_id": 0})
        assert msg, "Message not stored"
        c = msg["content"]
        print(f"stored content keys: {list(c.keys())}")
        assert c.get("media_kind") == "image", f"media_kind expected 'image', got {c.get('media_kind')!r}"
        assert c.get("mime_type") == "image/jpeg", f"mime_type wrong: {c.get('mime_type')!r}"
        assert c.get("storage_path", "").startswith("gimmicks-crm/inbox-attachments/"), \
            f"storage_path wrong: {c.get('storage_path')!r}"
        assert c.get("text") == "necesito cotizar 8 de estos exhibidores", \
            f"caption not preserved: {c.get('text')!r}"
        assert c.get("size") == len(tiny_png), f"size wrong: {c.get('size')}"
        assert "raw" not in c, "raw JSON should not be in content for successful media downloads"
        print(f"[OK] message persisted with media_kind=image, storage_path={c['storage_path']}")

        # Sidebar preview — the customer's caption triggered the bot which
        # replied; bot reply is now the latest message and rules the sidebar.
        # The important thing is that the sidebar NEVER shows the raw JSON.
        conv = await db.conversations.find_one({"phone_number": test_phone}, {"_id": 0})
        assert conv, "Conversation not created"
        preview = conv.get("last_message", "")
        assert "raw" not in preview and "wamid" not in preview and "\"image\"" not in preview, \
            f"sidebar leaked JSON: {preview!r}"
        print(f"[OK] sidebar preview is clean text (not JSON): {preview[:60]!r}")

        # Test the GET attachment endpoint resolves this attachment correctly
        import re as _re
        m = _re.search(r"inbox-attachments/([^./]+)", c["storage_path"])
        attachment_id = m.group(1)
        # Just verify the message can be found via the attachment_id regex
        found = await db.messages.find_one(
            {"content.storage_path": {"$regex": f"/{attachment_id}\\."}},
            {"_id": 0, "id": 1}
        )
        assert found, "GET attachment endpoint query would fail"
        print(f"[OK] attachment_id={attachment_id} retrievable by GET endpoint")

        # Cleanup
        await db.messages.delete_many({"phone_number": test_phone})
        await db.conversations.delete_many({"phone_number": test_phone})
        await db.leads.delete_many({"phone_number": test_phone})
        await db.conversation_states.delete_many({"phone_number": test_phone})

        # --- Scenario 2: image WITHOUT caption → bot must NOT respond ---
        test_phone2 = f"test_inbound_nocap_{int(time.time())}"
        fake_webhook_msg2 = {
            "from": test_phone2,
            "id": f"wamid.nocap_{uuid.uuid4()}",
            "timestamp": str(int(time.time())),
            "type": "image",
            "image": {"mime_type": "image/jpeg", "id": "media_nocap_123"},
        }
        await server.process_incoming_message(fake_webhook_msg2, fake_metadata)
        msgs = await db.messages.find({"phone_number": test_phone2}).to_list(10)
        senders = [m["sender"] for m in msgs]
        assert "user" in senders, "user image not stored"
        assert "business" not in senders, f"bot replied to caption-less media: {msgs}"
        print("[OK] image without caption → bot does NOT trigger")

        # Cleanup scenario 2
        await db.messages.delete_many({"phone_number": test_phone2})
        await db.conversations.delete_many({"phone_number": test_phone2})
        await db.leads.delete_many({"phone_number": test_phone2})

        print("\n=== INBOUND MEDIA FLOW: ALL CHECKS PASSED ===")
    finally:
        server.download_whatsapp_media = original
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
