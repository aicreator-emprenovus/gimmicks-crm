"""Verify agent-alerts persistence: a notification call still reaches
db.pending_agent_alerts even when both text and template send fail."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    import bot_service, server

    # Force both send_whatsapp_message and send_whatsapp_template to fail.
    async def fail_text(*a, **kw):
        raise Exception("(#131047) Re-engagement message")
    async def fail_template(*a, **kw):
        raise Exception("Template alerta_agente_humano not found in Meta")

    saved_text = server.send_whatsapp_message
    saved_tmpl = server.send_whatsapp_template
    server.send_whatsapp_message = fail_text
    server.send_whatsapp_template = fail_template
    try:
        before = await db.pending_agent_alerts.count_documents({})
        result = await bot_service._send_to_human_agent(
            "Test alert body",
            ["TestTitle", "Customer X", "Action hint"],
            db,
            alert_kind="test_failure",
        )
        after = await db.pending_agent_alerts.count_documents({})

        assert result is False, "_send_to_human_agent should return False when both deliveries fail"
        assert after == before + 1, f"alert must be persisted even on full failure (before={before} after={after})"
        latest = await db.pending_agent_alerts.find_one({"kind": "test_failure"}, sort=[("created_at", -1)])
        assert latest["delivered_via"] == "none"
        assert "131047" in (latest.get("error") or "")
        print(f"[OK] Full delivery failure → persisted in pending_agent_alerts (delivered_via=none)")
        await db.pending_agent_alerts.delete_one({"id": latest["id"]})

        # Now: text-only success path
        async def ok_text(*a, **kw): return "wamid_ok"
        server.send_whatsapp_message = ok_text
        await bot_service._send_to_human_agent("Test ok", ["T", "C", "H"], db, alert_kind="test_success")
        latest = await db.pending_agent_alerts.find_one({"kind": "test_success"}, sort=[("created_at", -1)])
        assert latest["delivered_via"] == "text"
        print(f"[OK] Text-only success → delivered_via=text")
        await db.pending_agent_alerts.delete_one({"id": latest["id"]})

        # Template fallback path
        server.send_whatsapp_message = fail_text
        async def ok_tmpl(*a, **kw): return "wamid_tmpl"
        server.send_whatsapp_template = ok_tmpl
        await bot_service._send_to_human_agent("Test tmpl", ["T", "C", "H"], db, alert_kind="test_tmpl")
        latest = await db.pending_agent_alerts.find_one({"kind": "test_tmpl"}, sort=[("created_at", -1)])
        assert latest["delivered_via"] == "template"
        print(f"[OK] 24h window expired → template fallback → delivered_via=template")
        await db.pending_agent_alerts.delete_one({"id": latest["id"]})

        print("\n=== AGENT ALERT FALLBACK CHAIN: ALL CHECKS PASSED ===")
    finally:
        server.send_whatsapp_message = saved_text
        server.send_whatsapp_template = saved_tmpl
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
