from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import secrets
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import jwt
import bcrypt
import json
from bson import ObjectId
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'gimmicks_crm')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

# Security
security = HTTPBearer()

# ============== SECURITY: Rate Limiting & Login Protection ==============
login_attempts = defaultdict(list)  # {ip: [timestamps]}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes


def check_rate_limit(ip: str, limit: int = 60, window: int = 60) -> bool:
    """Simple in-memory rate limiter. Returns True if allowed."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window)
    login_attempts[ip] = [t for t in login_attempts.get(ip, []) if t > cutoff]
    if len(login_attempts[ip]) >= limit:
        return False
    login_attempts[ip].append(now)
    return True


def check_login_attempts(ip: str) -> bool:
    """Check if IP has exceeded login attempt limit."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    login_attempts[f"login_{ip}"] = [t for t in login_attempts.get(f"login_{ip}", []) if t > cutoff]
    return len(login_attempts[f"login_{ip}"]) < MAX_LOGIN_ATTEMPTS


def record_login_attempt(ip: str):
    login_attempts[f"login_{ip}"].append(datetime.now(timezone.utc))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request demasiado grande"})
        return await call_next(request)

# Create the main app
app = FastAPI(title="Gimmicks CRM - WhatsApp Business")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# --- Import and configure new modular routes (Proyecto B) ---
from routes.inventory_routes import router as inventory_router, set_db as set_inv_db
from routes.quotes_routes import router as quotes_v2_router, set_db as set_quotes_db, set_jwt_secret as set_quotes_jwt
from routes.clients_routes import router as clients_router, set_db as set_clients_db
from routes.dashboard_routes import router as dashboard_v2_router, set_db as set_dash_db, set_jwt_secret as set_dash_jwt

# Inject DB and JWT into B routers
set_inv_db(db)
set_quotes_db(db)
set_quotes_jwt(JWT_SECRET)
set_clients_db(db)
set_dash_db(db)
set_dash_jwt(JWT_SECRET)

# Mount B routers under /api prefix
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory V2"])
api_router.include_router(quotes_v2_router, prefix="/quotes-v2", tags=["Quotes V2"])
api_router.include_router(clients_router, prefix="/clients", tags=["Clients"])
api_router.include_router(dashboard_v2_router, prefix="/dashboard-v2", tags=["Dashboard V2"])

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
    ai_category: Optional[str] = None
    empresa: Optional[str] = None
    ciudad: Optional[str] = None
    correo: Optional[str] = None
    producto_interes: Optional[str] = None
    cantidad_estimada: Optional[str] = None
    presupuesto: Optional[str] = None
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
    is_starred: Optional[bool] = False
    funnel_stage: Optional[str] = None
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
    trigger_type: str  # "keyword", "new_lead", "funnel_change", "no_response", "ai_intent"
    trigger_value: Optional[str] = None
    action_type: str  # "send_message", "change_stage", "assign_agent", "recommend_product", "ai_response"
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

# Conversation State Models (para memoria conversacional)
class ConversationState(BaseModel):
    phone_number: str
    current_step: str  # "greeting", "identify_need", "collect_name", "collect_empresa", etc.
    request_type: Optional[str] = None  # "cotizacion", "catalogo", "ideas", "temporada", "ejecutivo", "urgente"
    collected_data: Dict = {}
    products_recommended: List[str] = []
    catalog_sent: bool = False
    quote_generated: bool = False
    transferred_to_human: bool = False
    last_interaction: datetime

# Quote Models
class QuoteItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    personalization: Optional[str] = None

class Quote(BaseModel):
    id: str
    conversation_id: str
    phone_number: str
    client_name: Optional[str]
    client_empresa: Optional[str]
    items: List[QuoteItem]
    total: float
    delivery_time: str
    notes: Optional[str]
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

