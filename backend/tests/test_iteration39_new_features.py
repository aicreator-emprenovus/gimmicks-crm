"""
Iteration 39 - 6 new features regression tests
==============================================
F1: POST /api/clients/{id}/promote duplicate detection (409, 404, 400, happy path)
F2: GET /api/leads exposes codigos_producto field
F3: GET /api/leads exposes quote_number field
F4: Atomic consecutive QUOTE numbering via counters collection
F5: send_message persists attended_by_name/email and GET returns them; bot msgs do NOT
F6: Backend ACL unchanged for /settings (frontend-only). Smoke check: route guard untouched.

Run:
  pytest /app/backend/tests/test_iteration39_new_features.py -v
"""

import os
import re
import uuid
import asyncio
from datetime import datetime, timezone

import pytest
import requests

from motor.motor_asyncio import AsyncIOMotorClient


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to inside-container backend
    BASE_URL = "http://localhost:8001"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "gimmicks_crm")

ADMIN_EMAIL = "admin@gimmicks.com"
ADMIN_PASSWORD = "admin123456"


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ============================================================ FEATURE 1
class TestFeature1PromoteDuplicateDetection:
    """POST /api/clients/{id}/promote duplicate detection."""

    test_emails = []
    test_ids = []

    @classmethod
    def teardown_class(cls):
        async def _cleanup():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            if cls.test_ids:
                await db.clients.delete_many({"id": {"$in": cls.test_ids}})
                await db.client_activities.delete_many({"client_id": {"$in": cls.test_ids}})
        try:
            asyncio.get_event_loop().run_until_complete(_cleanup())
        except Exception:
            pass

    def _insert_client(self, db, **overrides):
        """Insert a client doc directly via Mongo to bypass API duplicate guard."""
        doc = {
            "id": str(uuid.uuid4()),
            "name": overrides.get("name", "TEST Cliente"),
            "email": overrides.get("email", f"TEST_{uuid.uuid4().hex[:8]}@example.com"),
            "phone": overrides.get("phone", f"+57{uuid.uuid4().int % 10**10:010d}"),
            "source": overrides.get("source", "manual"),
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc),
        }
        doc.update({k: v for k, v in overrides.items() if k not in doc})
        run(db.clients.insert_one(doc))
        self.test_ids.append(doc["id"])
        return doc

    def test_promote_returns_409_when_duplicate_email(self, session, db):
        email = f"TEST_dup_email_{uuid.uuid4().hex[:6]}@example.com"
        # 1) existing non-whatsapp client with email
        self._insert_client(db, email=email, source="manual", name="TEST Existing Manual")
        # 2) interesado (source=whatsapp) with same email
        interesado = self._insert_client(
            db, email=email, source="whatsapp", phone=f"+57{uuid.uuid4().int % 10**10:010d}",
            name="TEST Interesado Dup Email",
        )
        r = session.post(f"{BASE_URL}/api/clients/{interesado['id']}/promote", timeout=20)
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text}"
        detail = r.json().get("detail", "")
        assert "No se puede promover" in detail
        assert "correo" in detail

    def test_promote_returns_409_when_duplicate_phone(self, session, db):
        phone = f"+57{uuid.uuid4().int % 10**10:010d}"
        # existing manual client with the phone
        self._insert_client(
            db, phone=phone, source="manual",
            email=f"TEST_phoneA_{uuid.uuid4().hex[:6]}@example.com",
            name="TEST Existing Phone",
        )
        # interesado WITHOUT email but same phone → must match by phone
        interesado = self._insert_client(
            db, phone=phone, source="whatsapp", email="",
            name="TEST Interesado Dup Phone",
        )
        r = session.post(f"{BASE_URL}/api/clients/{interesado['id']}/promote", timeout=20)
        assert r.status_code == 409, f"expected 409, got {r.status_code} {r.text}"
        assert "teléfono" in r.json().get("detail", "") or "telefono" in r.json().get("detail", "")

    def test_promote_happy_path_unique_interesado(self, session, db):
        interesado = self._insert_client(
            db, source="whatsapp",
            email=f"TEST_unique_{uuid.uuid4().hex[:6]}@example.com",
            phone=f"+57{uuid.uuid4().int % 10**10:010d}",
            name="TEST Interesado Unique",
        )
        r = session.post(f"{BASE_URL}/api/clients/{interesado['id']}/promote", timeout=20)
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text}"
        # verify source was flipped to manual
        async def _check():
            doc = await db.clients.find_one({"id": interesado["id"]}, {"_id": 0})
            return doc
        doc = run(_check())
        assert doc is not None
        assert doc["source"] == "manual"

    def test_promote_returns_404_when_missing(self, session):
        r = session.post(f"{BASE_URL}/api/clients/{uuid.uuid4()}/promote", timeout=20)
        assert r.status_code == 404
        assert "no encontrado" in r.json().get("detail", "").lower()

    def test_promote_returns_400_when_source_not_whatsapp(self, session, db):
        manual_client = self._insert_client(
            db, source="manual",
            email=f"TEST_400_{uuid.uuid4().hex[:6]}@example.com",
            name="TEST Manual Already Client",
        )
        r = session.post(f"{BASE_URL}/api/clients/{manual_client['id']}/promote", timeout=20)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"


