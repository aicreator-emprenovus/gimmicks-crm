"""Emergent Object Storage wrapper for product images.

- Init once at app startup via init_storage()
- put/get helpers are sync (use asyncio.to_thread from async code to avoid blocking)
- We keep DB as the source of truth: each image still has a doc in `product_images`
  with {id, storage_path, content_type, size, is_deleted, created_at}.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "gimmicks-crm"

_storage_key: str | None = None


def _emergent_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY is not set")
    return key


def init_storage() -> str:
    """Call ONCE at startup. Returns a session-scoped, reusable storage_key."""
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(
        f"{STORAGE_URL}/init",
        json={"emergent_key": _emergent_key()},
        timeout=30,
    )
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    logger.info("Emergent Object Storage initialized")
    return _storage_key


def _ensure_key() -> str:
    if _storage_key:
        return _storage_key
    return init_storage()


def build_path(image_id: str, ext: str = "jpg") -> str:
    """Canonical path for a product image. No leading slash."""
    return f"{APP_NAME}/product-images/{image_id}.{ext}"


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file. Returns {"path": "...", "size": int, ...}.
    Raises on HTTP errors.
    """
    key = _ensure_key()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    if resp.status_code == 409:
        # Object already exists — treat as success (idempotent re-upload)
        return {"path": path, "size": len(data), "already_exists": True}
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    """Download file. Returns (content_bytes, content_type). Raises on HTTP errors."""
    key = _ensure_key()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