def validate_password_strength(password: str) -> str | None:
    """Returns error message if password is weak, None if ok."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    if not re.search(r'[A-Za-z]', password):
        return "La contraseña debe contener al menos una letra"
    if not re.search(r'[0-9]', password):
        return "La contraseña debe contener al menos un número"
    return None

def sanitize_input(value: str) -> str:
    """Basic input sanitization to prevent NoSQL injection."""
    if not isinstance(value, str):
        return value
    dangerous = ['$', '{', '}']
    for char in dangerous:
        value = value.replace(char, '')
    return value.strip()

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
    # Validate password strength
    pwd_error = validate_password_strength(user_data.password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)

    # Check if user exists
    existing = await db.users.find_one({"email": sanitize_input(user_data.email)})
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
async def login(credentials: UserLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if not check_login_attempts(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados intentos de login. Intenta de nuevo en {LOGIN_WINDOW_SECONDS // 60} minutos"
        )

    user = await db.users.find_one({"email": sanitize_input(credentials.email)})
    if not user or not verify_password(credentials.password, user["password"]):
        record_login_attempt(client_ip)
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
    # Validate password strength
    pwd_error = validate_password_strength(user_data.password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)

    # Check if user exists
    existing = await db.users.find_one({"email": sanitize_input(user_data.email)})
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

def build_lead_response(lead: dict) -> LeadResponse:
    """Build LeadResponse from a lead document, handling date parsing."""
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
        ai_category=lead.get("ai_category"),
        empresa=lead.get("empresa"),
        ciudad=lead.get("ciudad"),
        correo=lead.get("correo"),
        producto_interes=lead.get("producto_interes"),
        cantidad_estimada=lead.get("cantidad_estimada"),
        presupuesto=lead.get("presupuesto"),
        created_at=created_at,
        updated_at=updated_at,
        last_message_at=last_message_at
    )

# ============== LEADS ROUTES ==============

FUNNEL_STAGES = ["lead", "cliente_potencial", "cotizacion_generada", "pedido", "produccion", "entregado", "perdido"]
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
    
    return build_lead_response(lead_doc)

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
    
    return [build_lead_response(lead) for lead in leads]

@api_router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    return build_lead_response(lead)


async def _create_client_from_lead(lead_id: str, lead: dict, update_dict: dict):
    """Promote interesado to client or create a new client when lead reaches 'entregado'."""
    now = datetime.now(timezone.utc)
    name = update_dict.get("name") or lead.get("name", "")
    phone = lead.get("phone_number", "")
    email = lead.get("correo", "")

    if not name and not phone:
        return

    # Check if an interesado (source=whatsapp) already exists for this phone/email
    existing = None
    if email:
        existing = await db.clients.find_one({"email": email, "is_deleted": False}, {"_id": 0, "id": 1, "source": 1})
    if not existing and phone:
        phone_clean = phone.lstrip("+")[-10:]
        existing = await db.clients.find_one({"phone": {"$regex": phone_clean}, "is_deleted": False}, {"_id": 0, "id": 1, "source": 1})

    if existing:
        # Promote existing interesado to client
        update_fields = {"source": "manual"}
        if name:
            update_fields["name"] = name
        if email:
            update_fields["email"] = email
        if lead.get("ciudad"):
            update_fields["city"] = lead["ciudad"]
        if lead.get("empresa"):
            update_fields["sector_details"] = lead["empresa"]
        await db.clients.update_one({"id": existing["id"]}, {"$set": update_fields})
        await db.client_activities.insert_one({
            "id": str(uuid.uuid4()),
            "client_id": existing["id"],
            "action": "promoted",
            "details": f"Promovido de Interesado a Cliente al mover Lead #{lead_id} a Entregado",
            "timestamp": now
        })
        logger.info(f"Promoted interesado {existing['id']} to client from lead {lead_id} (entregado)")
        return

    # No existing interesado - create new client directly
    client_id = str(uuid.uuid4())
    client_doc = {
        "id": client_id,
        "name": name or f"Cliente {phone[-4:]}",
        "email": email,
        "commercial_email": "",
        "phone": phone,
        "contact_person": name,
        "address": "",
        "city": lead.get("ciudad", ""),
        "tax_id": "",
        "sector": "",
        "sector_details": lead.get("empresa", ""),
        "notes": f"Creado automaticamente desde Lead #{lead_id} al pasar a Entregado",
        "source": "manual",
        "is_deleted": False,
        "deleted_at": None,
        "created_at": now
    }
    await db.clients.insert_one(client_doc)
    await db.client_activities.insert_one({
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": "created",
        "details": f"Cliente creado automaticamente desde Lead (tel: {phone}) al pasar a Entregado",
        "timestamp": now
    })
    logger.info(f"Auto-created client {client_id} from lead {lead_id} (entregado)")


@api_router.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, update_data: LeadUpdate, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    # Sync name to conversation if changed
    if "name" in update_dict:
        phone = lead.get("phone_number")
        if phone:
            phone_variants = [phone, phone.lstrip("+"), "+" + phone.lstrip("+")]
            await db.conversations.update_many(
                {"phone_number": {"$in": phone_variants}},
                {"$set": {"contact_name": update_dict["name"]}}
            )
    
    # Auto-create client when lead moves to "entregado"
    if update_dict.get("funnel_stage") == "entregado" and lead.get("funnel_stage") != "entregado":
        await _create_client_from_lead(lead_id, lead, update_dict)
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return build_lead_response(updated_lead)

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
    funnel_stage: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    
    conversations = await db.conversations.find(query, {"_id": 0}).sort("last_message_time", -1).skip(skip).limit(limit).to_list(limit)
    
    # Batch-load lead stages for all phone numbers
    phone_numbers = [c["phone_number"] for c in conversations]
    leads_cursor = db.leads.find({"phone_number": {"$in": phone_numbers}}, {"_id": 0, "phone_number": 1, "funnel_stage": 1})
    stage_map = {l["phone_number"]: l.get("funnel_stage", "lead") async for l in leads_cursor}
    
    result = []
    for conv in conversations:
        created_at = conv.get("created_at")
        last_message_time = conv.get("last_message_time")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(last_message_time, str):
            last_message_time = datetime.fromisoformat(last_message_time.replace('Z', '+00:00'))
        
        conv_stage = stage_map.get(conv["phone_number"], "lead")
        
        # Apply funnel_stage filter if provided
        if funnel_stage and conv_stage != funnel_stage:
            continue
        
        result.append(ConversationResponse(
            id=conv["id"],
            phone_number=conv["phone_number"],
            contact_name=conv.get("contact_name"),
            last_message=conv.get("last_message"),
            last_message_time=last_message_time,
            status=conv.get("status", "active"),
            unread_count=conv.get("unread_count", 0),
            lead_id=conv.get("lead_id"),
            is_starred=conv.get("is_starred", False),
            funnel_stage=conv_stage,
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
        is_starred=conv.get("is_starred", False),
        created_at=created_at
    )

# Delete conversation
@api_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Delete conversation
    result = await db.conversations.delete_one({"id": conversation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    # Delete all messages in conversation
    await db.messages.delete_many({"conversation_id": conversation_id})
    
    return {"message": "Conversación eliminada exitosamente"}

# Clear messages from conversation (keep conversation)
@api_router.delete("/conversations/{conversation_id}/messages")
async def clear_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Verify conversation exists
    conv = await db.conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    # Delete all messages
    result = await db.messages.delete_many({"conversation_id": conversation_id})
    
    # Update conversation
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"last_message": None, "unread_count": 0}}
    )
    
    return {"message": f"{result.deleted_count} mensajes eliminados"}

# Toggle star/save conversation
@api_router.patch("/conversations/{conversation_id}/star")
async def toggle_star_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    conv = await db.conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    current_starred = conv.get("is_starred", False)
    new_starred = not current_starred
    
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"is_starred": new_starred}}
    )
    
    return {"is_starred": new_starred, "message": "Conversación guardada" if new_starred else "Conversación quitada de guardados"}

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

@api_router.get("/products")
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
    
    total = await db.products.count_documents(query)
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
    
    return {"products": result, "total": total, "skip": skip, "limit": limit}

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
async def update_automation_rule(
    rule_id: str,
    rule_data: Optional[AutomationRuleCreate] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    update_fields = {}
    if rule_data:
        update_fields = {
            "name": rule_data.name,
            "trigger_type": rule_data.trigger_type,
            "trigger_value": rule_data.trigger_value,
            "action_type": rule_data.action_type,
            "action_value": rule_data.action_value,
            "is_active": rule_data.is_active,
        }
    elif is_active is not None:
        update_fields = {"is_active": is_active}
    else:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    result = await db.automation_rules.update_one(
        {"id": rule_id},
        {"$set": update_fields}
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
    
    # Only text messages trigger the bot
    message_text = content.get("text", "")
    if not message_text.strip():
        return
    
    # Process with AI-powered bot
    from bot_service import process_ai_conversation
    await process_ai_conversation(
        db=db,
        phone_number=phone_number,
        message_text=message_text,
        conversation_id=conversation["id"],
        send_message_fn=send_bot_message
    )

# ============== INTELLIGENT BOT FUNCTIONS ==============

CONVERSATION_STEPS = [
    "greeting",
    "identify_need", 
    "collect_name",
    "collect_empresa",
    "collect_ciudad",
    "collect_correo",
    "collect_producto",
    "collect_cantidad",
    "collect_fecha",
    "collect_presupuesto",
    "collect_personalizacion",
    "confirm_data",
    "send_catalog",
    "generate_quote",
    "transfer_human"
]

REQUEST_TYPES = {
    "cotizacion": ["cotiza", "precio", "cuanto", "cuesta", "valor", "costo", "tarifa"],
    "catalogo": ["catalogo", "catálogo", "productos", "ver", "mostrar", "tienen", "ofrecen"],
    "ideas": ["idea", "sugerencia", "recomienda", "qué me", "opciones", "alternativas", "ayuda"],
    "temporada": ["navidad", "san valentin", "valentín", "día de", "madre", "padre", "playa", "verano", "evento", "fiestas", "halloween"],
    "ejecutivo": ["ejecutivo", "corporativo", "empresa", "empresarial", "premium", "lujo", "regalo corporativo"],
    "urgente": ["urgente", "rápido", "pronto", "mañana", "hoy", "inmediato", "express", "ya mismo"]
}

REQUIRED_FIELDS = ["nombre", "empresa", "ciudad", "correo", "producto", "cantidad", "fecha_entrega", "presupuesto", "personalizacion"]

async def get_conversation_state(phone_number: str) -> Optional[Dict]:
    state = await db.conversation_states.find_one({"phone_number": phone_number}, {"_id": 0})
    return state

async def update_conversation_state(phone_number: str, updates: Dict):
    updates["last_interaction"] = datetime.now(timezone.utc).isoformat()
    await db.conversation_states.update_one(
        {"phone_number": phone_number},
        {"$set": updates},
        upsert=True
    )

async def identify_request_type(message: str) -> str:
    message_lower = message.lower().strip()
    for req_type, keywords in REQUEST_TYPES.items():
        if any(kw in message_lower for kw in keywords):
            return req_type
    return "general"

async def extract_data_from_message(message: str, current_step: str, collected_data: Dict) -> Dict:
    message = message.strip()
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
    if email_match:
        collected_data["correo"] = email_match.group()
    
    number_match = re.search(r'\b(\d+)\b', message)
    
    step_field_map = {
        "collect_name": "nombre",
        "collect_empresa": "empresa", 
        "collect_ciudad": "ciudad",
        "collect_correo": "correo",
        "collect_producto": "producto",
        "collect_cantidad": "cantidad",
        "collect_fecha": "fecha_entrega",
        "collect_presupuesto": "presupuesto",
        "collect_personalizacion": "personalizacion"
    }
    
    if current_step in step_field_map:
        field = step_field_map[current_step]
        if field == "cantidad" and number_match:
            collected_data[field] = number_match.group()
        elif field == "correo" and email_match:
            pass
        elif field == "correo" and not email_match:
            collected_data[field] = message
        elif field not in ["correo"]:
            collected_data[field] = message
    
    return collected_data

def format_price_ecuador(price: float) -> str:
    return f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def generate_quote_message(phone_number: str, collected_data: Dict) -> str:
    try:
        product_need = collected_data.get("producto", "").lower()
        
        products = await db.products.find({
            "$or": [
                {"name": {"$regex": product_need, "$options": "i"}},
                {"categories": {"$regex": product_need, "$options": "i"}},
                {"category_1": {"$regex": product_need, "$options": "i"}},
                {"category_2": {"$regex": product_need, "$options": "i"}},
                {"description": {"$regex": product_need, "$options": "i"}}
            ]
        }, {"_id": 0}).limit(5).to_list(5)
        
        if not products:
            products = await db.products.find({}, {"_id": 0}).limit(3).to_list(3)
        
        if not products:
            return "Gracias por tu interés. No encontramos productos específicos en nuestro catálogo actual. Un asesor te contactará con opciones personalizadas."
        
        cantidad_str = collected_data.get("cantidad", "")
        try:
            cantidad = int(re.search(r'\d+', str(cantidad_str)).group()) if cantidad_str else None
        except:
            cantidad = None
        
        quantities = [cantidad] if cantidad else [50, 100, 300]
        
        quote_lines = ["*COTIZACIÓN GIMMICKS*\n"]
        quote_lines.append(f"Cliente: {collected_data.get('nombre', 'N/A')}")
        quote_lines.append(f"Empresa: {collected_data.get('empresa', 'N/A')}")
        quote_lines.append(f"Ciudad: {collected_data.get('ciudad', 'N/A')}\n")
        
        total_general = 0
        quote_items = []
        
        for product in products[:3]:
            product_name = product.get("name", "Producto")
            base_price = product.get("price", 0) or 5.00
            
            quote_lines.append(f"*{product_name}*")
            if product.get("description"):
                quote_lines.append(f"  {product['description'][:80]}")
            
            for qty in quantities:
                if qty >= 300:
                    unit_price = base_price * 0.85
                elif qty >= 100:
                    unit_price = base_price * 0.90
                else:
                    unit_price = base_price
                
                subtotal = unit_price * qty
                total_general += subtotal
                
                quote_lines.append(f"  {qty} unidades: {format_price_ecuador(unit_price)} c/u = {format_price_ecuador(subtotal)}")
                
                quote_items.append({
                    "product_id": product.get("id", ""),
                    "product_name": product_name,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "subtotal": subtotal
                })
            
            quote_lines.append("")
        
        if collected_data.get("personalizacion") and collected_data["personalizacion"].lower() not in ["no", "ninguna", "n/a"]:
            quote_lines.append(f"Personalización: {collected_data['personalizacion']}")
            quote_lines.append("Nota: El precio puede variar según complejidad del diseño.\n")
        
        fecha_entrega = collected_data.get("fecha_entrega", "")
        if any(w in str(fecha_entrega).lower() for w in ["urgente", "pronto", "rápido", "express", "hoy", "mañana"]):
            delivery = "3-5 días hábiles (servicio express)"
        else:
            delivery = "7-10 días hábiles"
        
        quote_lines.append(f"Tiempo de entrega: {delivery}")
        quote_lines.append("\n*Precios incluyen IVA*")
        quote_lines.append("Cotización válida por 15 días")
        
        # Save quote to DB
        conv = await db.conversations.find_one({"phone_number": phone_number}, {"_id": 0, "id": 1})
        quote_doc = {
            "id": str(uuid.uuid4()),
            "conversation_id": conv["id"] if conv else "",
            "phone_number": phone_number,
            "client_name": collected_data.get("nombre"),
            "client_empresa": collected_data.get("empresa"),
            "items": quote_items,
            "total": total_general,
            "delivery_time": delivery,
            "personalization": collected_data.get("personalizacion"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quotes.insert_one(quote_doc)
        logger.info(f"Quote saved for {phone_number}, total: {total_general}")
        
        return "\n".join(quote_lines)
        
    except Exception as e:
        logger.error(f"Error generating quote: {e}")
        return "Gracias por contactarnos, en un momento atenderemos tu requerimiento."

async def get_catalog_message(request_type: str, product_need: str = "") -> str:
    try:
        query = {}
        catalog_title = "CATÁLOGO GIMMICKS"
        
        if request_type == "temporada":
            query = {"$or": [
                {"categories": {"$regex": "navidad|evento|temporada|playa|verano", "$options": "i"}},
                {"category_1": {"$regex": "navidad|evento|temporada|playa|verano", "$options": "i"}},
                {"category_2": {"$regex": "navidad|evento|temporada|playa|verano", "$options": "i"}}
            ]}
            catalog_title = "CATÁLOGO DE TEMPORADA"
        elif request_type == "ejecutivo":
            query = {"$or": [
                {"categories": {"$regex": "ejecutivo|premium|corporativo|lujo", "$options": "i"}},
                {"category_1": {"$regex": "ejecutivo|premium|corporativo|lujo", "$options": "i"}},
                {"category_2": {"$regex": "ejecutivo|premium|corporativo|lujo", "$options": "i"}}
            ]}
            catalog_title = "CATÁLOGO EJECUTIVO / CORPORATIVO"
        elif product_need:
            query = {"$or": [
                {"name": {"$regex": product_need, "$options": "i"}},
                {"categories": {"$regex": product_need, "$options": "i"}},
                {"category_1": {"$regex": product_need, "$options": "i"}},
                {"description": {"$regex": product_need, "$options": "i"}}
            ]}
            catalog_title = f"PRODUCTOS: {product_need.upper()}"
        
        products = await db.products.find(query, {"_id": 0}).limit(10).to_list(10)
        
        if not products:
            products = await db.products.find({}, {"_id": 0}).limit(10).to_list(10)
            catalog_title = "CATÁLOGO GENERAL GIMMICKS"
        
        if not products:
            return "Nuestro catálogo está siendo actualizado. Un asesor te enviará las opciones disponibles pronto."
        
        catalog_lines = [f"*{catalog_title}*\n"]
        
        for i, product in enumerate(products, 1):
            name = product.get("name", "Producto")
            desc = product.get("description", "")[:60] if product.get("description") else ""
            price = product.get("price")
            sku = product.get("sku", "")
            
            catalog_lines.append(f"*{i}. {name}*")
            if sku:
                catalog_lines.append(f"  Código: {sku}")
            if desc:
                catalog_lines.append(f"  {desc}")
            if price:
                catalog_lines.append(f"  Desde: {format_price_ecuador(price)}")
            catalog_lines.append("")
        
        catalog_lines.append("¿Te interesa algún producto? Dime el número o nombre y te doy más detalles.")
        
        return "\n".join(catalog_lines)
        
    except Exception as e:
        logger.error(f"Error generating catalog: {e}")
        return "Un asesor te enviará nuestro catálogo completo pronto."

async def transfer_to_human(phone_number: str, collected_data: Dict, conversation_id: str) -> str:
    try:
        summary_lines = [
            "*NUEVO CASO PARA ATENCIÓN*\n",
            f"Teléfono: {phone_number}",
            f"Nombre: {collected_data.get('nombre', 'No proporcionado')}",
            f"Empresa: {collected_data.get('empresa', 'No proporcionado')}",
            f"Ciudad: {collected_data.get('ciudad', 'No proporcionado')}",
            f"Correo: {collected_data.get('correo', 'No proporcionado')}",
            f"\nProducto/Necesidad: {collected_data.get('producto', 'No especificado')}",
            f"Cantidad: {collected_data.get('cantidad', 'No especificada')}",
            f"Fecha entrega: {collected_data.get('fecha_entrega', 'No especificada')}",
            f"Presupuesto: {collected_data.get('presupuesto', 'No especificado')}",
            f"Personalización: {collected_data.get('personalizacion', 'No especificada')}",
        ]
        
        quote = await db.quotes.find_one({"phone_number": phone_number}, {"_id": 0}, sort=[("created_at", -1)])
        if quote:
            summary_lines.append(f"\nCotización generada: {format_price_ecuador(quote.get('total', 0))}")
            summary_lines.append(f"Productos: {', '.join([i.get('product_name','') for i in quote.get('items',[])])}")
        
        summary = "\n".join(summary_lines)
        
        await db.conversation_states.update_one(
            {"phone_number": phone_number},
            {"$set": {
                "transferred_to_human": True,
                "transfer_summary": summary,
                "transfer_time": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await db.leads.update_one(
            {"phone_number": phone_number},
            {"$set": {
                "name": collected_data.get("nombre"),
                "empresa": collected_data.get("empresa"),
                "ciudad": collected_data.get("ciudad"),
                "correo": collected_data.get("correo"),
                "producto_interes": collected_data.get("producto"),
                "cantidad_estimada": collected_data.get("cantidad"),
                "fecha_entrega": collected_data.get("fecha_entrega"),
                "presupuesto": collected_data.get("presupuesto"),
                "personalizacion": collected_data.get("personalizacion"),
                "funnel_stage": "qualified",
                "classification": "caliente",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Update conversation contact_name with collected name
        if collected_data.get("nombre"):
            await db.conversations.update_one(
                {"phone_number": phone_number},
                {"$set": {"contact_name": collected_data["nombre"]}}
            )
        
        logger.info(f"Case transferred to human: {phone_number}\n{summary}")
        
        return "¡Perfecto! He recopilado toda tu información.\n\n*Ana María*, nuestra asesora comercial, se pondrá en contacto contigo muy pronto para finalizar los detalles.\n\n¡Gracias por preferirnos!"
        
    except Exception as e:
        logger.error(f"Error transferring to human: {e}")
        return "Un asesor te contactará pronto. ¡Gracias!"

async def send_bot_message(phone_number: str, conversation_id: str, message: str):
    """Send a message from the bot and save it to DB"""
    now = datetime.now(timezone.utc)
    
    # Always save to DB first
    msg_doc = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "phone_number": phone_number,
        "sender": "business",
        "message_type": "text",
        "content": {"text": message},
        "status": "sent",
        "is_automated": True,
        "timestamp": now.isoformat()
    }
    try:
        await db.messages.insert_one(msg_doc)
        await db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {
                "last_message": message[:100],
                "last_message_time": now.isoformat()
            }}
        )
    except Exception as e:
        logger.error(f"Error saving bot message to DB: {e}")
    
    # Then try to send via WhatsApp
    try:
        await send_whatsapp_message(phone_number, message)
        logger.info(f"Bot message sent to {phone_number}: {message[:60]}...")
    except Exception as e:
        logger.warning(f"WhatsApp send failed for {phone_number}: {e}")

async def process_intelligent_conversation(phone_number: str, message_text: str, conversation_id: str, is_new_lead: bool = False):
    """Main intelligent conversation handler - single entry point for all bot logic"""
    try:
        state = await get_conversation_state(phone_number)
        
        if not state:
            # Brand new conversation
            state = {
                "phone_number": phone_number,
                "current_step": "greeting",
                "request_type": None,
                "collected_data": {},
                "catalog_sent": False,
                "quote_generated": False,
                "transferred_to_human": False,
                "message_count": 0,
                "last_interaction": datetime.now(timezone.utc).isoformat()
            }
            await db.conversation_states.update_one(
                {"phone_number": phone_number},
                {"$set": state},
                upsert=True
            )
            
            # Send welcome and immediately ask for need
            welcome = "¡Hola! Bienvenido a *Gimmicks Marketing Services*. Somos especialistas en productos promocionales y publicitarios.\n\n¿En qué podemos ayudarte hoy?\n\n1. Cotización de productos\n2. Ver nuestro catálogo\n3. Necesito ideas/sugerencias\n4. Productos de temporada\n5. Regalos corporativos/ejecutivos\n6. Tengo un pedido urgente"
            await send_bot_message(phone_number, conversation_id, welcome)
            
            await update_conversation_state(phone_number, {
                "current_step": "identify_need",
                "message_count": 1
            })
            return
        
        # If already transferred to human, let human handle it
        if state.get("transferred_to_human"):
            await send_bot_message(phone_number, conversation_id, 
                "Ana María ya tiene tu caso y te contactará muy pronto. Si necesitas algo adicional, ella te ayudará directamente.")
            return
        
        current_step = state.get("current_step", "identify_need")
        collected_data = state.get("collected_data", {})
        request_type = state.get("request_type")
        msg_count = state.get("message_count", 0) + 1
        
        # Extract data from current message
        collected_data = await extract_data_from_message(message_text, current_step, collected_data)
        
        # Detect request type if not already set
        if not request_type:
            request_type = await identify_request_type(message_text)
        
        response = None
        next_step = current_step
        
        # ====== STATE MACHINE ======
        
        if current_step == "greeting":
            # Shouldn't normally reach here, but handle gracefully
            welcome = "¡Hola! Bienvenido a *Gimmicks Marketing Services*.\n\n¿En qué podemos ayudarte hoy?"
            await send_bot_message(phone_number, conversation_id, welcome)
            next_step = "identify_need"
        
        elif current_step == "identify_need":
            # Check if user selected a number option
            msg_stripped = message_text.strip()
            if msg_stripped == "1":
                request_type = "cotizacion"
            elif msg_stripped == "2":
                request_type = "catalogo"
            elif msg_stripped == "3":
                request_type = "ideas"
            elif msg_stripped == "4":
                request_type = "temporada"
            elif msg_stripped == "5":
                request_type = "ejecutivo"
            elif msg_stripped == "6":
                request_type = "urgente"
            else:
                request_type = await identify_request_type(message_text)
            
            if request_type == "catalogo":
                catalog = await get_catalog_message(request_type, message_text)
                await send_bot_message(phone_number, conversation_id, catalog)
                await update_conversation_state(phone_number, {"catalog_sent": True})
                response = "¿Te gustaría cotizar alguno de estos productos? Para continuar, necesito algunos datos.\n\n¿Cuál es tu nombre completo?"
                next_step = "collect_name"
            
            elif request_type == "cotizacion":
                response = "¡Perfecto! Para darte una cotización precisa, necesito algunos datos.\n\n¿Cuál es tu nombre completo?"
                next_step = "collect_name"
            
            elif request_type == "ideas":
                response = "¡Con gusto te ayudo con ideas!\n\n¿Para qué ocasión o evento necesitas los productos promocionales?\n\nPor ejemplo: evento corporativo, feria, regalo de fin de año, lanzamiento de marca, etc."
                next_step = "collect_producto"
            
            elif request_type in ["temporada", "ejecutivo"]:
                catalog = await get_catalog_message(request_type)
                await send_bot_message(phone_number, conversation_id, catalog)
                await update_conversation_state(phone_number, {"catalog_sent": True})
                response = "¿Alguno te interesa? Para avanzar, dime tu nombre completo."
                next_step = "collect_name"
            
            elif request_type == "urgente":
                response = "Entiendo que es urgente. Haremos todo lo posible por ayudarte.\n\nPara agilizar, dime tu nombre completo."
                next_step = "collect_name"
            
            else:
                response = "¡Gracias por escribirnos! Para ayudarte mejor, cuéntame: ¿qué tipo de productos promocionales buscas?\n\nPuedes describir lo que necesitas o elegir una opción:\n1. Cotización\n2. Catálogo\n3. Ideas\n4. Temporada\n5. Corporativos\n6. Urgente"
                next_step = "identify_need"
        
        elif current_step == "collect_name":
            collected_data["nombre"] = message_text.strip()
            first_name = message_text.strip().split()[0]
            response = f"Gracias {first_name}. ¿De qué empresa nos contactas?"
            next_step = "collect_empresa"
        
        elif current_step == "collect_empresa":
            collected_data["empresa"] = message_text.strip()
            response = "¿En qué ciudad te encuentras?"
            next_step = "collect_ciudad"
        
        elif current_step == "collect_ciudad":
            collected_data["ciudad"] = message_text.strip()
            response = "¿Me puedes dar tu correo electrónico para enviarte la cotización formal?"
            next_step = "collect_correo"
        
        elif current_step == "collect_correo":
            if not collected_data.get("correo"):
                collected_data["correo"] = message_text.strip()
            
            if collected_data.get("producto"):
                response = "¿Qué cantidad aproximada necesitas?\n\nSi no estás seguro, te puedo cotizar varias opciones (50, 100 y 300 unidades)."
                next_step = "collect_cantidad"
            else:
                response = "¿Qué producto o tipo de artículo promocional te interesa?\n\nPuedes describir lo que buscas o el tipo de evento."
                next_step = "collect_producto"
        
        elif current_step == "collect_producto":
            collected_data["producto"] = message_text.strip()
            
            if not state.get("catalog_sent"):
                catalog = await get_catalog_message("general", message_text)
                await send_bot_message(phone_number, conversation_id, catalog)
                await update_conversation_state(phone_number, {"catalog_sent": True})
            
            # Check if we still need name
            if not collected_data.get("nombre"):
                response = "Para preparar tu cotización, necesito algunos datos.\n\n¿Cuál es tu nombre completo?"
                next_step = "collect_name"
            else:
                response = "¿Qué cantidad aproximada necesitas?\n\nSi no estás seguro, te puedo cotizar varias opciones."
                next_step = "collect_cantidad"
        
        elif current_step == "collect_cantidad":
            collected_data["cantidad"] = message_text.strip()
            response = "¿Para cuándo necesitas los productos?\n\n(Ejemplo: próxima semana, 15 de marzo, lo antes posible)"
            next_step = "collect_fecha"
        
        elif current_step == "collect_fecha":
            collected_data["fecha_entrega"] = message_text.strip()
            response = "¿Tienes un presupuesto estimado?\n\n(Puedes escribir un rango, monto aproximado, o 'flexible' si prefieres que te demos opciones)"
            next_step = "collect_presupuesto"
        
        elif current_step == "collect_presupuesto":
            collected_data["presupuesto"] = message_text.strip()
            response = "¿Necesitas personalización?\n\nPor ejemplo: logo impreso, nombre grabado, colores específicos, diseño especial.\n\n(Escribe 'no' si no aplica)"
            next_step = "collect_personalizacion"
        
        elif current_step == "collect_personalizacion":
            personalizacion = message_text.strip()
            if personalizacion.lower() in ["no", "ninguna", "n/a", "nada", "sin personalización"]:
                collected_data["personalizacion"] = "Sin personalización"
            else:
                collected_data["personalizacion"] = personalizacion
            
            # Show data summary for confirmation
            summary = "Perfecto, tengo todos tus datos. Déjame confirmar:\n\n"
            summary += f"Nombre: {collected_data.get('nombre', '-')}\n"
            summary += f"Empresa: {collected_data.get('empresa', '-')}\n"
            summary += f"Ciudad: {collected_data.get('ciudad', '-')}\n"
            summary += f"Correo: {collected_data.get('correo', '-')}\n"
            summary += f"Producto: {collected_data.get('producto', '-')}\n"
            summary += f"Cantidad: {collected_data.get('cantidad', '-')}\n"
            summary += f"Fecha entrega: {collected_data.get('fecha_entrega', '-')}\n"
            summary += f"Presupuesto: {collected_data.get('presupuesto', '-')}\n"
            summary += f"Personalización: {collected_data.get('personalizacion', '-')}\n"
            summary += "\n¿Los datos son correctos? (sí/no)"
            
            response = summary
            next_step = "confirm_data"
        
        elif current_step == "confirm_data":
            msg_lower = message_text.strip().lower()
            
            if msg_lower in ["si", "sí", "s", "correcto", "ok", "yes", "está bien", "confirmo"]:
                # Generate quote
                await send_bot_message(phone_number, conversation_id, "Generando tu cotización...")
                
                quote_msg = await generate_quote_message(phone_number, collected_data)
                await send_bot_message(phone_number, conversation_id, quote_msg)
                await update_conversation_state(phone_number, {"quote_generated": True})
                
                # Transfer to Ana María
                transfer_msg = await transfer_to_human(phone_number, collected_data, conversation_id)
                response = transfer_msg
                next_step = "transfer_human"
            
            elif msg_lower in ["no", "n", "corregir", "cambiar"]:
                response = "¿Qué dato necesitas corregir?\n\n1. Nombre\n2. Empresa\n3. Ciudad\n4. Correo\n5. Producto\n6. Cantidad\n7. Fecha\n8. Presupuesto\n9. Personalización"
                next_step = "correct_data"
            else:
                response = "Por favor responde *sí* si los datos son correctos, o *no* si necesitas corregir algo."
                next_step = "confirm_data"
        
        elif current_step == "correct_data":
            correction_map = {
                "1": ("collect_name", "nombre", "¿Cuál es tu nombre correcto?"),
                "2": ("collect_empresa", "empresa", "¿Cuál es la empresa correcta?"),
                "3": ("collect_ciudad", "ciudad", "¿Cuál es la ciudad correcta?"),
                "4": ("collect_correo", "correo", "¿Cuál es el correo correcto?"),
                "5": ("collect_producto", "producto", "¿Qué producto necesitas?"),
                "6": ("collect_cantidad", "cantidad", "¿Qué cantidad necesitas?"),
                "7": ("collect_fecha", "fecha_entrega", "¿Para cuándo lo necesitas?"),
                "8": ("collect_presupuesto", "presupuesto", "¿Cuál es tu presupuesto?"),
                "9": ("collect_personalizacion", "personalizacion", "¿Qué personalización necesitas?"),
            }
            
            choice = message_text.strip()
            if choice in correction_map:
                step, field, question = correction_map[choice]
                response = question
                next_step = step
            else:
                # Try to match by keyword
                msg_lower = message_text.lower()
                matched = False
                keywords_map = {
                    "nombre": "1", "empresa": "2", "ciudad": "3", "correo": "4",
                    "producto": "5", "cantidad": "6", "fecha": "7", "presupuesto": "8",
                    "personaliz": "9"
                }
                for kw, num in keywords_map.items():
                    if kw in msg_lower:
                        step, field, question = correction_map[num]
                        response = question
                        next_step = step
                        matched = True
                        break
                
                if not matched:
                    response = "No entendí qué dato quieres corregir. Por favor escribe el número (1-9) del dato a corregir."
                    next_step = "correct_data"
        
        elif current_step == "transfer_human":
            response = "Ana María ya tiene tu caso y te contactará muy pronto.\n\n¿Hay algo más que necesites agregar a tu solicitud?"
        
        # ====== UPDATE STATE ======
        await update_conversation_state(phone_number, {
            "current_step": next_step,
            "collected_data": collected_data,
            "request_type": request_type,
            "message_count": msg_count
        })
        
        if response:
            await send_bot_message(phone_number, conversation_id, response)
        
    except Exception as e:
        logger.error(f"Error in intelligent conversation for {phone_number}: {e}", exc_info=True)
        try:
            await send_bot_message(phone_number, conversation_id, 
                "Gracias por contactarnos, en un momento atenderemos tu requerimiento.")
        except:
            pass

async def process_automation_rules(phone_number: str, message_text: str, conversation_id: str, is_new_lead: bool = False):
    """Process automation rules and send automatic responses"""
    try:
        # Get all active rules
        rules = await db.automation_rules.find({"is_active": True}, {"_id": 0}).to_list(100)
        
        for rule in rules:
            should_trigger = False
            
            # Check trigger conditions
            if rule["trigger_type"] == "new_lead" and is_new_lead:
                should_trigger = True
                
            elif rule["trigger_type"] == "keyword" and rule.get("trigger_value"):
                keywords = [k.strip().lower() for k in rule["trigger_value"].split(",")]
                if any(keyword in message_text for keyword in keywords):
                    should_trigger = True
            
            elif rule["trigger_type"] == "ai_intent":
                # AI analyzes the message intent for product recommendations
                should_trigger = await check_ai_intent(message_text, rule.get("trigger_value", ""))
            
            # Execute action if triggered
            if should_trigger:
                logger.info(f"Rule triggered: {rule['name']}")
                
                if rule["action_type"] == "send_message":
                    # Send automatic response via WhatsApp
                    try:
                        await send_whatsapp_message(phone_number, rule["action_value"])
                        
                        # Save the sent message to database
                        now = datetime.now(timezone.utc)
                        auto_msg = {
                            "id": str(uuid.uuid4()),
                            "conversation_id": conversation_id,
                            "phone_number": phone_number,
                            "sender": "business",
                            "message_type": "text",
                            "content": {"text": rule["action_value"]},
                            "status": "sent",
                            "is_automated": True,
                            "rule_name": rule["name"],
                            "timestamp": now.isoformat()
                        }
                        await db.messages.insert_one(auto_msg)
                        
                        # Update conversation
                        await db.conversations.update_one(
                            {"id": conversation_id},
                            {"$set": {
                                "last_message": rule["action_value"][:100],
                                "last_message_time": now.isoformat()
                            }}
                        )
                        
                        logger.info(f"Auto-response sent to {phone_number}")
                    except Exception as e:
                        logger.error(f"Failed to send auto-response: {e}")
                
                elif rule["action_type"] == "ai_response":
                    # Generate AI response with product recommendations
                    try:
                        ai_response = await generate_ai_product_response(message_text)
                        if ai_response:
                            await send_whatsapp_message(phone_number, ai_response)
                            
                            now = datetime.now(timezone.utc)
                            auto_msg = {
                                "id": str(uuid.uuid4()),
                                "conversation_id": conversation_id,
                                "phone_number": phone_number,
                                "sender": "business",
                                "message_type": "text",
                                "content": {"text": ai_response},
                                "status": "sent",
                                "is_automated": True,
                                "rule_name": rule["name"],
                                "timestamp": now.isoformat()
                            }
                            await db.messages.insert_one(auto_msg)
                            
                            await db.conversations.update_one(
                                {"id": conversation_id},
                                {"$set": {
                                    "last_message": ai_response[:100],
                                    "last_message_time": now.isoformat()
                                }}
                            )
                            logger.info(f"AI response sent to {phone_number}")
                    except Exception as e:
                        logger.error(f"Failed to send AI response: {e}")
                
                elif rule["action_type"] == "change_stage":
                    # Update lead stage
                    conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
                    if conv and conv.get("lead_id"):
                        await db.leads.update_one(
                            {"id": conv["lead_id"]},
                            {"$set": {"funnel_stage": rule["action_value"], "updated_at": datetime.now(timezone.utc).isoformat()}}
                        )
                        logger.info(f"Lead stage changed to {rule['action_value']}")
                
                # Only execute first matching rule to avoid spam
                break
                
    except Exception as e:
        logger.error(f"Error processing automation rules: {e}")


async def check_ai_intent(message: str, intent_keywords: str) -> bool:
    """Check if message matches AI intent using keywords or patterns"""
    message_lower = message.lower()
    
    # Product-related keywords
    product_keywords = ["precio", "cuanto", "cuesta", "catalogo", "producto", "tienen", "venden", 
                       "busco", "necesito", "cotización", "cotizar", "disponible", "stock"]
    
    if intent_keywords:
        keywords = [k.strip().lower() for k in intent_keywords.split(",")]
        return any(kw in message_lower for kw in keywords)
    
    # Default: check for product-related queries
    return any(kw in message_lower for kw in product_keywords)


async def generate_ai_product_response(message: str) -> Optional[str]:
    """Generate an AI response with product recommendations based on user message"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return None
        
        products = await db.products.find({}, {"_id": 0}).limit(100).to_list(100)
        
        if not products:
            return "Gracias por tu interés. Actualmente estamos actualizando nuestro catálogo. Un asesor te contactará pronto con más información."
        
        products_context = "\n".join([
            f"- {p['name']}: {p.get('description', 'Sin descripción')[:150]} | Categoría: {p.get('category_1', 'General')} | Precio: ${p.get('price', 'Consultar')}"
            for p in products
        ])
        
        system_message = f"""Eres un asistente de ventas amigable de Gimmicks Marketing Services, especializado en productos promocionales y publicitarios.

Tu tarea es responder al cliente de manera profesional y sugerir productos relevantes basándote en su consulta.

CATÁLOGO DE PRODUCTOS DISPONIBLES:
{products_context}

INSTRUCCIONES:
1. Analiza lo que el cliente está buscando
2. Recomienda 1-3 productos relevantes de nuestro catálogo
3. Incluye nombre, descripción breve y precio si está disponible
4. Sé amigable y profesional
5. Si no hay productos exactos, sugiere alternativas similares
6. Invita al cliente a solicitar cotización o más información
7. Responde en español
8. Mantén la respuesta concisa (máximo 300 caracteres para WhatsApp)

NO uses formato markdown, solo texto plano."""

        chat = LlmChat(api_key=api_key, session_id=f"product-rec-{uuid.uuid4().hex[:8]}", system_message=system_message)
        chat.with_model("openai", "gpt-4o-mini")
        ai_response = await chat.send_message(UserMessage(text=f"Cliente dice: {message}"))
        return ai_response.strip()
        
    except Exception as e:
        logger.error(f"Error generating AI product response: {e}")
        return None

