from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import json
from bson import ObjectId
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'default-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Gimmicks CRM - WhatsApp Business")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Lead/Funnel Models
class LeadCreate(BaseModel):
    phone_number: str
    name: Optional[str] = None
    source: Optional[str] = "whatsapp"
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    funnel_stage: Optional[str] = None
    notes: Optional[str] = None
    classification: Optional[str] = None

class LeadResponse(BaseModel):
    id: str
    phone_number: str
    name: Optional[str]
    source: str
    status: str
    funnel_stage: str
    classification: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]

# Message Models
class MessageCreate(BaseModel):
    conversation_id: str
    content: str
    message_type: str = "text"

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    phone_number: str
    sender: str
    message_type: str
    content: Dict[str, Any]
    status: str
    timestamp: datetime

# Conversation Models
class ConversationResponse(BaseModel):
    id: str
    phone_number: str
    contact_name: Optional[str]
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    status: str
    unread_count: int
    lead_id: Optional[str]
    created_at: datetime

# Product/Inventory Models
class ProductCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category_1: Optional[str] = None
    category_2: Optional[str] = None
    category_3: Optional[str] = None
    price: Optional[float] = None
    stock: int = 0
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    category_1: Optional[str]
    category_2: Optional[str]
    category_3: Optional[str]
    price: Optional[float]
    stock: int
    image_url: Optional[str]
    created_at: datetime

# Automation Rule Models
class AutomationRuleCreate(BaseModel):
    name: str
    trigger_type: str  # "keyword", "new_lead", "funnel_change", "no_response"
    trigger_value: Optional[str] = None
    action_type: str  # "send_message", "change_stage", "assign_agent", "recommend_product"
    action_value: str
    is_active: bool = True

class AutomationRuleResponse(BaseModel):
    id: str
    name: str
    trigger_type: str
    trigger_value: Optional[str]
    action_type: str
    action_value: str
    is_active: bool
    created_at: datetime

# Dashboard Metrics
class DashboardMetrics(BaseModel):
    total_leads: int
    leads_today: int
    conversion_rate: float
    avg_response_time: float
    leads_by_stage: Dict[str, int]
    leads_by_source: Dict[str, int]
    messages_today: int
    active_conversations: int

# ============== HELPER FUNCTIONS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def serialize_doc(doc: dict) -> dict:
    """Remove MongoDB _id and convert ObjectId fields"""
    if doc is None:
        return None
    result = {k: v for k, v in doc.items() if k != '_id'}
    return result

# ============== WHATSAPP API FUNCTIONS ==============

async def send_whatsapp_message(to_phone: str, message_text: str) -> str:
    """Send a text message via WhatsApp Business API"""
    import aiohttp
    
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    
    if not phone_number_id or not access_token:
        raise Exception("WhatsApp credentials not configured")
    
    # Remove any non-numeric characters except +
    clean_phone = ''.join(c for c in to_phone if c.isdigit())
    
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            result = await response.json()
            
            if response.status != 200:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"WhatsApp API error: {result}")
                raise Exception(f"WhatsApp API error: {error_msg}")
            
            message_id = result.get("messages", [{}])[0].get("id")
            return message_id

# ============== AUTH ROUTES ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user_data.email)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            role="admin",
            created_at=datetime.now(timezone.utc)
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    token = create_token(user["id"], user["email"])
    
    created_at = user.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user.get("role", "user"),
            created_at=created_at
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    created_at = current_user.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user.get("role", "asesor"),
        created_at=created_at
    )

# ============== USER MANAGEMENT ROUTES (Admin Only) ==============

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de administrador.")
    return current_user

class UserCreateByAdmin(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "asesor"

class UserUpdateByAdmin(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    
    result = []
    for user in users:
        created_at = user.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        result.append(UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user.get("role", "asesor"),
            created_at=created_at
        ))
    
    return result

@api_router.post("/users", response_model=UserResponse)
async def create_user_by_admin(user_data: UserCreateByAdmin, current_user: dict = Depends(require_admin)):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Validate role
    if user_data.role not in ["admin", "asesor"]:
        raise HTTPException(status_code=400, detail="Rol inválido. Debe ser 'admin' o 'asesor'")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "created_at": now.isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        created_at=now
    )

