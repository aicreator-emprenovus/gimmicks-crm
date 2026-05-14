from fastapi import APIRouter, HTTPException, Body, Header, Request
from typing import List, Any, Dict
from models_b import Client, ClientActivity
from datetime import datetime, timezone
import re
import uuid

router = APIRouter()
db = None
get_user_from_token = None

def set_db(database):
    global db
    db = database

def set_auth_helper(fn):
    global get_user_from_token
    get_user_from_token = fn

_log_activity = None
def set_logger(fn):
    global _log_activity
    _log_activity = fn


async def log_client_activity(client_id: str, action: str, details: str):
    activity = ClientActivity(
        id=str(uuid.uuid4()),
        client_id=client_id,
        action=action,
        details=details
    )
    await db.client_activities.insert_one(activity.model_dump())

@router.get("/", response_model=List[Client])
async def get_clients(trash: bool = False, source: str = None):
    query = {"is_deleted": trash}
    if source:
        query["source"] = source
    clients = await db.clients.find(query, {"_id": 0}).to_list(1000)
    return clients

@router.post("/", response_model=Client)
async def create_client(client: Client, request: Request, authorization: str = Header(None)):
    existing = await db.clients.find_one({"email": client.email, "is_deleted": False})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con este email")
    await db.clients.insert_one(client.model_dump())
    await log_client_activity(client.id, "created", f"Cliente creado: {client.name}")
    if _log_activity and get_user_from_token:
        user = await get_user_from_token(authorization, request)
        if user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_create", f"Cliente creado: {client.name} ({client.email})")
    return client

@router.put("/{id}", response_model=Client)
async def update_client(id: str, client: Client, request: Request, authorization: str = Header(None)):
    result = await db.clients.update_one(
        {"id": id},
        {"$set": client.model_dump(exclude={"id"})}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await log_client_activity(id, "updated", "Información del cliente actualizada")
    if _log_activity and get_user_from_token:
        user = await get_user_from_token(authorization, request)
        if user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_update", f"Cliente actualizado: {client.name}")
    return client

@router.delete("/{id}")
async def delete_client(id: str, request: Request, permanent: bool = False, authorization: str = Header(None)):
    user = None
    if get_user_from_token:
        user = await get_user_from_token(authorization, request)
        if user.get("role") not in ("admin", "desarrollador"):
            raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar")
    query = {"id": id}
    existing = await db.clients.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    client_name = existing.get("name", id)

    if permanent:
        await db.clients.delete_one(query)
        if _log_activity and user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_delete", f"Cliente eliminado: {client_name}")
        return {"message": "Cliente eliminado permanentemente"}
    else:
        await db.clients.update_one(query, {
            "$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}
        })
        if _log_activity and user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_trash", f"Cliente a papelera: {client_name}")
        return {"message": "Cliente movido a papelera"}

@router.post("/{id}/restore")
async def restore_client(id: str, request: Request, authorization: str = Header(None)):
    query = {"id": id}
    existing = await db.clients.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await db.clients.update_one(query, {
        "$set": {"is_deleted": False, "deleted_at": None}
    })
    if _log_activity and get_user_from_token:
        user = await get_user_from_token(authorization, request)
        if user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_restore", f"Cliente restaurado: {existing.get('name', id)}")
    return {"message": "Cliente restaurado"}

@router.post("/{id}/promote")
async def promote_to_client(id: str, request: Request, authorization: str = Header(None)):
    existing = await db.clients.find_one({"id": id})
    if not existing:
        raise HTTPException(status_code=404, detail="Interesado no encontrado")
    if existing.get("source") != "whatsapp":
        raise HTTPException(status_code=400, detail="Este registro ya es un cliente")

    # Duplicate-detection: refuse promotion if another non-WhatsApp record already
    # exists with the same email or phone. This prevents accidental duplicates in
    # the Clientes section when an interesado matches an existing cliente.
    duplicate_query_or = []
    email = (existing.get("email") or "").strip().lower()
    phone = (existing.get("phone") or "").strip()
    if email:
        duplicate_query_or.append({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
    if phone:
        duplicate_query_or.append({"phone": phone})

    if duplicate_query_or:
        duplicate = await db.clients.find_one({
            "id": {"$ne": id},
            "source": {"$ne": "whatsapp"},
            "is_deleted": False,
            "$or": duplicate_query_or,
        }, {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1})
        if duplicate:
            matched_field = "correo" if email and duplicate.get("email", "").lower() == email else "teléfono"
            raise HTTPException(
                status_code=409,
                detail=(
                    f"No se puede promover: ya existe un cliente registrado con el mismo {matched_field} "
                    f"({duplicate.get('name') or duplicate.get('email') or duplicate.get('phone')}). "
                    f"Revisa la sección Clientes antes de continuar."
                ),
            )

    await db.clients.update_one(
        {"id": id},
        {"$set": {"source": "manual"}}
    )
    await log_client_activity(id, "promoted", "Promovido de Interesado a Cliente")
    if _log_activity and get_user_from_token:
        user = await get_user_from_token(authorization, request)
        if user:
            await _log_activity(user.get("email", ""), user.get("name", ""), "client_promote", f"Interesado promovido a cliente: {existing.get('name', id)}")
    return {"message": "Interesado promovido a Cliente exitosamente"}

@router.get("/{id}/history")
async def get_client_history(id: str) -> Dict[str, Any]:
    client = await db.clients.find_one({"id": id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    quotes = await db.quotes.find({"client_id": id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    activities = await db.client_activities.find({"client_id": id}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return {"client": client, "quotes": quotes, "activities": activities}
