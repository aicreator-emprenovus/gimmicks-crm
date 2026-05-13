"""Master regression suite — protects every critical bot/inbox invariant.

Run before any change to bot_service.py or the inbox endpoints to make sure
nothing important was broken. Designed to be cheap (uses a fake send fn so
WhatsApp Cloud API is NOT actually called) and fast (<60 s).

Usage:
    cd /app/backend && set -a && source .env && set +a && python tests/run_bot_regression.py

Exit code 0 ⇒ everything is intact.
Exit code != 0 ⇒ a regression was introduced.
"""
import asyncio
import os
import sys
import time
import traceback
import uuid
import datetime as dt

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient

# Track results
RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    icon = "✅" if ok else "❌"
    print(f"{icon} {name}{(' — ' + detail) if detail else ''}")


# ---------------------------------------------------------------------------
# 1. Static invariants in code (no DB / LLM needed)
# ---------------------------------------------------------------------------
def test_static_invariants():
    import importlib
    import server, bot_service
    importlib.reload(server)
    importlib.reload(bot_service)

    # --- WhatsApp safety ---
    assert "994356967089829" in server.RETIRED_PHONE_NUMBER_IDS
    record("server.RETIRED_PHONE_NUMBER_IDS contains 994356967089829", True)

    assert server.CURRENT_WHATSAPP_PHONE_NUMBER_ID == "965777766626628"
    record("server.CURRENT_WHATSAPP_PHONE_NUMBER_ID == 965777766626628", True)

    # --- Staff notification routing ---
    assert bot_service.STAFF_NOTIFICATION_PHONE == "593999440910", \
        f"STAFF_NOTIFICATION_PHONE must be the HUMAN AGENT (593999440910), got {bot_service.STAFF_NOTIFICATION_PHONE!r}"
    record("STAFF_NOTIFICATION_PHONE points to human agent (593999440910)", True)
    assert bot_service.STAFF_NOTIFICATION_PHONE != "593963560326", \
        "The BOT's own number cannot be STAFF_NOTIFICATION_PHONE"
    record("STAFF_NOTIFICATION_PHONE is NOT the bot's number", True)

    # --- SYSTEM_PROMPT critical phrases ---
    sp = bot_service.SYSTEM_PROMPT
    checks = {
        "OBJETIVO GENERAL DEL AGENTE block present": "OBJETIVO GENERAL DEL AGENTE" in sp,
        "Closure msg uses new wording": "se pondrá en contacto contigo para los siguientes pasos" in sp,
        "5 line max rule": "Máximo 5 líneas" in sp,
        "URL example present": "https://cotizador.gimmicks.com.ec/catalog?q=producto" in sp,
        "Forbidden personalization rule": "serigrafía" in sp and "PROHIBIDO" in sp,
        "Tildes rule": "tildes" in sp.lower(),
        "Single message rule": "UN SOLO MENSAJE" in sp,
    }
    for k, v in checks.items():
        record(f"SYSTEM_PROMPT: {k}", v)

    # --- Code-level helpers exist and are wired ---
    assert callable(getattr(server, "_resolve_phone_number_id", None))
    record("server._resolve_phone_number_id exists", True)
    assert callable(getattr(server, "load_system_config_cache", None))
    record("server.load_system_config_cache exists", True)
    assert callable(getattr(bot_service, "fix_spanish_accents", None))
    record("bot_service.fix_spanish_accents exists", True)
    assert callable(getattr(bot_service, "strip_forbidden_personalization", None))
    record("bot_service.strip_forbidden_personalization exists", True)


# ---------------------------------------------------------------------------
# 2. _resolve_phone_number_id behavior under all scenarios
# ---------------------------------------------------------------------------
def test_resolver_cases():
    import server
    # contextvar retired → ignored
    server._ACTIVE_WA_PHONE_ID.set("994356967089829")
    saved = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "994356967089829"
    out = server._resolve_phone_number_id()
    server._ACTIVE_WA_PHONE_ID.set("")
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = saved
    record(
        "Resolver: ctx+env retired → hardcoded fallback",
        out == server.CURRENT_WHATSAPP_PHONE_NUMBER_ID,
        f"got {out}"
    )

    # All empty → hardcoded fallback
    saved = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    os.environ.pop("WHATSAPP_PHONE_NUMBER_ID", None)
    server._ACTIVE_WA_PHONE_ID.set("")
    out = server._resolve_phone_number_id()
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = saved
    record(
        "Resolver: all empty → hardcoded fallback",
        out == server.CURRENT_WHATSAPP_PHONE_NUMBER_ID,
        f"got {out}"
    )

    # Resolver never returns a retired ID
    record(
        "Resolver: never returns a retired ID",
        out not in server.RETIRED_PHONE_NUMBER_IDS,
    )


