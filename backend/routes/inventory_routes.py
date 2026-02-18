from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Optional
from models_b import Product, ProductCreate
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd
import io
import uuid
import re
import os
import shutil
from pathlib import Path

router = APIRouter()

# Will be set from server.py
db = None

def set_db(database):
    global db
    db = database

def normalize_header(header: str) -> str:
    header = str(header).upper().strip()
    replacements = {
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'Ü': 'U', 'Ñ': 'N'
    }
    for char, rep in replacements.items():
        header = header.replace(char, rep)
    return header

def find_header_row(df_initial, expected_cols=['CODIGO', 'CODE', 'SKU']):
    if df_initial.shape[0] > 0:
        current_headers = [normalize_header(c) for c in df_initial.columns]
        for exp in expected_cols:
            if any(exp in h for h in current_headers):
                return -1
    for i, row in df_initial.head(10).iterrows():
        row_values = [normalize_header(str(val)) for val in row.values]
        for exp in expected_cols:
            if any(exp in str(rv) for rv in row_values):
                return i
    return None

@router.post("/upload")
async def upload_inventory(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xls', '.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Formato inválido. Use Excel o CSV.")
    
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            try:
                df_initial = pd.read_csv(io.BytesIO(contents), header=None, on_bad_lines='skip', engine='python')
            except:
                df_initial = pd.read_csv(io.BytesIO(contents), header=None)
        else:
            df_initial = pd.read_excel(io.BytesIO(contents), header=None)
            
        header_row_idx = find_header_row(df_initial, ['CODIGO', 'CODE', 'SKU', 'CODIGO PRODUCTO'])
        
        df = None
        if header_row_idx is None:
             if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(contents))
             else:
                df = pd.read_excel(io.BytesIO(contents))
        elif header_row_idx == -1:
             new_header = df_initial.iloc[0]
             df = df_initial[1:]
             df.columns = new_header
        else:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(contents), header=header_row_idx)
            else:
                df = pd.read_excel(io.BytesIO(contents), header=header_row_idx)

        header_map = {}
        found_headers = []
        for col in df.columns:
            norm = normalize_header(col)
            header_map[norm] = col
            found_headers.append(norm)
            
        def get_col(candidates):
            for c in candidates:
                if c in header_map:
                    return header_map[c]
                for h in header_map:
                    if c in h:
                        return header_map[h]
            return None

        col_code = get_col(['CODIGO PRODUCTO', 'CODIGO', 'CODE', 'SKU'])
        col_name = get_col(['NOMBRE DEL PRODUCTO', 'NOMBRE', 'NAME', 'PRODUCTO'])
        col_desc = get_col(['DESCRIPCION', 'DESCRIPTION'])
        col_cost = get_col(['COSTO', 'COST', 'PRECIO DE COMPRA'])
        col_supplier = get_col(['PROVEEDOR', 'SUPPLIER'])
        col_supplier_code = get_col(['CODIGO PROVEEDOR'])
        col_img = get_col(['FOTO', 'IMAGEN', 'IMAGE', 'URL', 'URL IMAGEN'])
        col_stock = get_col(['STOCK', 'CANTIDAD', 'EXISTENCIA'])
        col_price = get_col(['PRECIO', 'PRICE', 'PVP'])
        
        # Find category column(s) - single column with comma-separated values or multiple columns
        col_categorias = get_col(['CATEGORIAS', 'CATEGORIA', 'CATEGORIES'])
        cat_cols = []
        if not col_categorias:
            for h_norm, h_orig in header_map.items():
                if 'CAT' in h_norm:
                    cat_cols.append(h_orig)
        
        if not col_code:
            msg = f"No se encontró la columna 'CÓDIGO'. Columnas detectadas: {', '.join(found_headers[:5])}..."
            raise HTTPException(status_code=400, detail=msg)

        products_to_insert = []
        codes_seen = set()
        
        for index, row in df.iterrows():
            raw_code = row.get(col_code)
            if pd.isna(raw_code):
                continue
            code = str(raw_code).strip()
            if not code or code in codes_seen:
                continue
            codes_seen.add(code)
            
            def get_str(col):
                if not col: return ""
                val = row.get(col)
                if pd.isna(val) or str(val).lower() == 'nan': return ""
                return str(val).strip()

            def get_float(col):
                if not col: return 0.0
                val = row.get(col)
                if pd.isna(val): return 0.0
                try:
                    s = str(val).replace('$', '').replace(',', '').strip()
                    if not s: return 0.0
                    return float(s)
                except:
                    return 0.0
            
            def get_int(col):
                if not col: return 0
                val = row.get(col)
                if pd.isna(val): return 0
                try:
                    return int(float(str(val).replace(',', '').replace('$', '')))
                except:
                    return 0

            name = get_str(col_name)
            desc = get_str(col_desc)
            supplier = get_str(col_supplier)
            supplier_code = get_str(col_supplier_code)
            img_url = get_str(col_img)
            stock = get_int(col_stock)
            cost = get_float(col_cost)
            
            # Use explicit price if available, otherwise calculate from cost
            price = get_float(col_price)
            if price == 0 and cost > 0:
                price = cost * 1.35
            
            categories = []
            for c_col in cat_cols:
                val = get_str(c_col)
                if val and val.lower() != 'no':
                    parts = [p.strip() for p in val.split(',')]
                    for p in parts:
                        if p:
                            categories.append(p)
            categories = list(set([c for c in categories if c and c.lower() != 'nan']))

            if img_url == '0' or img_url.lower() == 'nan':
                img_url = ""

            product = Product(
                id=str(uuid.uuid4()),
                code=code,
                supplier_code=supplier_code,
                name=name,
                description=desc,
                stock=stock,
                price=round(price, 2),
                cost=cost,
                supplier=supplier,
                image_url=img_url,
                categories=categories
            )
            products_to_insert.append(product.model_dump())
        
        if not products_to_insert:
            raise HTTPException(status_code=400, detail="No se encontraron productos válidos.")

        await db.products.delete_many({})
        await db.products.insert_many(products_to_insert)
            
        return {"message": f"Se cargaron {len(products_to_insert)} productos correctamente."}
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")

