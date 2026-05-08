"""Verifies the frontend AttachmentRenderer can fetch a stored attachment with
JWT auth (using axios responseType='blob'). End-to-end: real upload → real GET
with a real JWT, just like the browser does."""
import asyncio
import os
import sys
import time
import uuid

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    import requests, base64

    api = os.environ["REACT_APP_BACKEND_URL"]
    # Login
    r = requests.post(f"{api}/api/auth/login",
                      json={"email": "admin@gimmicks.com", "password": "admin123456"},
                      timeout=10)
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"login failed: {r.text}"
    headers = {"Authorization": f"Bearer {token}"}

    # Get any conversation
    convs = requests.get(f"{api}/api/conversations?limit=1", headers=headers).json()
    assert convs, "no conversations available"
    conv_id = convs[0]["id"]

    # Build a tiny PNG (1x1 pixel)
    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    files = {"file": ("preview-test.png", tiny_png, "image/png")}
    data = {"caption": "test preview"}

    # Upload as attachment
    up = requests.post(
        f"{api}/api/conversations/{conv_id}/messages/attachment",
        headers=headers, files=files, data=data, timeout=60
    )
    print(f"upload status={up.status_code}")
    if up.status_code >= 400:
        print(f"body={up.text[:300]}")
        return
    upj = up.json()
    msg_id = upj["id"]
    storage_path = upj["content"]["storage_path"]
    print(f"storage_path={storage_path}")

    # Extract attachment id (uuid before extension)
    import re as _re
    m = _re.search(r"inbox-attachments/([^./]+)", storage_path)
    assert m, f"could not parse {storage_path}"
    attachment_id = m.group(1)

    # 1) Without auth → 401 (browser <img src=...> would fail)
    no_auth = requests.get(f"{api}/api/conversations/attachments/{attachment_id}", timeout=10)
    print(f"GET without auth: {no_auth.status_code}")
    assert no_auth.status_code == 401, f"expected 401, got {no_auth.status_code}"

    # 2) WITH auth (axios style) → 200 + image bytes
    with_auth = requests.get(
        f"{api}/api/conversations/attachments/{attachment_id}",
        headers=headers, timeout=10
    )
    print(f"GET with auth: {with_auth.status_code} | bytes={len(with_auth.content)} | ct={with_auth.headers.get('Content-Type')}")
    assert with_auth.status_code == 200
    assert with_auth.content == tiny_png, "served bytes must match uploaded bytes"
    assert with_auth.headers.get("Content-Type", "").startswith("image/png")
    print("[OK] AttachmentRenderer flow works: image fetched with JWT bearer header.")

    # Cleanup
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    await db.messages.delete_one({"id": msg_id})
    print(f"cleaned up message {msg_id}")
    client.close()
    print("\n=== PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