# ---------------------------------------------------------------------------
# 3. Spanish-accent post-processor
# ---------------------------------------------------------------------------
def test_accent_postprocessor():
    from bot_service import fix_spanish_accents
    cases = [
        ("Cotizacion lista", "Cotización lista"),
        ("Atencion al cliente", "Atención al cliente"),
        ("Codigo del producto", "Código del producto"),
        # interrogative fixes only apply inside ¿ ... ? — that's by design
        ("¿Como estas?", "Cómo"),
        ("¿Que necesitas?", "Qué"),
    ]
    ok = True
    for inp, expected in cases:
        out = fix_spanish_accents(inp)
        if expected not in out:
            ok = False
            record(f"accent_postprocessor failed for {inp!r}", False, f"got {out!r}, expected to contain {expected!r}")
    if ok:
        record("accent_postprocessor: 5/5 phrases corrected", True)


# ---------------------------------------------------------------------------
# 4. Forbidden-personalization stripper
# ---------------------------------------------------------------------------
def test_forbidden_personalization():
    from bot_service import strip_forbidden_personalization
    ok = True
    test_cases = [
        ("¿Quieres tu logotipo en serigrafía o bordado?", ["serigrafía", "bordado"]),
        ("Te ofrecemos sublimación, grabado láser o vinil.", ["sublimación", "grabado", "vinil"]),
    ]
    for text, banned_words in test_cases:
        out = strip_forbidden_personalization(text)
        for word in banned_words:
            if word.lower() in out.lower():
                ok = False
                record(f"strip_forbidden leaked {word!r} in {out!r}", False)
    if ok:
        record("strip_forbidden_personalization removes serigrafía/bordado/sublimación/etc.", True)


def test_json_leak_safety():
    """Bug May 8 2026: LLM emitted malformed JSON with trailing comma; raw dump
    leaked to customer. Verify the 3-tier defense is alive."""
    import json as _json
    from bot_service import _repair_json, _extract_response_field, _looks_like_json
    leaked = (
        '{ "response": "Hola Patricia, ¿tu empresa?", "extracted_data": {}, '
        '"intent": "saludo", "needs_quote": false, "needs_human": false, '
        '"conversation_summary": "...",\n}'
    )
    # Reproduces the original failure
    failed_strict = False
    try:
        _json.loads(leaked)
    except _json.JSONDecodeError:
        failed_strict = True
    record("Bug premise: leaked JSON fails strict parse", failed_strict)
    # Tier 1: repair
    try:
        parsed = _json.loads(_repair_json(leaked))
        record("JSON Tier 1: _repair_json fixes trailing comma", parsed.get("response", "").startswith("Hola Patricia"))
    except Exception as e:
        record("JSON Tier 1: _repair_json", False, str(e))
    # Tier 2: extract via regex
    fished = _extract_response_field(leaked)
    record("JSON Tier 2: _extract_response_field recovers field", fished.startswith("Hola Patricia"))
    # Tier 3: detector
    record("JSON Tier 3: _looks_like_json flags leak", _looks_like_json(leaked))
    record("JSON Tier 3: _looks_like_json does NOT false-positive on legit reply",
           not _looks_like_json("¡Claro! Aquí tienes el catálogo: https://x.com"))


