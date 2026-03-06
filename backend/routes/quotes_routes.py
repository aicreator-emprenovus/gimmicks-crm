from fastapi import APIRouter, HTTPException, Body, BackgroundTasks, Header
from typing import List, Optional
from models_b import Quote
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors
import io
import base64
from datetime import datetime, timezone
from bson import ObjectId
import requests
import re
import uuid
import jwt
import os
from services.email_service import send_po_email

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
            if not user:
                user = await db.users.find_one({"_id": user_id})
            if user:
                name = user.get("name", "")
                if not name:
                    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                return {
                    "id": user.get("id", user.get("_id")),
                    "name": name,
                    "email": user.get("email", ""),
                    "role": user.get("role", "asesor")
                }
    except Exception:
        pass
    return None

async def log_client_activity(client_id: str, action: str, details: str):
    if not client_id:
        return
    activity = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": action,
        "details": details,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.client_activities.insert_one(activity)

async def log_document_activity(document_id: str, document_number: str, document_type: str, action: str, user: dict, details: str = None):
    if not user:
        return
    activity = {
        "_id": str(uuid.uuid4()),
        "document_id": document_id,
        "document_number": document_number,
        "document_type": document_type,
        "action": action,
        "user_id": user.get("id", ""),
        "user_name": user.get("name", ""),
        "user_email": user.get("email", ""),
        "details": details,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.document_activities.insert_one(activity)

async def get_next_po_number():
    """Get next purchase order number from independent sequence starting at 4712"""
    existing = await db.counters.find_one({"_id": "po_number"})
    if not existing:
        await db.counters.insert_one({"_id": "po_number", "seq": 4711})
    result = await db.counters.find_one_and_update(
        {"_id": "po_number"},
        {"$inc": {"seq": 1}},
        return_document=True
    )
    return str(result["seq"])

@router.post("/", response_model=Quote)
async def create_quote(quote: Quote, authorization: str = Header(None)):
    if quote.doc_type == "PO":
        quote.quote_number = await get_next_po_number()
    else:
        count = await db.quotes_v2.count_documents({"doc_type": {"$ne": "PO"}})
        quote.quote_number = str(4698 + count)
    if not quote.doc_type:
        quote.doc_type = "QUOTE"
    user = await get_user_from_token(authorization)
    if user:
        quote.created_by_id = user["id"]
        quote.created_by_name = user["name"]
    await db.quotes_v2.insert_one(quote.model_dump())
    action_type = "Orden de Compra" if quote.doc_type == "PO" else "Cotización"
    await log_client_activity(quote.client_id, "quote_created", f"{action_type} generada #{quote.quote_number}")
    await log_document_activity(quote.id, quote.quote_number, quote.doc_type, "created", user, f"Creado para {quote.client_name}")
    return quote

@router.get("/activities/all")
async def get_all_activities(limit: int = 100, authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")
    activities = await db.document_activities.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return activities

@router.get("/", response_model=List[Quote])
async def get_quotes(trash: bool = False, doc_type: str = "QUOTE"):
    query = {"is_deleted": trash, "doc_type": doc_type}
    quotes = await db.quotes_v2.find(query).sort("created_at", -1).to_list(1000)
    for quote in quotes:
        if '_id' in quote and hasattr(quote['_id'], '__str__'):
            quote['_id'] = str(quote['_id'])
    return quotes

@router.get("/{id}", response_model=Quote)
async def get_quote_by_id(id: str):
    quote_data = await db.quotes_v2.find_one({"id": id})
    if not quote_data:
        try:
            quote_data = await db.quotes_v2.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
    if not quote_data:
        raise HTTPException(status_code=404, detail="Quote not found")
    if '_id' in quote_data:
        quote_data['id'] = str(quote_data['_id'])
        del quote_data['_id']
    return Quote(**quote_data)

@router.put("/{id}", response_model=Quote)
async def update_quote(id: str, quote: Quote, authorization: str = Header(None)):
    query = {"id": id}
    existing = await db.quotes_v2.find_one(query)
    if not existing:
        try:
            query = {"_id": ObjectId(id)}
            existing = await db.quotes_v2.find_one(query)
        except Exception:
            pass
    if not existing:
        raise HTTPException(status_code=404, detail="Quote not found")
    user = await get_user_from_token(authorization)
    if not quote.quote_number:
        quote.quote_number = existing.get('quote_number')
    quote_dict = quote.model_dump()
    if '_id' in quote_dict:
        del quote_dict['_id']
    await db.quotes_v2.update_one(query, {"$set": quote_dict})
    action_type = "Orden de Compra" if quote.doc_type == "PO" else "Cotización"
    await log_client_activity(quote.client_id, "quote_updated", f"{action_type} actualizada #{quote.quote_number}")
    await log_document_activity(id, quote.quote_number, quote.doc_type, "edited", user, f"Editado - Cliente: {quote.client_name}")
    return quote

@router.delete("/{id}")
async def delete_quote(id: str, permanent: bool = False, authorization: str = Header(None)):
    user = await get_user_from_token(authorization)
    if user.get("role") not in ("admin", "desarrollador"):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar")
    query = {"id": id}
    existing = await db.quotes_v2.find_one(query)
    if not existing:
        try:
            query = {"_id": ObjectId(id)}
            existing = await db.quotes_v2.find_one(query)
        except Exception:
            pass
    if not existing:
        raise HTTPException(status_code=404, detail="Quote not found")
    user = await get_user_from_token(authorization)
    doc_number = existing.get("quote_number", "")
    doc_type = existing.get("doc_type", "QUOTE")
    if permanent:
        await db.quotes_v2.delete_one(query)
        await log_document_activity(id, doc_number, doc_type, "deleted_permanent", user, "Eliminado permanentemente")
        return {"message": "Quote permanently deleted"}
    else:
        await db.quotes_v2.update_one(query, {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}})
        await log_document_activity(id, doc_number, doc_type, "deleted", user, "Movido a papelera")
        return {"message": "Quote moved to trash"}

@router.post("/{id}/restore")
async def restore_quote(id: str, authorization: str = Header(None)):
    query = {"id": id}
    existing = await db.quotes_v2.find_one(query)
    if not existing:
        try:
            query = {"_id": ObjectId(id)}
            existing = await db.quotes_v2.find_one(query)
        except Exception:
            pass
    if not existing:
        raise HTTPException(status_code=404, detail="Quote not found")
    user = await get_user_from_token(authorization)
    await db.quotes_v2.update_one(query, {"$set": {"is_deleted": False, "deleted_at": None}})
    doc_number = existing.get("quote_number", "")
    doc_type = existing.get("doc_type", "QUOTE")
    await log_document_activity(id, doc_number, doc_type, "restored", user, "Restaurado de papelera")
    return {"message": "Quote restored"}

def format_currency_ecuador(value):
    if value is None or value == 0:
        return '$0,00'
    formatted = f"{value:.2f}"
    int_part, dec_part = formatted.split('.')
    int_with_sep = ''
    for i, digit in enumerate(reversed(int_part)):
        if i > 0 and i % 3 == 0:
            int_with_sep = '.' + int_with_sep
        int_with_sep = digit + int_with_sep
    return f'${int_with_sep},{dec_part}'

def fetch_image(url, width_cm=None):
    try:
        if not url:
            return None
        img_data = None
        if url.startswith("data:image"):
            try:
                header, encoded = url.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                img_data = io.BytesIO(img_bytes)
            except Exception:
                return None
        elif url.startswith("/api/uploads/") or url.startswith("/uploads/"):
            filename = url.split("/products/")[-1] if "/products/" in url else ""
            possible_paths = [
                f"/app/backend/uploads/products/{filename}",
                f"/app/frontend/public/uploads/products/{filename}",
            ]
            if url.startswith("/api/uploads/"):
                possible_paths.insert(0, f"/app/backend/{url.replace('/api/', '')}")
            for path in possible_paths:
                if path and os.path.exists(path):
                    with open(path, 'rb') as f:
                        img_data = io.BytesIO(f.read())
                    break
            if not img_data:
                try:
                    api_path = url if url.startswith("/api/") else f"/api{url}"
                    local_url = f"http://localhost:8001{api_path}"
                    resp = requests.get(local_url, timeout=5)
                    if resp.status_code == 200:
                        img_data = io.BytesIO(resp.content)
                except Exception:
                    pass
        else:
            drive_match = re.search(r'drive\.google\.com/file/d/([^/\?]+)', url)
            if drive_match:
                file_id = drive_match.group(1)
                url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'svg' in content_type or url.endswith('.svg'):
                    return None
                img_data = io.BytesIO(response.content)
            else:
                return None
        if img_data:
            try:
                utils = ImageReader(img_data)
                iw, ih = utils.getSize()
                aspect = ih / float(iw)
                target_width = width_cm if width_cm else 2.5*cm
                target_height = target_width * aspect
                img = Image(img_data, width=target_width, height=target_height)
                img.hAlign = 'RIGHT'
                return img
            except Exception:
                return None
    except Exception:
        return None
    return None

def _generate_pdf_bytes(quote: Quote, is_po: bool = False, client_data: dict = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_normal.fontSize = 9
    style_bold = ParagraphStyle("Bold", parent=style_normal, fontName="Helvetica-Bold")
    effective_is_po = is_po or (quote.doc_type == "PO")
    if effective_is_po:
        logo_url = "https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/x43p1zgk_image.png"
        title_text = f"<b>ORDEN DE COMPRA No. {quote.quote_number or '---'}</b>"
    else:
        logo_url = "https://customer-assets.emergentagent.com/job_quote-crafter-1/artifacts/5cvzat7e_image.png"
        title_text = f"<b>PROFORMA No. {quote.quote_number or '---'}</b>"
    logo = fetch_image(logo_url, width_cm=4*cm)
    months = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
    day = quote.created_at.day
    month = months[quote.created_at.month]
    year = quote.created_at.year

    if effective_is_po and client_data:
        # PO header format with client details
        style_title_center = ParagraphStyle("TitleCenter", parent=styles["Heading1"], fontSize=12, alignment=TA_CENTER)
        style_subtitle = ParagraphStyle("Subtitle", parent=style_bold, fontSize=11, alignment=TA_CENTER)
        style_field_label = ParagraphStyle("FieldLabel", parent=style_bold, fontSize=9)
        style_field_value = ParagraphStyle("FieldValue", parent=style_normal, fontSize=9)
        if logo:
            elements.append(logo)
            elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(title_text, style_title_center))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>CONTRATO DE TRABAJO</b>", style_subtitle))
        elements.append(Spacer(1, 0.8*cm))
        date_str = f"{day} {month.lower()} {year}"
        c_name = quote.client_name or ""
        c_address = client_data.get("address", "")
        c_contact = client_data.get("contact_person", "") or quote.client_contact or ""
        c_ruc = client_data.get("tax_id", "")
        c_phone = client_data.get("phone", "")
        c_email = client_data.get("email", "") or quote.client_email or ""
        c_factura = quote.factura or ""
        info_data = [
            [Paragraph("<b>FECHA:</b>", style_field_label), Paragraph(date_str, style_field_value),
             Paragraph("<b>ORDEN DE</b><br/><b>COMPRA</b><br/><b>CLIENTE:</b>", style_field_label), Paragraph(c_name, style_field_value)],
            [Paragraph("<b>CLIENTE:</b>", style_field_label), Paragraph(c_name, style_field_value),
             Paragraph("<b>FACTURA:</b>", style_field_label), Paragraph(c_factura, style_field_value)],
            [Paragraph("<b>DIRECCION:</b>", style_field_label), Paragraph(c_address, style_field_value),
             Paragraph("<b>TELEFONO:</b>", style_field_label), Paragraph(c_phone, style_field_value)],
            [Paragraph("<b>SOLICITADO POR:</b>", style_field_label), Paragraph(c_contact, style_field_value),
             Paragraph("<b>CORREO:</b>", style_field_label), Paragraph(c_email, style_field_value)],
            [Paragraph("<b>RUC:</b>", style_field_label), Paragraph(c_ruc, style_field_value),
             Paragraph("", style_field_label), Paragraph("", style_field_value)],
        ]
        info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))
        style_normal_large = ParagraphStyle("NormalLarge", parent=style_normal, fontSize=11)
        elements.append(Paragraph("Detalle de la Orden de Compra:", style_normal_large))
        elements.append(Spacer(1, 0.5*cm))
    else:
        date_str = f"Quito, {day} de {month} de {year}"
        style_title_right = ParagraphStyle("TitleRight", parent=styles["Heading1"], fontSize=10, alignment=TA_RIGHT)
        right_col_content = [Paragraph(title_text, style_title_right)]
        if logo:
            right_col_content.append(logo)
        header_data = [[Paragraph(date_str, style_normal), right_col_content]]
        header_table = Table(header_data, colWidths=[9*cm, 9*cm])
        header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(0,0),(0,0),'LEFT'),('ALIGN',(1,0),(1,0),'RIGHT')]))
        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))
        style_client_header = ParagraphStyle("ClientHeader", parent=style_bold, textColor=colors.HexColor('#64AF9C'), fontSize=11)
        style_normal_large = ParagraphStyle("NormalLarge", parent=style_normal, fontSize=11)
        elements.append(Paragraph("Señores", style_client_header))
        elements.append(Paragraph(f"<b>{quote.client_name.upper()}</b>", style_bold))
        if quote.client_contact:
            elements.append(Paragraph(f"Att: {quote.client_contact}", style_normal))
        elements.append(Paragraph("Presente.-", style_normal_large))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("De nuestra consideración:", style_normal_large))
        elements.append(Paragraph("Por medio de la presente pongo a su consideración la siguiente proforma:", style_normal_large))
        elements.append(Spacer(1, 0.5*cm))
    table_headers = ['CÓDIGO', 'CANTIDAD', 'DESCRIPCIÓN', 'VALOR\nUNITARIO', 'VALOR\nTOTAL', 'IMAGEN']
    table_data = [table_headers]
    for item in quote.items:
        p_img = fetch_image(item.image_url, width_cm=2.5*cm)
        desc_parts = [f"<b>{item.name}</b>", item.description]
        # Show manually selected characteristics (not auto-filled from inventory)
        sel_chars = getattr(item, 'selected_characteristics', None) or []
        if sel_chars:
            chars_text = ", ".join(sel_chars)
            desc_parts.append(f"<i>Características: {chars_text}</i>")
        if item.otros and item.additional_amount > 0:
            if item.additional_type == '%':
                desc_parts.append(f"<font color='green'>Valor adicional ({item.otros}): {item.additional_amount}%</font>")
            else:
                desc_parts.append(f"<font color='green'>Valor adicional ({item.otros}): {format_currency_ecuador(item.additional_amount)}</font>")
        elif item.additional_amount > 0:
            if item.additional_type == '%':
                desc_parts.append(f"<font color='green'>Valor adicional: {item.additional_amount}%</font>")
            else:
                desc_parts.append(f"<font color='green'>Valor adicional: {format_currency_ecuador(item.additional_amount)}</font>")
        elif item.otros:
            desc_parts.append(f"<i>Otros: {item.otros}</i>")
        desc_text = "<br/>".join(desc_parts)
        discount_text = ""
        if item.discount_amount > 0:
            if item.discount_type == '%':
                discount_text = f"<br/><font color='red'>Descuento: {item.discount_amount}%</font>"
            else:
                discount_text = f"<br/><font color='red'>Descuento: {format_currency_ecuador(item.discount_amount)}</font>"
        row = [
            Paragraph(item.code, style_normal),
            str(item.quantity),
            Paragraph(desc_text + discount_text, style_normal),
            format_currency_ecuador(item.unit_price),
            format_currency_ecuador(item.total_price),
            p_img if p_img else Paragraph("(No Image)", style_normal)
        ]
        table_data.append(row)
    col_widths = [2.5*cm, 2*cm, 6*cm, 2.5*cm, 2.5*cm, 3*cm]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,-1),'CENTER'),('ALIGN',(2,1),(2,-1),'LEFT'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),0.5,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F0F0F0')),('FONTSIZE',(0,0),(-1,-1),8)]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    style_total = ParagraphStyle("TotalStyle", parent=style_normal, textColor=colors.black, fontName="Helvetica", alignment=TA_RIGHT)
    total_data = [
        ["", "Subtotal:", format_currency_ecuador(quote.subtotal)],
        ["", "IVA 15%:", format_currency_ecuador(quote.tax)],
        ["", Paragraph("<b>TOTAL:</b>", style_total), Paragraph(format_currency_ecuador(quote.total), style_total)]
    ]
    total_table = Table(total_data, colWidths=[13*cm, 3*cm, 2.5*cm])
    total_table.setStyle(TableStyle([('ALIGN',(1,0),(2,-1),'RIGHT'),('GRID',(1,0),(2,-1),0.5,colors.black)]))
    elements.append(total_table)
    elements.append(Spacer(1, 1*cm))
    obs_style = ParagraphStyle('Obs', parent=style_normal, leading=12)
    elements.append(Paragraph("<b>OBSERVACIONES</b>", style_bold))
    elements.append(Paragraph(f"<b>FORMA DE PAGO:</b> {quote.payment_terms}", obs_style))
    elements.append(Paragraph(f"<b>VALIDEZ DE LA OFERTA:</b> {quote.validity}", obs_style))
    elements.append(Paragraph(f"<b>TIEMPO DE ENTREGA:</b> {quote.delivery_time}", obs_style))
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("Atentamente,", style_normal))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("<b>Ana María Burbano</b>", style_bold))
    elements.append(Paragraph("GERENTE", style_normal))
    doc.build(elements)
    return buffer.getvalue()