# ============== AI ANALYSIS ROUTES ==============

@api_router.post("/ai/analyze-message")
async def analyze_message(
    message: str = "",
    conversation_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Analyze full conversation context using AI to provide actionable insights"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return {
                "intent": "consulta",
                "lead_classification": "tibio",
                "suggested_products": [],
                "suggested_response": "Gracias por tu mensaje. Un asesor te contactará pronto.",
                "analysis_notes": "API key no configurada",
                "next_action": "Configurar EMERGENT_LLM_KEY",
                "quote_status": "sin_datos"
            }
        
        # Build full conversation context
        conversation_text = ""
        lead_context = ""
        state_context = ""
        
        if conversation_id:
            # Get all messages
            msgs = await db.messages.find(
                {"conversation_id": conversation_id},
                {"_id": 0, "sender": 1, "content": 1, "timestamp": 1}
            ).sort("timestamp", 1).to_list(50)
            
            lines = []
            for m in msgs:
                role = "Cliente" if m["sender"] == "user" else "Bot/Asesor"
                text = m.get("content", {}).get("text", "")
                if text:
                    lines.append(f"{role}: {text[:300]}")
            conversation_text = "\n".join(lines)
            
            # Get conversation phone number
            conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0, "phone_number": 1})
            if conv:
                phone = conv["phone_number"]
                # Get lead data
                lead = await db.leads.find_one({"phone_number": phone}, {"_id": 0})
                if lead:
                    lead_parts = []
                    for k in ["name", "empresa", "correo", "ciudad", "funnel_stage", "classification", "producto_interes", "cantidad_estimada", "personalizacion"]:
                        v = lead.get(k)
                        if v and str(v).strip():
                            lead_parts.append(f"{k}: {v}")
                    lead_context = "\n".join(lead_parts) if lead_parts else "Sin datos previos"
                
                # Get conversation state
                state = await db.conversation_states.find_one({"phone_number": phone}, {"_id": 0})
                if state:
                    state_context = f"Cotizacion generada: {'Si' if state.get('quote_generated') else 'No'}\nDatos recopilados: {json.dumps(state.get('collected_data', {}), ensure_ascii=False)}"
        
        system_msg = """Eres un analista comercial de Gimmicks Marketing Services. Analiza la conversacion completa con el cliente y proporciona un diagnostico accionable para el asesor.

Responde SIEMPRE en JSON valido:
{
    "intent": "cotizacion|consulta|queja|seguimiento|informacion|otro",
    "lead_classification": "frio|tibio|caliente",
    "quote_status": "sin_datos|datos_parciales|listo_para_cotizar|ya_cotizado",
    "missing_data": ["lista de datos que faltan para cotizar"],
    "next_action": "accion concreta que debe tomar el asesor",
    "suggested_response": "respuesta sugerida para el asesor",
    "suggested_products": ["productos relevantes si aplica"],
    "analysis_notes": "resumen ejecutivo del estado de la conversacion"
}"""

        user_msg = f"""CONVERSACION COMPLETA:
{conversation_text if conversation_text else f'Ultimo mensaje: {message}'}

DATOS DEL LEAD:
{lead_context if lead_context else 'Sin datos previos'}

ESTADO DE LA CONVERSACION:
{state_context if state_context else 'Sin estado'}

Analiza: 1) El cliente tiene intencion de cotizar? 2) Ya cotizo? 3) Que datos faltan? 4) Cual es la mejor accion siguiente?"""

        chat = LlmChat(api_key=api_key, session_id=f"analyze-{uuid.uuid4().hex[:8]}", system_message=system_msg)
        chat.with_model("openai", "gpt-4o-mini")
        response_text = await chat.send_message(UserMessage(text=user_msg))
        
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                pass
        
        return {
            "intent": "otro",
            "lead_classification": "frio",
            "suggested_products": [],
            "suggested_response": response_text,
            "analysis_notes": "Respuesta sin formato JSON",
            "next_action": "Revisar manualmente",
            "quote_status": "sin_datos",
            "missing_data": []
        }
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        return {
            "intent": "consulta",
            "lead_classification": "tibio",
            "suggested_products": [],
            "suggested_response": "Gracias por tu mensaje. Un asesor te contactará pronto.",
            "analysis_notes": f"Error en análisis: {str(e)}",
            "next_action": "Revisar manualmente",
            "quote_status": "sin_datos",
            "missing_data": []
        }

