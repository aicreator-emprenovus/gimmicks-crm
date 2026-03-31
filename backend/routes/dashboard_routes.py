from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone, timedelta
import jwt
import os

router = APIRouter()
db = None
JWT_SECRET = None

def set_db(database):
    global db
    db = database

def set_jwt_secret(secret):
    global JWT_SECRET
    JWT_SECRET = secret

async def get_user_from_token(authorization: str = None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if user:
                return {"id": user.get("id"), "name": user.get("name", ""), "email": user.get("email", "")}
    except Exception:
        pass
    return None

@router.get("/stats")
async def get_dashboard_stats(authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_products = await db.products.count_documents({})
    total_clients = await db.clients.count_documents({"is_deleted": False})
    total_quotes = await db.quotes_v2.count_documents({"is_deleted": False, "doc_type": "QUOTE"})
    total_pos = await db.quotes_v2.count_documents({"is_deleted": False, "doc_type": "PO"})
    total_leads = await db.leads.count_documents({})
    active_conversations = await db.conversations.count_documents({"status": "active"})
    pipeline_quotes = [
        {"$match": {"is_deleted": False, "doc_type": "QUOTE"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]
    quotes_total = 0
    async for result in db.quotes_v2.aggregate(pipeline_quotes):
        quotes_total = result.get("total", 0)
    pipeline_pos = [
        {"$match": {"is_deleted": False, "doc_type": "PO"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]
    pos_total = 0
    async for result in db.quotes_v2.aggregate(pipeline_pos):
        pos_total = result.get("total", 0)
    return {
        "total_products": total_products,
        "total_clients": total_clients,
        "total_quotes": total_quotes,
        "total_pos": total_pos,
        "total_leads": total_leads,
        "active_conversations": active_conversations,
        "quotes_total_value": quotes_total,
        "pos_total_value": pos_total
    }

@router.get("/activity-chart")
async def get_activity_chart(days: int = 30, authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    chart_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        quotes_count = await db.quotes_v2.count_documents({
            "is_deleted": False,
            "created_at": {"$gte": day_start, "$lt": day_end},
            "$or": [{"doc_type": "QUOTE"}, {"doc_type": {"$exists": False}}]
        })
        pos_count = await db.quotes_v2.count_documents({
            "doc_type": "PO", "is_deleted": False,
            "created_at": {"$gte": day_start, "$lt": day_end}
        })
        leads_count = await db.leads.count_documents({
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        chart_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "cotizaciones": quotes_count,
            "ordenes": pos_count,
            "leads": leads_count
        })
    return chart_data

@router.get("/top-products")
async def get_top_products(limit: int = 10, authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.code", "name": {"$first": "$items.name"}, "total_quantity": {"$sum": "$items.quantity"}, "total_value": {"$sum": "$items.total_price"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    results = []
    async for item in db.quotes_v2.aggregate(pipeline):
        results.append({"code": item["_id"], "name": item.get("name", ""), "total_quantity": item.get("total_quantity", 0), "total_value": item.get("total_value", 0), "count": item.get("count", 0)})
    return results

@router.get("/top-clients")
async def get_top_clients(limit: int = 10, authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": "$client_id", "client_name": {"$first": "$client_name"}, "total_quotes": {"$sum": 1}, "total_value": {"$sum": "$total"}}},
        {"$sort": {"total_value": -1}},
        {"$limit": limit}
    ]
    results = []
    async for item in db.quotes_v2.aggregate(pipeline):
        results.append({"client_id": item["_id"], "client_name": item.get("client_name", ""), "total_quotes": item.get("total_quotes", 0), "total_value": item.get("total_value", 0)})
    return results



@router.get("/orders-by-client")
async def get_orders_by_client(month: int = None, year: int = None, authorization: str = Header(None)):
    """Purchase orders summary grouped by client for a given month.
    Admin only. Returns clients with their order count and total amount."""
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    # Check admin role
    full_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "role": 1})
    if not full_user or full_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")

    now = datetime.now(timezone.utc)
    m = month or now.month
    y = year or now.year

    start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, m + 1, 1, tzinfo=timezone.utc)

    pipeline = [
        {"$match": {
            "is_deleted": {"$ne": True},
            "created_at": {"$gte": start, "$lt": end}
        }},
        {"$group": {
            "_id": "$client_name",
            "total_orders": {"$sum": 1},
            "total_amount": {"$sum": "$total"},
            "phone": {"$first": "$phone_number"},
            "last_order": {"$max": "$created_at"},
            "items_count": {"$sum": {"$size": {"$ifNull": ["$items", []]}}}
        }},
        {"$sort": {"total_amount": -1}}
    ]

    clients = []
    grand_total = 0
    grand_orders = 0
    async for row in db.quotes_v2.aggregate(pipeline):
        amount = row.get("total_amount", 0) or 0
        orders = row.get("total_orders", 0)
        clients.append({
            "client_name": row["_id"] or "Sin nombre",
            "total_orders": orders,
            "total_amount": amount,
            "phone": row.get("phone", ""),
            "last_order": row.get("last_order").isoformat() if row.get("last_order") else None,
            "items_count": row.get("items_count", 0)
        })
        grand_total += amount
        grand_orders += orders

    return {
        "month": m,
        "year": y,
        "clients": clients,
        "grand_total": grand_total,
        "grand_orders": grand_orders
    }