@router.post("/{id}/generate-pdf")
async def generate_pdf(id: str, doc_type: str = "PROFORMA", factura: str = ""):
    quote_data = await db.quotes_v2.find_one({"id": id}, {"_id": 0})
    if not quote_data:
        try:
            quote_data = await db.quotes_v2.find_one({"_id": ObjectId(id)})
            if quote_data:
                quote_data['id'] = str(quote_data['_id'])
                del quote_data['_id']
        except Exception:
            pass
    if not quote_data:
        raise HTTPException(status_code=404, detail="Quote not found")
    if factura:
        quote_data['factura'] = factura
        await db.quotes_v2.update_one({"id": id}, {"$set": {"factura": factura}})
    quote = Quote(**quote_data)
    is_po = (doc_type == "ORDEN_COMPRA") or (quote.doc_type == "PO")
    client_data = None
    if is_po and quote.client_id:
        client_data = await db.clients.find_one({"id": quote.client_id}, {"_id": 0})
    pdf_bytes = _generate_pdf_bytes(quote, is_po=is_po, client_data=client_data)
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    prefix = "ORDEN_COMPRA" if is_po else "PROFORMA"
    filename = f"{prefix}_{quote.quote_number}.pdf"
    return {"pdf_base64": pdf_base64, "filename": filename}