@api_router.post("/ai/recommend-products")
async def recommend_products(
    query: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Recommend products based on customer query using AI"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
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
        
        chat = LlmChat(api_key=api_key, session_id=f"recommend-{uuid.uuid4().hex[:8]}", system_message=system_message)
        chat.with_model("openai", "gpt-4o-mini")
        response_text = await chat.send_message(UserMessage(text=f"El cliente necesita: {query}"))
        
        try:
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
            "last_message": "Hola, estoy interesado en productos promocionales",
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

# ============== ADMIN: RESET CONVERSATION STATES ==============

@api_router.post("/admin/reset-conversation-states")
async def reset_conversation_states(current_user: dict = Depends(get_current_user)):
    """Reset all conversation states so bot responds to everyone again"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    result = await db.conversation_states.delete_many({})
    return {"message": f"Estados de conversación limpiados: {result.deleted_count} eliminados"}

@api_router.post("/admin/reset-conversation/{phone_number}")
async def reset_single_conversation(phone_number: str, current_user: dict = Depends(get_current_user)):
    """Reset conversation state for a specific phone number"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    await db.conversation_states.delete_one({"phone_number": phone_number})
    return {"message": f"Estado de conversación de {phone_number} reiniciado"}

# ============== PUBLIC CATALOG (NO AUTH) ==============

@api_router.get("/catalog/public")
async def public_catalog(q: str = "", category: str = "", limit: int = 40):
    """Public endpoint - no auth required. Returns filtered products for WhatsApp catalog links."""
    if not q.strip() and not category.strip():
        return []
    
    conditions = []
    if q.strip():
        words = q.strip().split()
        stems = set()
        for w in words:
            stems.add(re.escape(w))
            if w.endswith("es") and len(w) > 3:
                stems.add(re.escape(w[:-2]))
            if w.endswith("s") and len(w) > 2:
                stems.add(re.escape(w[:-1]))
        regex = "|".join(stems)
        conditions.append({"$or": [
            {"name": {"$regex": regex, "$options": "i"}},
            {"description": {"$regex": regex, "$options": "i"}},
            {"code": {"$regex": regex, "$options": "i"}},
            {"categories": {"$regex": regex, "$options": "i"}},
            {"category_1": {"$regex": regex, "$options": "i"}},
            {"category_2": {"$regex": regex, "$options": "i"}},
            {"category_3": {"$regex": regex, "$options": "i"}}
        ]})
    if category.strip():
        conditions.append({"categories": {"$regex": re.escape(category.strip()), "$options": "i"}})
    
    query_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0] if conditions else {}
    
    products = await db.products.find(
        query_filter,
        {"_id": 0, "code": 1, "name": 1, "description": 1, "image_url": 1, "price": 1, "categories": 1}
    ).limit(limit).to_list(limit)
    
    return products

