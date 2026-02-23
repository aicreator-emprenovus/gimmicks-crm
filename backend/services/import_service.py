"""
Import service for uploading Excel files (clients, quotes, purchase orders).
Handles duplicate detection and only inserts new records.
"""
import uuid
import io
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
import openpyxl


async def import_clients(file: UploadFile, db) -> dict:
    """Import clients from xlsx. Duplicates detected by email or phone."""
    wb = openpyxl.load_workbook(io.BytesIO(await file.read()))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]

    col_map = {}
    mapping = {
        "empresa / nombre": "name", "nombre": "name", "empresa": "name",
        "contacto": "contact_person",
        "email": "email", "correo": "email",
        "email comercial": "commercial_email",
        "teléfono": "phone", "telefono": "phone",
        "ciudad": "city",
        "dirección": "address", "direccion": "address",
        "ruc / ci": "tax_id", "ruc": "tax_id", "ci": "tax_id",
        "sector": "sector",
        "notas": "notes",
    }
    for i, h in enumerate(headers):
        if h:
            key = h.strip().lower()
            if key in mapping:
                col_map[i] = mapping[key]

    inserted = 0
    skipped = 0
    errors = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        data = {}
        for i, val in enumerate(row):
            if i in col_map and val is not None:
                data[col_map[i]] = str(val).strip()

        if not data.get("name"):
            continue

        email = data.get("email", "")
        phone = data.get("phone", "")

        # Duplicate check
        is_dup = False
        if email:
            existing = await db.clients.find_one({"email": email, "is_deleted": False})
            if existing:
                is_dup = True
        if not is_dup and phone:
            clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            existing = await db.clients.find_one({"phone": {"$regex": clean_phone[-8:]}, "is_deleted": False})
            if existing:
                is_dup = True

        if is_dup:
            skipped += 1
            continue

        client = {
            "id": str(uuid.uuid4()),
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "commercial_email": data.get("commercial_email", ""),
            "phone": data.get("phone", ""),
            "contact_person": data.get("contact_person", ""),
            "address": data.get("address", ""),
            "city": data.get("city", ""),
            "tax_id": data.get("tax_id", ""),
            "sector": data.get("sector", ""),
            "sector_details": "",
            "notes": data.get("notes", ""),
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "manual"
        }
        await db.clients.insert_one(client)
        inserted += 1

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


async def import_quotes(file: UploadFile, db, doc_type: str = "QUOTE", user: dict = None) -> dict:
    """Import quotes/POs from xlsx. Duplicates detected by quote_number."""
    wb = openpyxl.load_workbook(io.BytesIO(await file.read()))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]

    col_map = {}
    mapping = {
        "número": "quote_number", "numero": "quote_number", "nro": "quote_number",
        "no. cotización": "quote_number", "no. orden": "quote_number",
        "cliente": "client_name",
        "contacto": "client_contact",
        "email cliente": "client_email", "email": "client_email",
        "producto": "product_name", "código": "product_code", "codigo": "product_code",
        "descripción": "description", "descripcion": "description",
        "cantidad": "quantity", "cant": "quantity",
        "precio unitario": "unit_price", "precio": "unit_price",
        "total": "total_price",
        "condiciones de pago": "payment_terms", "pago": "payment_terms",
        "validez": "validity",
        "tiempo de entrega": "delivery_time", "entrega": "delivery_time",
        "estado": "status",
    }
    for i, h in enumerate(headers):
        if h:
            key = h.strip().lower()
            if key in mapping:
                col_map[i] = mapping[key]

    # Group rows by quote_number (multi-line quotes)
    quotes_data = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        data = {}
        for i, val in enumerate(row):
            if i in col_map and val is not None:
                data[col_map[i]] = str(val).strip() if not isinstance(val, (int, float)) else val

        qnum = str(data.get("quote_number", "")).strip()
        if not qnum:
            continue

        if qnum not in quotes_data:
            quotes_data[qnum] = {"info": data, "items": []}

        if data.get("product_name") or data.get("product_code"):
            try:
                qty = float(data.get("quantity", 0) or 0)
                price = float(data.get("unit_price", 0) or 0)
            except (ValueError, TypeError):
                qty = 0
                price = 0
            quotes_data[qnum]["items"].append({
                "item_id": str(uuid.uuid4()),
                "product_id": "",
                "code": str(data.get("product_code", "")),
                "name": str(data.get("product_name", "")),
                "description": str(data.get("description", "")),
                "quantity": qty,
                "unit_price": price,
                "total_price": qty * price,
                "image_url": "",
                "categories": [],
                "discount_amount": 0,
                "discount_type": "none",
                "additional_amount": 0,
                "additional_type": "none",
                "otros": ""
            })

    inserted = 0
    skipped = 0

    counter_key = "po_counter" if doc_type == "PO" else "quote_counter"

    for qnum, qdata in quotes_data.items():
        # Duplicate check by quote_number
        existing = await db.quotes_v2.find_one({"quote_number": qnum, "is_deleted": False})
        if existing:
            skipped += 1
            continue

        info = qdata["info"]
        items = qdata["items"]
        subtotal = sum(it["total_price"] for it in items)
        tax = subtotal * 0.15
        total = subtotal + tax

        quote = {
            "id": str(uuid.uuid4()),
            "doc_type": doc_type,
            "quote_number": qnum,
            "client_id": "",
            "client_name": str(info.get("client_name", "")),
            "client_contact": str(info.get("client_contact", "")),
            "client_email": str(info.get("client_email", "")),
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "status": str(info.get("status", "draft")).lower() if info.get("status") else "draft",
            "payment_terms": str(info.get("payment_terms", "")),
            "validity": str(info.get("validity", "15 días")),
            "delivery_time": str(info.get("delivery_time", "")),
            "is_deleted": False,
            "deleted_at": None,
            "created_by_id": user.get("id", "") if user else "",
            "created_by_name": user.get("name", "") if user else "",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quotes_v2.insert_one(quote)
        inserted += 1

    return {"inserted": inserted, "skipped": skipped}