@router.post("/{id}/convert-to-po")
async def convert_to_po(id: str):
    quote_data = await db.quotes_v2.find_one({"id": id})
    if not quote_data:
        try:
            quote_data = await db.quotes_v2.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
    if not quote_data:
        raise HTTPException(status_code=404, detail="Quote not found")
    po_data = quote_data.copy()
    if '_id' in po_data:
        del po_data['_id']
    po_data['id'] = str(uuid.uuid4())
    po_data['doc_type'] = "PO"
    po_data['status'] = "orden_compra"
    po_data['created_at'] = datetime.now(timezone.utc)
    po_data['source_quote_number'] = quote_data.get('quote_number')
    po_data['quote_number'] = await get_next_po_number()
    await db.quotes_v2.insert_one(po_data)
    await log_client_activity(po_data['client_id'], "po_generated", f"Orden de Compra generada #{po_data['quote_number']}")
    return {"message": "Orden de compra generada", "po_id": po_data['id']}

@router.post("/{id}/send-po")
async def send_purchase_order(id: str, background_tasks: BackgroundTasks, payload: dict = Body(...)):
    quote_data = await db.quotes_v2.find_one({"id": id})
    if not quote_data:
        try:
            quote_data = await db.quotes_v2.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
    if not quote_data:
        raise HTTPException(status_code=404, detail="Quote not found")
    if '_id' in quote_data:
        quote_data['id'] = str(quote_data['_id'])
        del quote_data['_id']
    quote = Quote(**quote_data)
    emails = payload.get('emails', [])
    if not emails:
        raise HTTPException(status_code=400, detail="No hay destinatarios especificados")
    pdf_bytes = _generate_pdf_bytes(quote, is_po=True)
    subject = f"Orden de Compra #{quote.quote_number} - Gimmicks"
    html_content = f"""<h1>Orden de Compra</h1><p>Estimado/a {quote.client_name},</p><p>Adjunto encontrará la orden de compra #{quote.quote_number}.</p><p>Saludos,<br>Gimmicks Marketing Services</p>"""
    filename = f"ORDEN_COMPRA_{quote.quote_number}.pdf"
    for email in emails:
        background_tasks.add_task(send_po_email, email, subject, html_content, pdf_bytes, filename)
    await log_client_activity(quote.client_id, "po_sent", f"Orden de Compra enviada #{quote.quote_number} a {', '.join(emails)}")
    return {"message": f"Orden de compra enviada a {', '.join(emails)}"}