@api_router.get("/catalog/public/categories")
async def public_catalog_categories():
    """Public endpoint - returns all product categories."""
    try:
        categories = await db.products.distinct("categories")
        return sorted([c for c in categories if c])
    except:
        return []

# ============== QUOTES MANAGEMENT ROUTES ==============

class QuoteResponse(BaseModel):
    id: str
    conversation_id: str
    phone_number: str
    status: str
    client_name: Optional[str]
    client_empresa: Optional[str]
    client_correo: Optional[str]
    client_ciudad: Optional[str]
    items: List[Dict[str, Any]]
    cantidad: Optional[str]
    fecha_entrega: Optional[str]
    personalizacion: Optional[str]
    necesita_diseno: Optional[str]
    total: float
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

def build_quote_response(q: dict) -> QuoteResponse:
    created_at = q.get("created_at")
    updated_at = q.get("updated_at", created_at)
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    return QuoteResponse(
        id=q["id"],
        conversation_id=q.get("conversation_id", ""),
        phone_number=q.get("phone_number", ""),
        status=q.get("status", "pending"),
        client_name=q.get("client_name"),
        client_empresa=q.get("client_empresa"),
        client_correo=q.get("client_correo"),
        client_ciudad=q.get("client_ciudad"),
        items=q.get("items", []),
        cantidad=q.get("cantidad"),
        fecha_entrega=q.get("fecha_entrega"),
        personalizacion=q.get("personalizacion"),
        necesita_diseno=q.get("necesita_diseno"),
        total=q.get("total", 0),
        notes=q.get("notes", ""),
        created_at=created_at,
        updated_at=updated_at
    )