@api_router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(user_id: str, update_data: UserUpdateByAdmin, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_dict = {}
    if update_data.name:
        update_dict["name"] = update_data.name
    if update_data.role:
        if update_data.role not in ["admin", "asesor"]:
            raise HTTPException(status_code=400, detail="Rol inválido")
        update_dict["role"] = update_data.role
    if update_data.password:
        update_dict["password"] = hash_password(update_data.password)
    
    if update_dict:
        await db.users.update_one({"id": user_id}, {"$set": update_dict})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    
    created_at = updated_user.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        name=updated_user["name"],
        role=updated_user.get("role", "asesor"),
        created_at=created_at
    )

@api_router.delete("/users/{user_id}")
async def delete_user_by_admin(user_id: str, current_user: dict = Depends(require_admin)):
    # Prevent self-deletion
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {"message": "Usuario eliminado exitosamente"}

# ============== LEADS ROUTES ==============

# ============== LEADS ROUTES ==============

FUNNEL_STAGES = ["lead", "pedido", "produccion", "entregado", "perdido", "cierre"]
LEAD_CLASSIFICATIONS = ["frio", "tibio", "caliente"]

@api_router.post("/leads", response_model=LeadResponse)
async def create_lead(lead_data: LeadCreate, current_user: dict = Depends(get_current_user)):
    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    lead_doc = {
        "id": lead_id,
        "phone_number": lead_data.phone_number,
        "name": lead_data.name,
        "source": lead_data.source,
        "status": "active",
        "funnel_stage": "lead",
        "classification": "frio",
        "notes": lead_data.notes,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "last_message_at": None
    }
    
    await db.leads.insert_one(lead_doc)
    
    return LeadResponse(
        id=lead_id,
        phone_number=lead_data.phone_number,
        name=lead_data.name,
        source=lead_data.source,
        status="active",
        funnel_stage="lead",
        classification="frio",
        notes=lead_data.notes,
        created_at=now,
        updated_at=now,
        last_message_at=None
    )

