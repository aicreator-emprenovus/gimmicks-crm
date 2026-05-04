"""Export ALL critical MongoDB data from this Emergent preview to a single JSON file.
Run BEFORE deploying to Emergent production. The output file is portable.
Object Storage images do NOT need to be exported — they live outside the DB and
are accessible from any environment that has the same EMERGENT_LLM_KEY.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "gimmicks_crm"
OUT_FILE = "/app/backups/emergent_full_export.json"

# Collections to export. Order matters: dependents after parents.
COLLECTIONS = [
    "users",
    "automation_rules",
    "catalog_config",
    "counters",
    "products",
    "product_images",  # contains storage_path refs (no binary data)
    "clients",
    "leads",
    "conversations",
    "messages",
    "conversation_states",
    "quotes",
    "quotes_v2",
    "activity_log",
    "audit_logs",
    "client_activities",
    "document_activities",
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    out = {
        "_meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_db": DB_NAME,
            "tool_version": 1,
        },
        "collections": {},
    }

    total_docs = 0
    for coll_name in COLLECTIONS:
        docs = await db[coll_name].find({}, {"_id": 0}).to_list(100000)
        # product_images: drop the legacy `data` field if present (binary). We only
        # need the storage_path / id references. Binaries are in Object Storage.
        if coll_name == "product_images":
            for d in docs:
                d.pop("data", None)
        out["collections"][coll_name] = docs
        total_docs += len(docs)
        print(f"  {coll_name}: {len(docs)}")

    out["_meta"]["total_documents"] = total_docs

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)

    size_mb = os.path.getsize(OUT_FILE) / (1024 * 1024)
    print(f"\n[OK] {total_docs} documentos exportados a {OUT_FILE} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