@router.get("/categories", response_model=List[str])
async def get_categories():
    try:
        categories = await db.products.distinct("categories")
        return sorted([c for c in categories if c])
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

@router.get("/", response_model=None)
async def get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=10000)
):
    query = {}
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"description": regex},
            {"code": regex},
            {"supplier_code": regex},
            {"name": regex},
            {"categories": regex}
        ]
    if category and category != "Todas":
        query["categories"] = category
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query
    if min_cost is not None or max_cost is not None:
        cost_query = {}
        if min_cost is not None:
            cost_query["$gte"] = min_cost
        if max_cost is not None:
            cost_query["$lte"] = max_cost
        query["cost"] = cost_query
    
    total = await db.products.count_documents(query)
    skip = (page - 1) * limit
    products = await db.products.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    return {
        "products": products,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.post("/", response_model=Product)
async def create_product(product: ProductCreate):
    existing = await db.products.find_one({"code": product.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"El producto con código {product.code} ya existe.")
    new_product = Product(**product.model_dump())
    await db.products.insert_one(new_product.model_dump())
    return new_product

@router.put("/{code}", response_model=Product)
async def update_product(code: str, product: ProductCreate):
    result = await db.products.update_one(
        {"code": code},
        {"$set": product.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    updated = await db.products.find_one({"code": code}, {"_id": 0})
    return Product(**updated)

@router.delete("/{code}")
async def delete_product(code: str):
    result = await db.products.delete_one({"code": code})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado"}

@router.post("/upload-image")
async def upload_product_image(image: UploadFile = File(...)):
    contents = await image.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen no debe superar 20MB")
    
    upload_dir = Path("/app/backend/uploads/products")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(contents))
        if img.mode in ('RGBA', 'P', 'LA'):
            background = PILImage.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode == 'CMYK':
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        max_dim = 1200
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
        
        unique_filename = f"{uuid.uuid4()}.jpg"
        file_path = upload_dir / unique_filename
        img.save(file_path, 'JPEG', quality=82, optimize=True)
        
        image_url = f"/api/uploads/products/{unique_filename}"
        return {"image_url": image_url, "message": "Imagen subida exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo procesar la imagen: {str(e)}")
