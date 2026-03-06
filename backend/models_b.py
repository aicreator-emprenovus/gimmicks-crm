from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    supplier_code: str = ""
    name: str
    description: str = ""
    stock: int = 0
    price: float = 0.0
    cost: float = 0.0
    supplier: str = ""
    image_url: str = ""
    categories: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    code: str
    supplier_code: str = ""
    name: str
    description: str = ""
    stock: int = 0
    price: float = 0.0
    cost: float = 0.0
    supplier: str = ""
    image_url: str = ""
    categories: List[str] = []


class QuoteItem(BaseModel):
    item_id: str = ""
    product_id: str = ""
    code: str = ""
    name: str = ""
    description: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    image_url: str = ""
    categories: List[str] = []
    selected_characteristics: List[str] = []
    discount_amount: float = 0.0
    discount_type: str = "$"
    additional_amount: float = 0.0
    additional_type: str = "$"
    otros: str = ""


class Quote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: str = "QUOTE"
    quote_number: str = ""
    client_id: str = ""
    client_name: str = ""
    client_contact: str = ""
    client_email: str = ""
    factura: str = ""
    items: List[QuoteItem] = []
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    status: str = "draft"
    payment_terms: str = "50% anticipo, 50% contra entrega"
    validity: str = "8 días"
    delivery_time: str = "Por confirmar"
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_by_id: str = ""
    created_by_name: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    commercial_email: str = ""
    phone: str = ""
    contact_person: str = ""
    address: str = ""
    city: str = ""
    tax_id: str = ""
    sector: str = ""
    sector_details: str = ""
    notes: str = ""
    source: str = "manual"
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClientActivity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    action: str
    details: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