@api_router.get("/leads", response_model=List[LeadResponse])
async def get_leads(
    stage: Optional[str] = None,
    classification: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if stage:
        query["funnel_stage"] = stage
    if classification:
        query["classification"] = classification
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone_number": {"$regex": search, "$options": "i"}}
        ]
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for lead in leads:
        created_at = lead.get("created_at")
        updated_at = lead.get("updated_at")
        last_message_at = lead.get("last_message_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        if isinstance(last_message_at, str):
            last_message_at = datetime.fromisoformat(last_message_at.replace('Z', '+00:00'))
        
        result.append(LeadResponse(
            id=lead["id"],
            phone_number=lead["phone_number"],
            name=lead.get("name"),
            source=lead.get("source", "whatsapp"),
            status=lead.get("status", "active"),
            funnel_stage=lead.get("funnel_stage", "lead"),
            classification=lead.get("classification", "frio"),
            notes=lead.get("notes"),
            created_at=created_at,
            updated_at=updated_at,
            last_message_at=last_message_at
        ))
    
    return result

@api_router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    created_at = lead.get("created_at")
    updated_at = lead.get("updated_at")
    last_message_at = lead.get("last_message_at")
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    if isinstance(last_message_at, str):
        last_message_at = datetime.fromisoformat(last_message_at.replace('Z', '+00:00'))
    
    return LeadResponse(
        id=lead["id"],
        phone_number=lead["phone_number"],
        name=lead.get("name"),
        source=lead.get("source", "whatsapp"),
        status=lead.get("status", "active"),
        funnel_stage=lead.get("funnel_stage", "lead"),
        classification=lead.get("classification", "frio"),
        notes=lead.get("notes"),
        created_at=created_at,
        updated_at=updated_at,
        last_message_at=last_message_at
    )

@api_router.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, update_data: LeadUpdate, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    
    created_at = updated_lead.get("created_at")
    updated_at = updated_lead.get("updated_at")
    last_message_at = updated_lead.get("last_message_at")
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    if isinstance(last_message_at, str):
        last_message_at = datetime.fromisoformat(last_message_at.replace('Z', '+00:00'))
    
    return LeadResponse(
        id=updated_lead["id"],
        phone_number=updated_lead["phone_number"],
        name=updated_lead.get("name"),
        source=updated_lead.get("source", "whatsapp"),
        status=updated_lead.get("status", "active"),
        funnel_stage=updated_lead.get("funnel_stage", "lead"),
        classification=updated_lead.get("classification", "frio"),
        notes=updated_lead.get("notes"),
        created_at=created_at,
        updated_at=updated_at,
        last_message_at=last_message_at
    )

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return {"message": "Lead eliminado exitosamente"}

# ============== CONVERSATIONS ROUTES ==============

@api_router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    
    conversations = await db.conversations.find(query, {"_id": 0}).sort("last_message_time", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for conv in conversations:
        created_at = conv.get("created_at")
        last_message_time = conv.get("last_message_time")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(last_message_time, str):
            last_message_time = datetime.fromisoformat(last_message_time.replace('Z', '+00:00'))
        
        result.append(ConversationResponse(
            id=conv["id"],
            phone_number=conv["phone_number"],
            contact_name=conv.get("contact_name"),
            last_message=conv.get("last_message"),
            last_message_time=last_message_time,
            status=conv.get("status", "active"),
            unread_count=conv.get("unread_count", 0),
            lead_id=conv.get("lead_id"),
            created_at=created_at
        ))
    
    return result

@api_router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    created_at = conv.get("created_at")
    last_message_time = conv.get("last_message_time")
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(last_message_time, str):
        last_message_time = datetime.fromisoformat(last_message_time.replace('Z', '+00:00'))
    
    return ConversationResponse(
        id=conv["id"],
        phone_number=conv["phone_number"],
        contact_name=conv.get("contact_name"),
        last_message=conv.get("last_message"),
        last_message_time=last_message_time,
        status=conv.get("status", "active"),
        unread_count=conv.get("unread_count", 0),
        lead_id=conv.get("lead_id"),
        created_at=created_at
    )

@api_router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("timestamp", 1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for msg in messages:
        timestamp = msg.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        result.append(MessageResponse(
            id=msg["id"],
            conversation_id=msg["conversation_id"],
            phone_number=msg["phone_number"],
            sender=msg["sender"],
            message_type=msg.get("message_type", "text"),
            content=msg.get("content", {}),
            status=msg.get("status", "sent"),
            timestamp=timestamp
        ))
    
    return result

@api_router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    # Get conversation
    conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Send message via WhatsApp API
    whatsapp_message_id = None
    send_status = "sent"
    
    try:
        whatsapp_message_id = await send_whatsapp_message(
            conv["phone_number"],
            message_data.content
        )
        send_status = "delivered"
        logger.info(f"WhatsApp message sent: {whatsapp_message_id}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        send_status = "failed"
    
    message_doc = {
        "id": message_id,
        "conversation_id": conversation_id,
        "phone_number": conv["phone_number"],
        "sender": "business",
        "message_type": message_data.message_type,
        "content": {"text": message_data.content},
        "status": send_status,
        "whatsapp_message_id": whatsapp_message_id,
        "timestamp": now.isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    # Update conversation
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {
            "last_message": message_data.content[:100],
            "last_message_time": now.isoformat()
        }}
    )
    
    return MessageResponse(
        id=message_id,
        conversation_id=conversation_id,
        phone_number=conv["phone_number"],
        sender="business",
        message_type=message_data.message_type,
        content={"text": message_data.content},
        status="sent",
        timestamp=now
    )

# ============== PRODUCTS/INVENTORY ROUTES ==============

@api_router.get("/products", response_model=List[ProductResponse])
async def get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"code": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if category:
        query["$or"] = query.get("$or", []) + [
            {"category_1": {"$regex": category, "$options": "i"}},
            {"category_2": {"$regex": category, "$options": "i"}},
            {"category_3": {"$regex": category, "$options": "i"}}
        ]
    
    products = await db.products.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for prod in products:
        created_at = prod.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        result.append(ProductResponse(
            id=prod["id"],
            code=prod["code"],
            name=prod["name"],
            description=prod.get("description"),
            category_1=prod.get("category_1"),
            category_2=prod.get("category_2"),
            category_3=prod.get("category_3"),
            price=prod.get("price"),
            stock=prod.get("stock", 0),
            image_url=prod.get("image_url"),
            created_at=created_at
        ))
    
    return result

@api_router.post("/products", response_model=ProductResponse)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    product_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    product_doc = {
        "id": product_id,
        "code": product_data.code,
        "name": product_data.name,
        "description": product_data.description,
        "category_1": product_data.category_1,
        "category_2": product_data.category_2,
        "category_3": product_data.category_3,
        "price": product_data.price,
        "stock": product_data.stock,
        "image_url": product_data.image_url,
        "created_at": now.isoformat()
    }
    
    await db.products.insert_one(product_doc)
    
    return ProductResponse(
        id=product_id,
        code=product_data.code,
        name=product_data.name,
        description=product_data.description,
        category_1=product_data.category_1,
        category_2=product_data.category_2,
        category_3=product_data.category_3,
        price=product_data.price,
        stock=product_data.stock,
        image_url=product_data.image_url,
        created_at=now
    )

@api_router.post("/products/upload")
async def upload_products_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    import openpyxl
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
    
    contents = await file.read()
    
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(contents))
        sheet = workbook.active
        
        # Get headers from first row
        headers = [cell.value for cell in sheet[1]]
        
        # Map common header names
        header_map = {
            'código producto': 'code',
            'codigo producto': 'code',
            'code': 'code',
            'nombre del producto': 'name',
            'nombre': 'name',
            'name': 'name',
            'descripción': 'description',
            'descripcion': 'description',
            'description': 'description',
            'cat. 1': 'category_1',
            'cat 1': 'category_1',
            'categoria 1': 'category_1',
            'cat. 2': 'category_2',
            'cat 2': 'category_2',
            'categoria 2': 'category_2',
            'cat. 3': 'category_3',
            'cat 3': 'category_3',
            'categoria 3': 'category_3',
            'precio': 'price',
            'price': 'price',
            'stock': 'stock',
            'foto': 'image_url',
            'image': 'image_url',
            'imagen': 'image_url'
        }
        
        # Normalize headers
        normalized_headers = []
        for h in headers:
            if h:
                h_lower = str(h).lower().strip()
                normalized_headers.append(header_map.get(h_lower, h_lower))
            else:
                normalized_headers.append(None)
        
        products_created = 0
        products_updated = 0
        now = datetime.now(timezone.utc)
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_data = dict(zip(normalized_headers, row))
            
            # Skip empty rows
            if not row_data.get('code') and not row_data.get('name'):
                continue
            
            code = str(row_data.get('code', '')).strip()
            if not code:
                continue
            
            # Check if product exists
            existing = await db.products.find_one({"code": code})
            
            product_doc = {
                "code": code,
                "name": str(row_data.get('name', '')).strip(),
                "description": str(row_data.get('description', '')).strip() if row_data.get('description') else None,
                "category_1": str(row_data.get('category_1', '')).strip() if row_data.get('category_1') else None,
                "category_2": str(row_data.get('category_2', '')).strip() if row_data.get('category_2') else None,
                "category_3": str(row_data.get('category_3', '')).strip() if row_data.get('category_3') else None,
                "image_url": str(row_data.get('image_url', '')).strip() if row_data.get('image_url') else None,
                "updated_at": now.isoformat()
            }
            
            # Handle price
            price = row_data.get('price')
            if price:
                try:
                    if isinstance(price, str):
                        price = float(price.replace('$', '').replace(',', '.').strip())
                    product_doc['price'] = float(price)
                except:
                    product_doc['price'] = None
            
            # Handle stock
            stock = row_data.get('stock')
            if stock:
                try:
                    product_doc['stock'] = int(stock)
                except:
                    product_doc['stock'] = 0
            
            if existing:
                await db.products.update_one({"code": code}, {"$set": product_doc})
                products_updated += 1
            else:
                product_doc["id"] = str(uuid.uuid4())
                product_doc["created_at"] = now.isoformat()
                product_doc["stock"] = product_doc.get("stock", 0)
                await db.products.insert_one(product_doc)
                products_created += 1
        
        return {
            "message": "Productos cargados exitosamente",
            "created": products_created,
            "updated": products_updated
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error procesando el archivo: {str(e)}")

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado exitosamente"}

# ============== AUTOMATION RULES ROUTES ==============

@api_router.get("/automation-rules", response_model=List[AutomationRuleResponse])
async def get_automation_rules(current_user: dict = Depends(get_current_user)):
    rules = await db.automation_rules.find({}, {"_id": 0}).to_list(100)
    
    result = []
    for rule in rules:
        created_at = rule.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        result.append(AutomationRuleResponse(
            id=rule["id"],
            name=rule["name"],
            trigger_type=rule["trigger_type"],
            trigger_value=rule.get("trigger_value"),
            action_type=rule["action_type"],
            action_value=rule["action_value"],
            is_active=rule.get("is_active", True),
            created_at=created_at
        ))
    
    return result

@api_router.post("/automation-rules", response_model=AutomationRuleResponse)
async def create_automation_rule(rule_data: AutomationRuleCreate, current_user: dict = Depends(get_current_user)):
    rule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    rule_doc = {
        "id": rule_id,
        "name": rule_data.name,
        "trigger_type": rule_data.trigger_type,
        "trigger_value": rule_data.trigger_value,
        "action_type": rule_data.action_type,
        "action_value": rule_data.action_value,
        "is_active": rule_data.is_active,
        "created_at": now.isoformat()
    }
    
    await db.automation_rules.insert_one(rule_doc)
    
    return AutomationRuleResponse(
        id=rule_id,
        name=rule_data.name,
        trigger_type=rule_data.trigger_type,
        trigger_value=rule_data.trigger_value,
        action_type=rule_data.action_type,
        action_value=rule_data.action_value,
        is_active=rule_data.is_active,
        created_at=now
    )

@api_router.patch("/automation-rules/{rule_id}")
async def update_automation_rule(rule_id: str, is_active: bool, current_user: dict = Depends(get_current_user)):
    result = await db.automation_rules.update_one(
        {"id": rule_id},
        {"$set": {"is_active": is_active}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return {"message": "Regla actualizada"}

@api_router.delete("/automation-rules/{rule_id}")
async def delete_automation_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.automation_rules.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return {"message": "Regla eliminada exitosamente"}

# ============== DASHBOARD ROUTES ==============

@api_router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(current_user: dict = Depends(get_current_user)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total leads
    total_leads = await db.leads.count_documents({})
    
    # Leads today
    leads_today = await db.leads.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    # Leads by stage
    pipeline_stage = [
        {"$group": {"_id": "$funnel_stage", "count": {"$sum": 1}}}
    ]
    stage_results = await db.leads.aggregate(pipeline_stage).to_list(100)
    leads_by_stage = {r["_id"]: r["count"] for r in stage_results if r["_id"]}
    
    # Leads by source
    pipeline_source = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    source_results = await db.leads.aggregate(pipeline_source).to_list(100)
    leads_by_source = {r["_id"]: r["count"] for r in source_results if r["_id"]}
    
    # Conversion rate (leads that reached 'cierre' stage)
    closed_leads = await db.leads.count_documents({"funnel_stage": "cierre"})
    conversion_rate = (closed_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Messages today
    messages_today = await db.messages.count_documents({
        "timestamp": {"$gte": today_start.isoformat()}
    })
    
    # Active conversations
    active_conversations = await db.conversations.count_documents({"status": "active"})
    
    return DashboardMetrics(
        total_leads=total_leads,
        leads_today=leads_today,
        conversion_rate=round(conversion_rate, 2),
        avg_response_time=5.2,  # Placeholder - would need message timestamp analysis
        leads_by_stage=leads_by_stage,
        leads_by_source=leads_by_source,
        messages_today=messages_today,
        active_conversations=active_conversations
    )

# ============== WHATSAPP WEBHOOK ==============

from fastapi.responses import PlainTextResponse, Response
from fastapi import Request

@api_router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    """Webhook verification for WhatsApp Business API"""
    # Get query parameters directly from request
    params = dict(request.query_params)
    
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")
    
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    
    logger.info(f"Webhook verification request: mode={hub_mode}, challenge={hub_challenge}, token_received={hub_verify_token}, token_expected={verify_token}")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info(f"Webhook verified successfully, returning challenge: {hub_challenge}")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning(f"Webhook verification failed: mode={hub_mode}, token_match={hub_verify_token == verify_token}")
    return Response(content="Verification failed", status_code=403, media_type="text/plain")

@api_router.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(request_data: dict):
    """Handle incoming WhatsApp messages"""
    logger.info(f"Received webhook: {json.dumps(request_data)}")
    
    if request_data.get("object") == "whatsapp_business_account":
        for entry in request_data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    await process_incoming_message(message, value.get("metadata", {}))
    
    return {"status": "ok"}

async def process_incoming_message(message: dict, metadata: dict):
    """Process an incoming WhatsApp message"""
    phone_number = message.get("from")
    message_id = message.get("id")
    timestamp = message.get("timestamp")
    message_type = message.get("type", "text")
    
    now = datetime.now(timezone.utc)
    
    # Extract content based on message type
    if message_type == "text":
        content = {"text": message.get("text", {}).get("body", "")}
    else:
        content = {"raw": message}
    
    # Find or create conversation
    conversation = await db.conversations.find_one({"phone_number": phone_number}, {"_id": 0})
    
    if not conversation:
        conv_id = str(uuid.uuid4())
        conversation = {
            "id": conv_id,
            "phone_number": phone_number,
            "contact_name": None,
            "last_message": content.get("text", ""),
            "last_message_time": now.isoformat(),
            "status": "active",
            "unread_count": 1,
            "lead_id": None,
            "created_at": now.isoformat()
        }
        await db.conversations.insert_one(conversation)
        
        # Also create a lead
        lead_id = str(uuid.uuid4())
        lead_doc = {
            "id": lead_id,
            "phone_number": phone_number,
            "name": None,
            "source": "whatsapp",
            "status": "active",
            "funnel_stage": "lead",
            "classification": "frio",
            "notes": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_message_at": now.isoformat()
        }
        await db.leads.insert_one(lead_doc)
        
        await db.conversations.update_one({"id": conv_id}, {"$set": {"lead_id": lead_id}})
    else:
        await db.conversations.update_one(
            {"id": conversation["id"]},
            {
                "$set": {
                    "last_message": content.get("text", "")[:100],
                    "last_message_time": now.isoformat()
                },
                "$inc": {"unread_count": 1}
            }
        )
        
        # Update lead last_message_at
        if conversation.get("lead_id"):
            await db.leads.update_one(
                {"id": conversation["lead_id"]},
                {"$set": {"last_message_at": now.isoformat(), "updated_at": now.isoformat()}}
            )
    
    # Store message
    msg_doc = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation["id"],
        "phone_number": phone_number,
        "sender": "user",
        "message_type": message_type,
        "content": content,
        "status": "received",
        "whatsapp_message_id": message_id,
        "timestamp": now.isoformat()
    }
    await db.messages.insert_one(msg_doc)
    
    logger.info(f"Message processed from {phone_number}")

# ============== AI ANALYSIS ROUTES ==============

@api_router.post("/ai/analyze-message")
async def analyze_message(
    message: str,
    conversation_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Analyze a message using AI to classify intent and suggest products"""
    try:
        from openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            # Return basic analysis if no API key
            return {
                "intent": "consulta",
                "lead_classification": "tibio",
                "suggested_products": [],
                "suggested_response": f"Gracias por tu mensaje. Un asesor te contactará pronto.",
                "analysis_notes": "Análisis básico - API key no configurada"
            }
        
        # Get products for context
        products = await db.products.find({}, {"_id": 0, "name": 1, "description": 1, "category_1": 1, "category_2": 1}).limit(50).to_list(50)
        products_context = "\n".join([f"- {p['name']}: {p.get('description', '')[:100]}" for p in products])
        
        system_message = f"""Eres un asistente de ventas de Gimmicks Marketing Services, una empresa de productos promocionales.
        
Tu tarea es analizar mensajes de clientes y:
1. Clasificar la intención del mensaje (consulta, cotización, queja, seguimiento, otro)
2. Determinar la clasificación del lead (frio, tibio, caliente)
3. Sugerir productos relevantes de nuestro catálogo si aplica
4. Generar una respuesta sugerida profesional

Productos disponibles:
{products_context}

Responde SIEMPRE en formato JSON con esta estructura:
{{
    "intent": "consulta|cotizacion|queja|seguimiento|otro",
    "lead_classification": "frio|tibio|caliente",
    "suggested_products": ["producto1", "producto2"],
    "suggested_response": "texto de respuesta sugerida",
    "analysis_notes": "notas sobre el análisis"
}}"""
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Analiza este mensaje del cliente: \"{message}\""}
            ],
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        # Parse response
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "intent": "otro",
                    "lead_classification": "frio",
                    "suggested_products": [],
                    "suggested_response": response_text,
                    "analysis_notes": "No se pudo parsear la respuesta JSON"
                }
        except json.JSONDecodeError:
            result = {
                "intent": "otro",
                "lead_classification": "frio",
                "suggested_products": [],
                "suggested_response": response_text,
                "analysis_notes": "No se pudo parsear la respuesta JSON"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        return {
            "intent": "consulta",
            "lead_classification": "tibio",
            "suggested_products": [],
            "suggested_response": "Gracias por tu mensaje. Un asesor te contactará pronto.",
            "analysis_notes": f"Error en análisis: {str(e)}"
        }

@api_router.post("/ai/recommend-products")
async def recommend_products(
    query: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Recommend products based on customer query using AI"""
    try:
        from openai import OpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return {"recommendations": [], "message": "API key no configurada"}
        
        # Get all products
        products = await db.products.find({}, {"_id": 0}).limit(100).to_list(100)
        products_json = json.dumps([{
            "code": p["code"],
            "name": p["name"],
            "description": p.get("description", ""),
            "category_1": p.get("category_1", ""),
            "category_2": p.get("category_2", ""),
            "price": p.get("price"),
            "stock": p.get("stock", 0)
        } for p in products], ensure_ascii=False)
        
        system_message = f"""Eres un asistente de recomendación de productos de Gimmicks Marketing Services.

Catálogo de productos disponibles:
{products_json}

Analiza la consulta del cliente y recomienda los productos más relevantes.
Responde en formato JSON:
{{
    "recommendations": [
        {{
            "code": "código del producto",
            "name": "nombre",
            "reason": "razón de la recomendación"
        }}
    ],
    "message": "mensaje para el cliente explicando las recomendaciones"
}}"""
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"El cliente necesita: {query}"}
            ],
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"recommendations": [], "message": response_text}
        except:
            result = {"recommendations": [], "message": response_text}
        
        return result
        
    except Exception as e:
        logger.error(f"Product recommendation error: {str(e)}")
        return {"recommendations": [], "message": f"Error: {str(e)}"}

# ============== SEED DATA FOR DEMO ==============

@api_router.post("/seed-demo-data")
async def seed_demo_data(current_user: dict = Depends(get_current_user)):
    """Seed demo data for testing"""
    now = datetime.now(timezone.utc)
    
    # Create demo conversations and leads
    demo_data = [
        {"phone": "+593987654321", "name": "María García", "stage": "lead", "classification": "caliente", "source": "meta_ads"},
        {"phone": "+593912345678", "name": "Juan Pérez", "stage": "pedido", "classification": "tibio", "source": "whatsapp"},
        {"phone": "+593998765432", "name": "Ana López", "stage": "produccion", "classification": "caliente", "source": "web"},
        {"phone": "+593923456789", "name": "Carlos Ruiz", "stage": "lead", "classification": "frio", "source": "organico"},
        {"phone": "+593934567890", "name": "Laura Sánchez", "stage": "cierre", "classification": "caliente", "source": "meta_ads"},
    ]
    
    created_leads = 0
    created_conversations = 0
    
    for data in demo_data:
        # Check if lead exists
        existing_lead = await db.leads.find_one({"phone_number": data["phone"]})
        if existing_lead:
            continue
        
        lead_id = str(uuid.uuid4())
        conv_id = str(uuid.uuid4())
        
        # Create lead
        lead_doc = {
            "id": lead_id,
            "phone_number": data["phone"],
            "name": data["name"],
            "source": data["source"],
            "status": "active",
            "funnel_stage": data["stage"],
            "classification": data["classification"],
            "notes": f"Lead de demostración - {data['source']}",
            "created_at": (now - timedelta(days=created_leads)).isoformat(),
            "updated_at": now.isoformat(),
            "last_message_at": now.isoformat()
        }
        await db.leads.insert_one(lead_doc)
        created_leads += 1
        
        # Create conversation
        conv_doc = {
            "id": conv_id,
            "phone_number": data["phone"],
            "contact_name": data["name"],
            "last_message": f"Hola, estoy interesado en productos promocionales",
            "last_message_time": now.isoformat(),
            "status": "active",
            "unread_count": 1,
            "lead_id": lead_id,
            "created_at": (now - timedelta(days=created_leads)).isoformat()
        }
        await db.conversations.insert_one(conv_doc)
        created_conversations += 1
        
        # Create some messages
        messages = [
            {"sender": "user", "text": "Hola, estoy interesado en productos promocionales"},
            {"sender": "business", "text": f"¡Hola {data['name']}! Gracias por contactarnos. ¿Qué tipo de productos te interesan?"},
            {"sender": "user", "text": "Necesito tazas y termos personalizados para un evento corporativo"}
        ]
        
        for i, msg in enumerate(messages):
            msg_doc = {
                "id": str(uuid.uuid4()),
                "conversation_id": conv_id,
                "phone_number": data["phone"],
                "sender": msg["sender"],
                "message_type": "text",
                "content": {"text": msg["text"]},
                "status": "delivered" if msg["sender"] == "business" else "received",
                "timestamp": (now - timedelta(minutes=30-i*10)).isoformat()
            }
            await db.messages.insert_one(msg_doc)
    
    # Create demo automation rules
    demo_rules = [
        {
            "name": "Bienvenida automática",
            "trigger_type": "new_lead",
            "trigger_value": None,
            "action_type": "send_message",
            "action_value": "¡Hola! Gracias por contactar a Gimmicks Marketing. ¿En qué podemos ayudarte hoy?",
            "is_active": True
        },
        {
            "name": "Respuesta a cotización",
            "trigger_type": "keyword",
            "trigger_value": "cotización,precio,costo,cuánto",
            "action_type": "send_message",
            "action_value": "Con gusto te ayudamos con una cotización. ¿Podrías indicarnos qué productos necesitas y la cantidad aproximada?",
            "is_active": True
        }
    ]
    
    rules_created = 0
    for rule in demo_rules:
        existing = await db.automation_rules.find_one({"name": rule["name"]})
        if not existing:
            rule["id"] = str(uuid.uuid4())
            rule["created_at"] = now.isoformat()
            await db.automation_rules.insert_one(rule)
            rules_created += 1
    
    return {
        "message": "Datos de demostración creados",
        "leads_created": created_leads,
        "conversations_created": created_conversations,
        "rules_created": rules_created
    }

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
