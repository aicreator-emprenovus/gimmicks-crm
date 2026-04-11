"""
Production data sync service.
Syncs conversations, messages, and leads from the production Railway MongoDB
to the local preview database so the Inbox shows real-time data.
"""
import os
import logging
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# automation_rules are managed via the panel and pushed TO production.
# They should NOT be pulled FROM production to avoid overwriting user edits.
COLLECTIONS_TO_SYNC = ["leads", "conversations", "messages"]


async def sync_from_production(local_db: AsyncIOMotorDatabase) -> dict:
    """
    Pull data from production MongoDB and upsert into local DB.
    Returns stats about what was synced.
    """
    prod_url = os.environ.get("PROD_MONGO_URL")
    if not prod_url:
        return {"error": "PROD_MONGO_URL not configured", "synced": False}

    prod_db_name = os.environ.get("PROD_DB_NAME", "gimmicks_crm")
    stats = {}

    try:
        prod_client = AsyncIOMotorClient(prod_url, serverSelectionTimeoutMS=5000)
        prod_db = prod_client[prod_db_name]
        # Quick connectivity test
        await prod_db.command("ping")

        for collection_name in COLLECTIONS_TO_SYNC:
            prod_coll = prod_db[collection_name]
            local_coll = local_db[collection_name]

            prod_docs = await prod_coll.find({}, {"_id": 0}).to_list(10000)
            inserted = 0
            updated = 0

            for doc in prod_docs:
                doc_id = doc.get("id")
                if not doc_id:
                    continue

                existing = await local_coll.find_one({"id": doc_id})
                if existing:
                    await local_coll.replace_one({"id": doc_id}, doc)
                    updated += 1
                else:
                    await local_coll.insert_one(doc)
                    inserted += 1

            stats[collection_name] = {"inserted": inserted, "updated": updated, "total_prod": len(prod_docs)}

        prod_client.close()
        return {"synced": True, "timestamp": datetime.now(timezone.utc).isoformat(), "stats": stats}

    except Exception as e:
        logger.error(f"Production sync failed: {e}")
        return {"error": str(e), "synced": False}


class BackgroundSyncTask:
    """Runs periodic sync in the background."""
    def __init__(self, local_db: AsyncIOMotorDatabase, interval_seconds: int = 120):
        self.local_db = local_db
        self.interval = interval_seconds
        self._task = None
        self.last_sync = None
        self.last_result = None

    async def _run_loop(self):
        while True:
            try:
                result = await sync_from_production(self.local_db)
                self.last_sync = datetime.now(timezone.utc).isoformat()
                self.last_result = result
                if result.get("synced"):
                    logger.info(f"Background sync completed: {result.get('stats', {})}")
                else:
                    logger.warning(f"Background sync failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Background sync error: {e}")
            await asyncio.sleep(self.interval)

    def start(self):
        if not self._task:
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Background sync started (interval: {self.interval}s)")

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
