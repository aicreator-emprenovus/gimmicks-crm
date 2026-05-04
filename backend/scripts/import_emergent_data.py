"""Import a JSON export (produced by export_emergent_data.py) into this database.
Run on the TARGET environment AFTER deploy.

Behavior:
- Idempotent: documents are upserted by `id` (or `code` for products,
  `phone_number` for conversations/conversation_states).
- Existing data on the target is NOT deleted; only matching docs are replaced
  and new ones inserted.
- product_images binary data is NOT included in the export; binaries live in
  Object Storage and are accessible from any environment sharing the same
  EMERGENT_LLM_KEY.
"""
import asyncio
import json
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "gimmicks_crm")
IN_FILE = os.environ.get("IMPORT_FILE", "/app/backups/emergent_full_export.json")

# Per-collection unique key for upserts
KEY_BY_COLLECTION = {
    "products": "code",
    "conversations": "phone_number",
    "conversation_states": "phone_number",
    "users": "email",
    "counters": "_id",  # special — uses _id
}
DEFAULT_KEY = "id"


async def upsert_collection(db, name: str, docs: list[dict]) -> dict:
    if not docs:
        return {"inserted": 0, "updated": 0, "skipped": 0}
    coll = db[name]
    key = KEY_BY_COLLECTION.get(name, DEFAULT_KEY)
    inserted = updated = skipped = 0
    for doc in docs:
        if key not in doc:
            skipped += 1
            continue
        kv = doc[key]
        existing = await coll.find_one({key: kv}, {"_id": 1})
        if existing:
            await coll.replace_one({key: kv}, doc)
            updated += 1
        else:
            await coll.insert_one(doc)
            inserted += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


async def main():
    if not os.path.exists(IN_FILE):
        print(f"[ERROR] Archivo no encontrado: {IN_FILE}")
        print("Asegúrate de que el archivo /app/backups/emergent_full_export.json esté presente en el deploy.")
        sys.exit(1)

    with open(IN_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)

    meta = payload.get("_meta", {})
    print(f"[INFO] Importando export del {meta.get('exported_at')}")
    print(f"[INFO] Total documentos: {meta.get('total_documents')}")
    print(f"[INFO] Destino: {MONGO_URL.split('@')[-1]}/{DB_NAME}\n")

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.command("ping")

    grand = {"inserted": 0, "updated": 0, "skipped": 0}
    for name, docs in payload.get("collections", {}).items():
        stats = await upsert_collection(db, name, docs)
        grand["inserted"] += stats["inserted"]
        grand["updated"] += stats["updated"]
        grand["skipped"] += stats["skipped"]
        print(f"  {name:25s} inserted={stats['inserted']}, updated={stats['updated']}, skipped={stats['skipped']}")

    print(f"\n[DONE] inserted={grand['inserted']}, updated={grand['updated']}, skipped={grand['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())
