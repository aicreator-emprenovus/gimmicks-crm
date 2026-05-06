"""
Cleanup script: remove all data tied to a retired WhatsApp Phone Number ID.

Use case: an old WhatsApp Business number was disconnected from the CRM and
its data must be wiped completely from MongoDB to avoid the bot or staff
seeing stale conversations.

Usage (dry run first):
    cd /app/backend && python -m scripts.remove_retired_phone_id

To actually delete, set EXECUTE=1:
    cd /app/backend && EXECUTE=1 python -m scripts.remove_retired_phone_id
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# The Phone Number ID to remove completely
RETIRED_PHONE_NUMBER_ID = "994356967089829"


async def main():
    load_dotenv()
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    execute = os.environ.get("EXECUTE") == "1"

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("=" * 70)
    print(f"DB: {db_name} @ {mongo_url[:30]}...")
    print(f"Retired phone_number_id: {RETIRED_PHONE_NUMBER_ID}")
    print(f"Mode: {'EXECUTE (will delete)' if execute else 'DRY RUN (no changes)'}")
    print("=" * 70)

    # 1) Find all conversations linked to this Phone Number ID
    convs = await db.conversations.find(
        {"wa_phone_number_id": RETIRED_PHONE_NUMBER_ID},
        {"_id": 0, "id": 1, "phone_number": 1, "contact_name": 1},
    ).to_list(None)

    print(f"\n[1] conversations matching wa_phone_number_id: {len(convs)}")
    for c in convs[:10]:
        print(f"    - id={c['id']}  phone={c.get('phone_number')}  name={c.get('contact_name')}")
    if len(convs) > 10:
        print(f"    ... and {len(convs) - 10} more")

    conv_ids = [c["id"] for c in convs]
    affected_phones = list({c["phone_number"] for c in convs if c.get("phone_number")})

    # 2) Messages tied to those conversations
    msg_count = await db.messages.count_documents({"conversation_id": {"$in": conv_ids}}) if conv_ids else 0
    print(f"\n[2] messages in those conversations: {msg_count}")

    # 3) Conversation states for those phones
    state_count = await db.conversation_states.count_documents(
        {"phone_number": {"$in": affected_phones}}
    ) if affected_phones else 0
    print(f"\n[3] conversation_states for those phones: {state_count}")

    # 4) Leads from those phones (only if they came from this number)
    lead_count = await db.leads.count_documents(
        {"phone_number": {"$in": affected_phones}}
    ) if affected_phones else 0
    print(f"\n[4] leads with those phones: {lead_count}")
    print("    (Only delete a lead if it has NO conversation tied to a non-retired number)")

    # 5) Quotes generated through this Phone Number ID
    quote_count = await db.quotes_v2.count_documents(
        {"phone_number": {"$in": affected_phones}}
    ) if affected_phones else 0
    print(f"\n[5] quotes_v2 from those phones: {quote_count}")
    print("    (NOT deleted — quotes are commercial records, kept for history)")

    if not execute:
        print("\n=== DRY RUN — no data was modified. Re-run with EXECUTE=1 to apply. ===")
        return

    print("\n>>> EXECUTING deletes...")

    if conv_ids:
        r = await db.messages.delete_many({"conversation_id": {"$in": conv_ids}})
        print(f"    Deleted messages: {r.deleted_count}")

        r = await db.conversations.delete_many({"id": {"$in": conv_ids}})
        print(f"    Deleted conversations: {r.deleted_count}")

    if affected_phones:
        # Only delete state docs that are exclusively linked to retired conversations
        r = await db.conversation_states.delete_many({"phone_number": {"$in": affected_phones}})
        print(f"    Deleted conversation_states: {r.deleted_count}")

    # We do NOT delete leads or quotes automatically. Print a list so the
    # admin can decide manually whether to soft-delete them from the UI.
    if affected_phones:
        print("\n[INFO] The following phones had data tied to the retired number.")
        print("       Review them in CRM (Leads / Quotes) and decide manually if they")
        print("       should be archived:")
        for p in affected_phones:
            print(f"         - {p}")

    print("\n>>> Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())
