from fastapi import APIRouter, HTTPException, Body
from typing import List, Any, Dict
from models_b import Client, ClientActivity
from datetime import datetime, timezone
import uuid

router = APIRouter()
db = None

def set_db(database):
    global db
    db = database

async def log_client_activity(client_id: str, action: str, details: str):
    activity = ClientActivity(
        id=str(uuid.uuid4()),
        client_id=client_id,
        action=action,
        details=details
    )
    await db.client_activities.insert_one(activity.model_dump())

@router.get("/", response_model=List[Client])
async def get_clients(trash: bool = False):
    query = {"is_deleted": trash}
    clients = await db.clients.find(query, {"_id": 0}).to_list(1000)
    return clients

@router.post("/", response_model=Client)
async def create_client(client: Client):
    existing = await db.clients.find_one({"email": client.email, "is_deleted": False})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con este email")
    await db.clients.insert_one(client.model_dump())
    await log_client_activity(client.id, "created", f"Cliente creado: {client.name}")
    return client

@router.put("/{id}", response_model=Client)
async def update_client(id: str, client: Client):
    result = await db.clients.update_one(
        {"id": id},
        {"$set": client.model_dump(exclude={"id"})}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await log_client_activity(id, "updated", "Información del cliente actualizada")
    return client

@router.delete("/{id}")
async def delete_client(id: str, permanent: bool = False):
    query = {"id": id}
    existing = await db.clients.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    if permanent:
        await db.clients.delete_one(query)
        return {"message": "Cliente eliminado permanentemente"}
    else:
        await db.clients.update_one(query, {
            "$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}
        })
        return {"message": "Cliente movido a papelera"}

@router.post("/{id}/restore")
async def restore_client(id: str):
    query = {"id": id}
    existing = await db.clients.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    await db.clients.update_one(query, {
        "$set": {"is_deleted": False, "deleted_at": None}
    })
    return {"message": "Cliente restaurado"}

@router.get("/{id}/history")
async def get_client_history(id: str) -> Dict[str, Any]:
    client = await db.clients.find_one({"id": id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    quotes = await db.quotes.find({"client_id": id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    activities = await db.client_activities.find({"client_id": id}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return {"client": client, "quotes": quotes, "activities": activities}