@api_router.get("/quotes", response_model=List[QuoteResponse])
async def get_quotes(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    quotes = await db.quotes.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [build_quote_response(q) for q in quotes]

@api_router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    q = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    return build_quote_response(q)

class QuoteUpdate(BaseModel):
    total: Optional[float] = None
    notes: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None

@api_router.patch("/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(quote_id: str, data: QuoteUpdate, current_user: dict = Depends(get_current_user)):
    q = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.quotes.update_one({"id": quote_id}, {"$set": update})
    updated = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    return build_quote_response(updated)

@api_router.post("/quotes/{quote_id}/send")
async def send_quote_email(quote_id: str, current_user: dict = Depends(get_current_user)):
    """Send quote to client via email"""
    q = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    
    correo = q.get("client_correo")
    if not correo:
        raise HTTPException(status_code=400, detail="El cliente no tiene correo registrado")
    
    # Build email
    items_text = ""
    for item in q.get("items", []):
        items_text += f"- {item.get('code', '')} {item.get('product_name', 'Producto')}\n"
    
    body = f"""Estimado/a {q.get('client_name', 'Cliente')},

Gracias por su interes en Gimmicks Marketing Services.

Adjunto los detalles de su cotizacion:

Productos solicitados:
{items_text}
Cantidad: {q.get('cantidad', 'Por confirmar')}
Personalizacion: {q.get('personalizacion', 'N/A')}
Fecha de entrega: {q.get('fecha_entrega', 'Por confirmar')}
Total: ${q.get('total', 0):,.2f}

{q.get('notes', '')}

Quedamos atentos a su confirmacion.

Saludos cordiales,
Gimmicks Marketing Services
"""
    
    # Try SMTP
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", smtp_user)
    
    email_sent = False
    if smtp_host and smtp_user and smtp_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg["From"] = smtp_from
            msg["To"] = correo
            msg["Subject"] = f"Cotizacion Gimmicks - {q.get('client_name', '')}"
            msg.attach(MIMEText(body, "plain"))
            
            port = int(os.environ.get("SMTP_PORT", 587))
            server = smtplib.SMTP(smtp_host, port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            email_sent = True
            logger.info(f"Quote email sent to {correo}")
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise HTTPException(status_code=500, detail=f"Error enviando email: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="SMTP no configurado. Agrega SMTP_HOST, SMTP_USER, SMTP_PASSWORD en .env")
    
    # Update status
    await db.quotes.update_one(
        {"id": quote_id},
        {"$set": {"status": "sent", "sent_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Update lead stage
    await db.leads.update_one(
        {"phone_number": q["phone_number"]},
        {"$set": {"funnel_stage": "cotizacion_generada", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "quote_sent",
        "quote_id": quote_id,
        "sent_to": correo,
        "sent_by": current_user.get("email"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Cotizacion enviada a {correo}", "email_sent": email_sent}

@api_router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.quotes.delete_one({"id": quote_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    return {"message": "Cotizacion eliminada"}

# ============== FOLLOW-UP SYSTEM ==============

@api_router.post("/followup/check")
async def check_followups(current_user: dict = Depends(get_current_user)):
    """Manually trigger follow-up check for inactive conversations"""
    results = await run_followup_check()
    return results

async def run_followup_check():
    """Check for inactive conversations and send reminders or mark as lost"""
    now = datetime.now(timezone.utc)
    results = {"reminders_sent": 0, "marked_lost": 0, "reactivated": 0}
    
    states = await db.conversation_states.find(
        {"transferred_to_human": {"$ne": True}},
        {"_id": 0}
    ).to_list(500)
    
    for state in states:
        phone = state.get("phone_number")
        last_interaction = state.get("last_interaction")
        if not last_interaction:
            continue
        
        # Skip conversations that already generated a quote
        if state.get("quote_generated"):
            continue
        
        if isinstance(last_interaction, str):
            last_dt = datetime.fromisoformat(last_interaction.replace('Z', '+00:00'))
        else:
            last_dt = last_interaction
        
        hours_inactive = (now - last_dt).total_seconds() / 3600
        reminder_count = state.get("reminder_count", 0)
        
        # First reminder at 4 hours (only if no reminders sent yet)
        if 4 <= hours_inactive and reminder_count == 0:
            conv = await db.conversations.find_one({"phone_number": phone}, {"_id": 0, "id": 1})
            if conv:
                try:
                    await send_whatsapp_message(phone, "Hola, solo para saber si pudiste revisar la información que te envié. Si quieres te ayudo con la cotización.")
                    
                    now_iso = now.isoformat()
                    msg_doc = {
                        "id": str(uuid.uuid4()),
                        "conversation_id": conv["id"],
                        "phone_number": phone,
                        "sender": "business",
                        "message_type": "text",
                        "content": {"text": "Hola, solo para saber si pudiste revisar la información que te envié. Si quieres te ayudo con la cotización."},
                        "status": "sent",
                        "is_automated": True,
                        "is_followup": True,
                        "timestamp": now_iso
                    }
                    await db.messages.insert_one(msg_doc)
                    await db.conversation_states.update_one(
                        {"phone_number": phone},
                        {"$set": {"reminder_count": 1, "first_reminder_time": now_iso}}
                    )
                    results["reminders_sent"] += 1
                except Exception as e:
                    logger.error(f"Failed to send reminder to {phone}: {e}")
        
        # Second reminder 24 hours after first reminder
        elif reminder_count == 1:
            first_reminder_time = state.get("first_reminder_time")
            if first_reminder_time:
                if isinstance(first_reminder_time, str):
                    first_dt = datetime.fromisoformat(first_reminder_time.replace('Z', '+00:00'))
                else:
                    first_dt = first_reminder_time
                hours_since_first = (now - first_dt).total_seconds() / 3600
                if hours_since_first >= 24:
                    conv = await db.conversations.find_one({"phone_number": phone}, {"_id": 0, "id": 1})
                    if conv:
                        try:
                            await send_whatsapp_message(phone, "Hola de nuevo, quería saber si aún tienes interés en los productos. Estoy aquí para ayudarte cuando lo necesites.")
                            
                            now_iso = now.isoformat()
                            msg_doc = {
                                "id": str(uuid.uuid4()),
                                "conversation_id": conv["id"],
                                "phone_number": phone,
                                "sender": "business",
                                "message_type": "text",
                                "content": {"text": "Hola de nuevo, quería saber si aún tienes interés en los productos. Estoy aquí para ayudarte cuando lo necesites."},
                                "status": "sent",
                                "is_automated": True,
                                "is_followup": True,
                                "timestamp": now_iso
                            }
                            await db.messages.insert_one(msg_doc)
                            await db.conversation_states.update_one(
                                {"phone_number": phone},
                                {"$set": {"reminder_count": 2, "second_reminder_time": now_iso}}
                            )
                            results["reminders_sent"] += 1
                        except Exception as e:
                            logger.error(f"Failed to send 2nd reminder to {phone}: {e}")
        
        # Mark as lost 24 hours after second reminder
        elif reminder_count >= 2:
            second_reminder_time = state.get("second_reminder_time")
            if second_reminder_time:
                if isinstance(second_reminder_time, str):
                    second_dt = datetime.fromisoformat(second_reminder_time.replace('Z', '+00:00'))
                else:
                    second_dt = second_reminder_time
                hours_since_second = (now - second_dt).total_seconds() / 3600
                if hours_since_second >= 24:
                    lead = await db.leads.find_one({"phone_number": phone}, {"_id": 0})
                    if lead and lead.get("funnel_stage") not in ("perdido", "pedido", "cotizacion_generada"):
                        await db.leads.update_one(
                            {"phone_number": phone},
                            {"$set": {"funnel_stage": "perdido", "updated_at": now.isoformat()}}
                        )
                        await db.audit_logs.insert_one({
                            "id": str(uuid.uuid4()),
                            "action": "lead_marked_lost",
                            "phone_number": phone,
                            "reason": "no_response_after_2_reminders",
                            "timestamp": now.isoformat()
                        })
                        results["marked_lost"] += 1
    
    return results

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============== LEGAL PAGES ==============

@api_router.get("/privacy", include_in_schema=False)
async def privacy_policy():
    from fastapi.responses import HTMLResponse
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Política de Privacidad - Gimmicks CRM</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; line-height: 1.6; }
            h1 { color: #10b981; }
            h2 { color: #374151; margin-top: 30px; }
        </style>
    </head>
    <body>
        <h1>Política de Privacidad</h1>
        <p><strong>Última actualización:</strong> Febrero 2026</p>
        
        <h2>1. Información que Recopilamos</h2>
        <p>Gimmicks CRM recopila información proporcionada a través de WhatsApp Business, incluyendo números de teléfono, nombres y mensajes de conversación para gestionar la comunicación con clientes.</p>
        
        <h2>2. Uso de la Información</h2>
        <p>La información se utiliza exclusivamente para:</p>
        <ul>
            <li>Gestionar conversaciones con clientes</li>
            <li>Proporcionar soporte y seguimiento de ventas</li>
            <li>Mejorar nuestros servicios</li>
        </ul>
        
        <h2>3. Protección de Datos</h2>
        <p>Implementamos medidas de seguridad técnicas y organizativas para proteger su información personal.</p>
        
        <h2>4. Contacto</h2>
        <p>Para consultas sobre privacidad, contactar a: info@gimmicks.com</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@api_router.get("/terms", include_in_schema=False)
async def terms_of_service():
    from fastapi.responses import HTMLResponse
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Términos de Servicio - Gimmicks CRM</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; line-height: 1.6; }
            h1 { color: #10b981; }
            h2 { color: #374151; margin-top: 30px; }
        </style>
    </head>
    <body>
        <h1>Términos de Servicio</h1>
        <p><strong>Última actualización:</strong> Febrero 2026</p>
        
        <h2>1. Aceptación de Términos</h2>
        <p>Al utilizar Gimmicks CRM y sus servicios de WhatsApp Business, acepta estos términos de servicio.</p>
        
        <h2>2. Descripción del Servicio</h2>
        <p>Gimmicks CRM proporciona una plataforma de gestión de relaciones con clientes integrada con WhatsApp Business.</p>
        
        <h2>3. Uso Aceptable</h2>
        <p>El usuario se compromete a utilizar el servicio de manera responsable y conforme a las políticas de WhatsApp Business.</p>
        
        <h2>4. Contacto</h2>
        <p>Para consultas: info@gimmicks.com</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Include the router in the main app

# ============== ROOT PAGE (for Meta verification) ==============

@app.get("/", include_in_schema=False)
async def root_page():
    from fastapi.responses import HTMLResponse
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gimmicks CRM - WhatsApp Business</title>
        <meta name="description" content="Plataforma CRM integrada con WhatsApp Business para gestión de clientes y ventas.">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #09090b 0%, #18181b 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            .container {
                text-align: center;
                padding: 40px;
                max-width: 600px;
            }
            .logo {
                width: 120px;
                margin-bottom: 30px;
            }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 15px;
                color: #10b981;
            }
            p {
                font-size: 1.1rem;
                color: #a1a1aa;
                margin-bottom: 30px;
                line-height: 1.6;
            }
            .features {
                display: flex;
                gap: 20px;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 30px;
            }
            .feature {
                background: rgba(255,255,255,0.05);
                padding: 20px;
                border-radius: 12px;
                width: 150px;
            }
            .feature-icon {
                font-size: 2rem;
                margin-bottom: 10px;
            }
            .feature-text {
                font-size: 0.9rem;
                color: #d4d4d8;
            }
            .btn {
                display: inline-block;
                background: #10b981;
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 20px;
                transition: background 0.3s;
            }
            .btn:hover {
                background: #059669;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Gimmicks CRM</h1>
            <p>Plataforma de gestión de clientes integrada con WhatsApp Business. Centraliza tus conversaciones, automatiza respuestas y aumenta tus ventas.</p>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">💬</div>
                    <div class="feature-text">Chat en tiempo real</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <div class="feature-text">Respuestas automáticas</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <div class="feature-text">Seguimiento de leads</div>
                </div>
            </div>
            
            <a href="/api/privacy" class="btn">Política de Privacidad</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ============== PRODUCTION SYNC ROUTES ==============

@api_router.post("/sync/production")
async def trigger_production_sync(current_user: dict = Depends(get_current_user)):
    """Manually trigger a sync from production MongoDB"""
    from services.sync_service import sync_from_production
    result = await sync_from_production(db)
    return result

@api_router.get("/sync/status")
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """Get the status of the background sync task"""
    global _bg_sync
    if _bg_sync:
        return {
            "running": _bg_sync._task is not None and not _bg_sync._task.done(),
            "interval_seconds": _bg_sync.interval,
            "last_sync": _bg_sync.last_sync,
            "last_result": _bg_sync.last_result
        }
    return {"running": False, "last_sync": None}

_bg_sync = None

app.include_router(api_router)

# ============== PUBLIC CATALOG PAGE (HTML) ==============

LOGO_URL = "https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/ee7e6zy2_logo-gimmicks.png"

@app.get("/catalog", include_in_schema=False)
async def catalog_page(q: str = ""):
    from fastapi.responses import HTMLResponse
    import re as re_mod

    def fix_drive_url(url):
        """Convert Google Drive sharing URLs to direct image URLs"""
        if not url:
            return url
        # https://drive.google.com/file/d/FILE_ID/view...
        m = re_mod.search(r'drive\.google\.com/file/d/([^/]+)', url)
        if m:
            return f"https://lh3.googleusercontent.com/d/{m.group(1)}"
        # https://drive.google.com/open?id=FILE_ID
        m = re_mod.search(r'drive\.google\.com/open\?id=([^&]+)', url)
        if m:
            return f"https://lh3.googleusercontent.com/d/{m.group(1)}"
        # https://drive.google.com/uc?id=FILE_ID
        m = re_mod.search(r'drive\.google\.com/uc\?.*id=([^&]+)', url)
        if m:
            return f"https://lh3.googleusercontent.com/d/{m.group(1)}"
        return url

    products_html = ""
    count = 0
    if q.strip():
        words = q.strip().split()
        # Handle plurals/singulars: add stem without trailing 's/es'
        stems = set()
        for w in words:
            stems.add(w)
            if w.endswith("es") and len(w) > 3:
                stems.add(w[:-2])
            if w.endswith("s") and len(w) > 2:
                stems.add(w[:-1])
        regex = "|".join([re.escape(s) for s in stems])
        products = await db.products.find(
            {"$or": [
                {"name": {"$regex": regex, "$options": "i"}},
                {"description": {"$regex": regex, "$options": "i"}},
                {"code": {"$regex": regex, "$options": "i"}},
                {"category_1": {"$regex": regex, "$options": "i"}},
                {"category_2": {"$regex": regex, "$options": "i"}},
                {"category_3": {"$regex": regex, "$options": "i"}}
            ]},
            {"_id": 0, "code": 1, "name": 1, "description": 1, "image_url": 1}
        ).limit(40).to_list(40)
        count = len(products)
        for p in products:
            code = p.get("code", "")
            name = p.get("name", "")
            desc = p.get("description") or ""
            img = fix_drive_url(p.get("image_url") or "")
            img_html = f'<img src="{img}" alt="{name}" loading="lazy" onerror="this.parentElement.innerHTML=\'<div class=no-img>Sin imagen</div>\'">' if img and img != "N/A" else '<div class="no-img">Sin imagen</div>'
            desc_html = f'<p class="desc">{desc[:80]}</p>' if desc else ""
            products_html += f'''<div class="card">
                <div class="img">{img_html}</div>
                <div class="info">
                    <p class="name">{name}</p>
                    {desc_html}
                    <div class="code-row">
                        <span class="code">{code}</span>
                        <button onclick="copyCode(this,'{code}')" class="copy-btn">Copiar c\u00f3digo</button>
                    </div>
                </div>
            </div>'''

    results_text = f'{count} producto(s) para "{q}"' if q else ""
    grid_html = f"<div class='grid'>{products_html}</div>" if products_html else "<div class='empty'><p>" + ("No se encontraron productos" if q else "Busca un producto para ver opciones") + "</p></div>"
    footer_html = "<div class='footer'>Comparte los códigos de los productos que te interesen con tu asesor por WhatsApp</div>" if products_html else ""

    css = """*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#fff;color:#222}
    header{background:#1a2332;padding:14px 16px;position:sticky;top:0;z-index:10}header img{height:40px}
    .wrap{max-width:1100px;margin:0 auto;padding:20px 16px}
    .search{display:block;width:100%;max-width:400px;margin:0 auto 16px;padding:12px 16px;border:1px solid #ddd;border-radius:12px;font-size:14px;outline:none}
    .search:focus{border-color:#7BA899;box-shadow:0 0 0 2px rgba(123,168,153,0.2)}
    .info-text{text-align:center;color:#888;font-size:13px;margin-bottom:16px}
    .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
    @media(min-width:640px){.grid{grid-template-columns:repeat(3,1fr)}}
    @media(min-width:900px){.grid{grid-template-columns:repeat(4,1fr)}}
    .card{border:1px solid #f0f0f0;border-radius:12px;overflow:hidden;transition:box-shadow .2s}.card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.08)}
    .img{aspect-ratio:1;background:#fafafa;display:flex;align-items:center;justify-content:center;overflow:hidden}
    .img img{width:100%;height:100%;object-fit:contain;padding:8px}.no-img{color:#ccc;font-size:13px}
    .info{padding:10px}.name{font-weight:600;font-size:13px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
    .desc{font-size:11px;color:#888;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
    .code-row{display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap}
    .code{background:rgba(123,168,153,0.1);color:#7BA899;padding:4px 8px;border-radius:6px;font-size:11px;font-weight:700;font-family:monospace}
    .copy-btn{padding:4px 10px;border:1px solid #ddd;border-radius:8px;font-size:11px;cursor:pointer;background:#fff;color:#555;transition:all .2s}
    .copy-btn:hover{background:rgba(123,168,153,0.1);color:#7BA899;border-color:#7BA899}
    .copy-btn.copied{background:#e8f5e9;color:#2e7d32;border-color:#a5d6a7}
    .footer{text-align:center;margin-top:30px;padding:16px;border-top:1px solid #f0f0f0;color:#888;font-size:13px}
    .empty{text-align:center;padding:60px 20px;color:#aaa}.empty p{font-size:16px}"""

    js = """function copyCode(btn,code){navigator.clipboard.writeText(code);btn.textContent="Copiado";btn.classList.add("copied");setTimeout(function(){btn.textContent="Copiar código";btn.classList.remove("copied")},1500)}"""

    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Catalogo Gimmicks</title>'
        '<style>' + css + '</style></head><body>'
        '<header><img src="' + LOGO_URL + '" alt="Gimmicks"></header>'
        '<div class="wrap">'
        '<form method="get" action="/catalog"><input class="search" type="text" name="q" value="' + q + '" placeholder="Buscar productos..."></form>'
        '<p class="info-text">' + results_text + '</p>'
        + grid_html + footer_html +
        '</div><script>' + js + '</script></body></html>'
    )
    return HTMLResponse(content=html)

# Background follow-up task
import asyncio

async def followup_background_task():
    """Run follow-up check every 30 minutes"""
    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutes
            result = await run_followup_check()
            if result["reminders_sent"] > 0 or result["marked_lost"] > 0:
                logger.info(f"Follow-up check: {result}")
        except Exception as e:
            logger.error(f"Follow-up task error: {e}")

@app.on_event("startup")
async def start_followup_task():
    asyncio.create_task(followup_background_task())
    await seed_system_automation_rules()
    # Start background sync from production
    from services.sync_service import BackgroundSyncTask
    global _bg_sync
    _bg_sync = BackgroundSyncTask(db, interval_seconds=120)
    _bg_sync.start()


async def seed_system_automation_rules():
    """Seed all system automation rules on startup if they don't exist"""
    system_rules = [
        {
            "name": "Bienvenida automática",
            "trigger_type": "new_lead",
            "trigger_value": None,
            "action_type": "ai_response",
            "action_value": "Saluda al cliente, preséntate como Ana de Gimmicks y pregunta en qué puedes ayudar.",
            "is_active": True
        },
        {
            "name": "Envío de catálogo",
            "trigger_type": "ai_intent",
            "trigger_value": "solicitud_catalogo",
            "action_type": "ai_response",
            "action_value": "Cuando el cliente mencione un tipo de producto (jarros, termos, gorras, etc.), envía automáticamente el link del catálogo público filtrado por ese producto.",
            "is_active": True
        },
        {
            "name": "Recopilación de datos",
            "trigger_type": "ai_intent",
            "trigger_value": "cotizacion_directa",
            "action_type": "ai_response",
            "action_value": "Recopila datos del cliente UNO a la vez en este orden: cantidad, personalización, correo, nombre/empresa, ciudad/fecha. No repitas datos ya proporcionados.",
            "is_active": True
        },
        {
            "name": "Generación de cotización",
            "trigger_type": "ai_intent",
            "trigger_value": "datos_completos",
            "action_type": "ai_response",
            "action_value": "Cuando se tengan producto/códigos + cantidad + correo, genera automáticamente una cotización pendiente para revisión del admin.",
            "is_active": True
        },
        {
            "name": "Primer recordatorio (4 horas)",
            "trigger_type": "no_response",
            "trigger_value": "4",
            "action_type": "send_message",
            "action_value": "Hola, solo para saber si pudiste revisar la información que te envié. Si quieres te ayudo con la cotización.",
            "is_active": True
        },
        {
            "name": "Segundo recordatorio (24 horas)",
            "trigger_type": "no_response",
            "trigger_value": "24",
            "action_type": "send_message",
            "action_value": "Hola de nuevo, quería saber si aún tienes interés en los productos. Estoy aquí para ayudarte cuando lo necesites.",
            "is_active": True
        },
        {
            "name": "Marcar como perdido",
            "trigger_type": "no_response",
            "trigger_value": "48",
            "action_type": "change_stage",
            "action_value": "perdido",
            "is_active": True
        },
        {
            "name": "Reanudar conversación (12h inactiva)",
            "trigger_type": "no_response",
            "trigger_value": "12",
            "action_type": "ai_response",
            "action_value": "Si la conversación estuvo inactiva 12+ horas y tenía datos pendientes, pregunta al cliente si quiere retomar donde quedó o empezar una nueva consulta.",
            "is_active": True
        },
        {
            "name": "Transferir a humano",
            "trigger_type": "ai_intent",
            "trigger_value": "queja,problema,reclamo",
            "action_type": "assign_agent",
            "action_value": "Transfiere la conversación a un asesor humano cuando el bot detecta una queja, problema complejo o solicitud explícita de hablar con una persona.",
            "is_active": True
        },
        {
            "name": "Respuesta a consulta de precios",
            "trigger_type": "keyword",
            "trigger_value": "precio,costo,cuánto,cotización",
            "action_type": "ai_response",
            "action_value": "Cuando el cliente pregunte por precios, guíalo hacia la cotización: pregunta qué producto necesita y en qué cantidad para poder generar una cotización personalizada.",
            "is_active": True
        },
    ]
    now = datetime.now(timezone.utc)
    created = 0
    for rule in system_rules:
        existing = await db.automation_rules.find_one({"name": rule["name"]})
        if not existing:
            rule["id"] = str(uuid.uuid4())
            rule["created_at"] = now.isoformat()
            await db.automation_rules.insert_one(rule)
            created += 1
    if created:
        logger.info(f"Seeded {created} system automation rules")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# Serve uploaded product images
from fastapi.staticfiles import StaticFiles
uploads_dir = ROOT_DIR / "uploads" / "products"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads/products", StaticFiles(directory=str(uploads_dir)), name="product_uploads")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