# ============================================================ FEATURE 2 + 3
class TestFeature2_3LeadFields:
    """GET /api/leads must expose codigos_producto and quote_number."""

    lead_ids = []

    @classmethod
    def teardown_class(cls):
        async def _cleanup():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            if cls.lead_ids:
                await db.leads.delete_many({"id": {"$in": cls.lead_ids}})
        try:
            asyncio.get_event_loop().run_until_complete(_cleanup())
        except Exception:
            pass

    def test_leads_response_includes_new_fields(self, session, db):
        # Seed a lead with both fields set
        lead_id = str(uuid.uuid4())
        seed_lead = {
            "id": lead_id,
            "phone_number": f"+57300{uuid.uuid4().int % 10**7:07d}",
            "name": "TEST Lead F2F3",
            "source": "whatsapp",
            "status": "new",
            "funnel_stage": "nuevo",
            "classification": "interesado",
            "notes": "",
            "codigos_producto": "GIM-001, GIM-042",
            "quote_number": "99991",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        run(db.leads.insert_one(seed_lead))
        self.lead_ids.append(lead_id)

        r = session.get(f"{BASE_URL}/api/leads?limit=50", timeout=20)
        assert r.status_code == 200, r.text
        leads = r.json()
        target = next((l for l in leads if l["id"] == lead_id), None)
        assert target is not None, "Seeded lead not found in /api/leads response"

        # FEATURE 2
        assert "codigos_producto" in target, "Missing codigos_producto field in lead response"
        assert target["codigos_producto"] == "GIM-001, GIM-042"
        # FEATURE 3
        assert "quote_number" in target, "Missing quote_number field in lead response"
        assert target["quote_number"] == "99991"

    def test_lead_detail_includes_new_fields(self, session, db):
        # use the lead seeded above
        assert self.lead_ids, "no seeded lead"
        lid = self.lead_ids[0]
        r = session.get(f"{BASE_URL}/api/leads/{lid}", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body.get("codigos_producto") == "GIM-001, GIM-042"
        assert body.get("quote_number") == "99991"


# ============================================================ FEATURE 4
class TestFeature4AtomicQuoteCounter:
    """POST /api/quotes-v2/ with doc_type=QUOTE must use atomic counter and be consecutive."""

    created_quote_ids = []

    @classmethod
    def teardown_class(cls):
        async def _cleanup():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            if cls.created_quote_ids:
                await db.quotes_v2.delete_many({"id": {"$in": cls.created_quote_ids}})
                await db.document_activities.delete_many({"document_id": {"$in": cls.created_quote_ids}})
        try:
            asyncio.get_event_loop().run_until_complete(_cleanup())
        except Exception:
            pass

    def _quote_payload(self, doc_type="QUOTE"):
        return {
            "id": str(uuid.uuid4()),
            "doc_type": doc_type,
            "quote_number": "",
            "client_id": f"TEST_client_{uuid.uuid4().hex[:6]}",
            "client_name": "TEST Quote Client",
            "client_contact": "TEST Contact",
            "client_email": f"TEST_q_{uuid.uuid4().hex[:6]}@example.com",
            "factura": "",
            "items": [
                {
                    "item_id": str(uuid.uuid4()),
                    "product_id": "P1",
                    "code": "GIM-001",
                    "name": "Test Item",
                    "description": "",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "total_price": 100.0,
                    "image_url": "",
                    "categories": [],
                    "selected_characteristics": [],
                    "discount_amount": 0.0,
                    "discount_type": "$",
                    "additional_amount": 0.0,
                    "additional_type": "$",
                    "otros": "",
                }
            ],
            "subtotal": 100.0,
            "tax": 0.0,
            "total": 100.0,
            "status": "draft",
            "payment_terms": "50/50",
            "validity": "8 días",
            "delivery_time": "10 días",
            "is_deleted": False,
            "created_by_id": "",
            "created_by_name": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_two_quotes_have_consecutive_numbers(self, session):
        r1 = session.post(f"{BASE_URL}/api/quotes-v2/", json=self._quote_payload("QUOTE"), timeout=30)
        assert r1.status_code == 200, f"first quote failed: {r1.status_code} {r1.text}"
        q1 = r1.json()
        self.created_quote_ids.append(q1["id"])
        assert q1.get("quote_number"), "first quote_number empty"

        r2 = session.post(f"{BASE_URL}/api/quotes-v2/", json=self._quote_payload("QUOTE"), timeout=30)
        assert r2.status_code == 200, f"second quote failed: {r2.status_code} {r2.text}"
        q2 = r2.json()
        self.created_quote_ids.append(q2["id"])
        assert q2.get("quote_number"), "second quote_number empty"

        n1 = int(re.sub(r"\D+", "", str(q1["quote_number"])) or "0")
        n2 = int(re.sub(r"\D+", "", str(q2["quote_number"])) or "0")
        assert n2 == n1 + 1, f"expected consecutive numbers, got {n1} and {n2}"

    def test_counters_collection_has_quote_number_doc(self, db):
        async def _check():
            return await db.counters.find_one({"_id": "quote_number"})
        doc = run(_check())
        assert doc is not None, "counters._id=quote_number not seeded after creating quotes"
        assert isinstance(doc.get("seq"), int)
        # Seeded value should be >= 4698 (the safety floor)
        assert doc["seq"] >= 4698

    def test_po_counter_unchanged(self, session, db):
        # Capture before po seq if present
        async def _po_seq():
            return await db.counters.find_one({"_id": "po_number"})

        before = run(_po_seq())
        before_seq = before["seq"] if before else None

        r = session.post(f"{BASE_URL}/api/quotes-v2/", json=self._quote_payload("PO"), timeout=30)
        assert r.status_code == 200, r.text
        po = r.json()
        self.created_quote_ids.append(po["id"])
        assert po.get("quote_number"), "PO quote_number empty"

        after = run(_po_seq())
        assert after is not None
        # PO counter must have advanced by 1 or initialised to 4712
        if before_seq is not None:
            assert after["seq"] == before_seq + 1, f"PO counter not consecutive ({before_seq} → {after['seq']})"
        else:
            assert after["seq"] == 4712


# ============================================================ FEATURE 5
class TestFeature5AttendedByAttribution:
    """send_message persists attended_by_name/email; GET returns them."""

    conv_ids = []
    msg_ids = []

    @classmethod
    def teardown_class(cls):
        async def _cleanup():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            if cls.conv_ids:
                await db.conversations.delete_many({"id": {"$in": cls.conv_ids}})
                await db.messages.delete_many({"conversation_id": {"$in": cls.conv_ids}})
        try:
            asyncio.get_event_loop().run_until_complete(_cleanup())
        except Exception:
            pass

    def test_agent_message_has_attended_by(self, session, db):
        conv_id = str(uuid.uuid4())
        phone = f"+57300{uuid.uuid4().int % 10**7:07d}"
        run(db.conversations.insert_one({
            "id": conv_id,
            "phone_number": phone,
            "contact_name": "TEST Conv F5",
            "status": "active",
            "unread_count": 0,
            "created_at": datetime.now(timezone.utc),
        }))
        self.conv_ids.append(conv_id)

        # Also seed a bot-sent message (sender=business but no attended_by_*)
        bot_msg_id = str(uuid.uuid4())
        run(db.messages.insert_one({
            "id": bot_msg_id,
            "conversation_id": conv_id,
            "phone_number": phone,
            "sender": "business",
            "message_type": "text",
            "content": {"text": "Hola desde el bot"},
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # No attended_by_* fields → represents bot-generated message.
        }))

        # Send agent message via HTTP. WhatsApp send will fail (no real number),
        # which returns 502, BUT the message doc is inserted BEFORE the 502
        # is raised, so attended_by fields should still be persisted.
        payload = {"conversation_id": conv_id, "content": "TEST agent message F5", "message_type": "text"}
        r = session.post(f"{BASE_URL}/api/conversations/{conv_id}/messages", json=payload, timeout=30)
        assert r.status_code in (200, 502), f"unexpected status {r.status_code}: {r.text}"

        # Fetch messages
        gr = session.get(f"{BASE_URL}/api/conversations/{conv_id}/messages", timeout=20)
        assert gr.status_code == 200
        msgs = gr.json()
        assert len(msgs) >= 2, f"expected ≥2 messages, got {len(msgs)}"

        # Bot message → no attended_by
        bot = next((m for m in msgs if m["id"] == bot_msg_id), None)
        assert bot is not None
        assert bot.get("attended_by_name") in (None, "")
        assert bot.get("attended_by_email") in (None, "")

        # Agent message → has attended_by = admin@gimmicks.com
        agent = next(
            (m for m in msgs
             if m["id"] != bot_msg_id
             and isinstance(m.get("content"), dict)
             and "TEST agent message F5" in (m["content"].get("text", ""))),
            None,
        )
        assert agent is not None, "agent message not found in GET response"
        assert agent.get("attended_by_email") == ADMIN_EMAIL, (
            f"attended_by_email mismatch: {agent.get('attended_by_email')}"
        )
        assert agent.get("attended_by_name"), "attended_by_name empty for agent message"


# ============================================================ FEATURE 6 (smoke)
class TestFeature6BackendAclUnchanged:
    """Backend has NO /settings ACL changes. Smoke: /api/users still works for admin."""

    def test_admin_can_still_list_users(self, session):
        r = session.get(f"{BASE_URL}/api/users", timeout=20)
        # Should be 200 or at least not 403 for admin
        assert r.status_code in (200, 404), f"admin unexpectedly blocked: {r.status_code} {r.text}"