# ---------------------------------------------------------------------------
# 5. End-to-end bot invariants (uses real LLM but with fake WhatsApp send)
# ---------------------------------------------------------------------------
async def test_e2e_invariants():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    test_phone = f"test_regression_{int(time.time())}"
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

    def last_reply():
        for ph, t in reversed(sent):
            if ph == test_phone:
                return t
        return ""

    conv_id = str(uuid.uuid4())
    await db.conversations.insert_one({
        "id": conv_id, "phone_number": test_phone, "contact_name": None,
        "wa_phone_number_id": "test_pid",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })

    from bot_service import process_ai_conversation

    # ----- Scenario A: short product query with '?' must trigger catalog link -----
    sent.clear()
    await db.conversation_states.delete_many({"phone_number": test_phone})
    await process_ai_conversation(db=db, phone_number=test_phone, conversation_id=conv_id, message_text="hola", send_message_fn=fake_send)
    await process_ai_conversation(db=db, phone_number=test_phone, conversation_id=conv_id, message_text="tienen jarros?", send_message_fn=fake_send)
    reply = last_reply()
    ok = ("http" in reply) and ("/catalog" in reply or "jarros" in reply.lower())
    record("E2E: 'tienen jarros?' → catalog link sent", ok, f"reply={reply[:80]!r}")

    # ----- Scenario B: post-quote 'gracias' must NOT escalate -----
    sent.clear()
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {
            "phone_number": test_phone,
            "current_step": "post_quote",
            "collected_data": {"nombre": "Test", "correo": "t@t.com", "empresa": "X"},
            "quote_generated": True,
            "transferred_to_human": True,
            "message_count": 5,
        }},
        upsert=True
    )
    await process_ai_conversation(db=db, phone_number=test_phone, conversation_id=conv_id, message_text="gracias", send_message_fn=fake_send)
    reply = last_reply()
    ok = bool(reply) and "Permíteme revisar" not in reply
    record("E2E: post-quote 'gracias' → cordial farewell, no escalation", ok, f"reply={reply[:80]!r}")

    # ----- Scenario C: bot_paused = True → bot stays silent -----
    sent.clear()
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"bot_paused": True, "quote_generated": False}}
    )
    await process_ai_conversation(db=db, phone_number=test_phone, conversation_id=conv_id, message_text="hola, tienen termos?", send_message_fn=fake_send)
    customer_replies = [t for ph, t in sent if ph == test_phone]
    record("E2E: bot_paused=True → no auto-reply", len(customer_replies) == 0, f"replies={len(customer_replies)}")

    # ----- Scenario D: resume → bot replies -----
    sent.clear()
    await db.conversation_states.update_one(
        {"phone_number": test_phone},
        {"$set": {"bot_paused": False}}
    )
    await process_ai_conversation(db=db, phone_number=test_phone, conversation_id=conv_id, message_text="hola", send_message_fn=fake_send)
    reply = last_reply()
    record("E2E: bot resumed → bot replies again", bool(reply), f"reply={reply[:60]!r}")

    # cleanup
    await db.messages.delete_many({"conversation_id": conv_id})
    await db.conversations.delete_one({"id": conv_id})
    await db.conversation_states.delete_many({"phone_number": test_phone})
    await db.leads.delete_many({"phone_number": test_phone})
    client.close()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def main():
    print("=" * 70)
    print("BOT REGRESSION SUITE — protects every critical invariant")
    print("=" * 70)

    suites = [
        ("Static invariants (code/SYSTEM_PROMPT)", test_static_invariants),
        ("Resolver phone-id behavior", test_resolver_cases),
        ("Accent post-processor", test_accent_postprocessor),
        ("Forbidden-personalization stripper", test_forbidden_personalization),
        ("JSON leak safety net", test_json_leak_safety),
    ]
    for name, fn in suites:
        print(f"\n— {name} —")
        try:
            fn()
        except AssertionError as e:
            record(name, False, f"assertion: {e}")
        except Exception as e:
            record(name, False, f"{type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n— End-to-end LLM scenarios —")
    try:
        await test_e2e_invariants()
    except Exception as e:
        record("E2E suite", False, f"{type(e).__name__}: {e}")
        traceback.print_exc()

    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 70)
    print(f"PASSED: {len(RESULTS) - len(failed)} / {len(RESULTS)}")
    if failed:
        print("FAILED:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        print("=" * 70)
        sys.exit(1)
    print("ALL INVARIANTS HOLD. Bot is BLINDADO ✅")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