@router.post("/{id}/send-quote")
async def send_quote_email(id: str, background_tasks: BackgroundTasks, payload: dict = Body(...)):
    quote_data = await db.quotes_v2.find_one({"id": id})
    if not quote_data:
        try:
            quote_data = await db.quotes_v2.find_one({"_id": ObjectId(id)})
        except Exception:
            pass
    if not quote_data:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if '_id' in quote_data:
        quote_data['id'] = str(quote_data['_id'])
        del quote_data['_id']
    quote = Quote(**quote_data)
    emails = payload.get('emails', [])
    if not emails:
        raise HTTPException(status_code=400, detail="No hay destinatarios especificados")
    pdf_bytes = _generate_pdf_bytes(quote, is_po=False)
    subject = f"Cotización #{quote.quote_number} - Gimmicks"
    html_content = f"""<h1>Cotización</h1><p>Estimado/a {quote.client_name},</p><p>Adjunto encontrará la cotización #{quote.quote_number} para su revisión.</p><p>Quedamos atentos a sus comentarios.</p><p>Saludos,<br>Gimmicks Marketing Services</p>"""
    filename = f"COTIZACION_{quote.quote_number}.pdf"
    for email in emails:
        background_tasks.add_task(send_po_email, email, subject, html_content, pdf_bytes, filename)
    await log_client_activity(quote.client_id, "quote_sent", f"Cotización enviada #{quote.quote_number} a {', '.join(emails)}")
    return {"message": f"Cotización enviada a {', '.join(emails)}"}
