# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestion de leads, cotizaciones dinamicas, catalogo publico.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP
- **Production DB**: Railway MongoDB

## Roles y Permisos

### Admin
- Acceso completo a todo el sistema
- Puede crear, editar, eliminar clientes/interesados/cotizaciones/ordenes
- Puede exportar datos, ver papelera, dashboard, leads, usuarios
- NO puede ver, editar ni eliminar al usuario desarrollador

### Asesor
- Puede: crear y editar clientes, interesados, ordenes de compra, cotizaciones
- NO puede: eliminar nada (clientes, interesados, cotizaciones, ordenes)
- NO puede: descargar/exportar datos, ver papelera
- NO puede: ver Dashboard, Leads, Usuarios, Configuracion
- Inbox: solo leer y responder (no eliminar/limpiar conversaciones)

### Desarrollador
- SOLO acceso a Configuracion
- No puede ser eliminado ni modificado por admin
- No aparece en listado de usuarios para admin
- Credenciales: aicreator@emprenovus.com / Jlsb*1082

## Completed Tasks
- [x] Core system merge (Project A + B)
- [x] WhatsApp Bot multi-step flow
- [x] Interesados/Clientes separation
- [x] Lead-to-Client auto-promotion
- [x] SMTP email integration
- [x] Dashboard analytics
- [x] Security hardening
- [x] Bot flow refinements
- [x] Production data sync
- [x] Bot E2E verification (17/17)
- [x] Railway deploy fix
- [x] Inbox: asesor read-only (no delete/clear)
- [x] Starred conversations filter fix
- [x] Role-based permissions (admin/asesor/desarrollador) - Feb 23, 2026
- [x] Asesor: no delete/export, no dashboard/leads
- [x] Desarrollador: only Configuracion access, protected user
- [x] WhatsApp number migration (+593963560326) - Mar 2026
- [x] **Bot: Integración de reglas de automatización** - Mar 18, 2026:
  - Bot ahora carga reglas activas de `automation_rules` e inyecta en system prompt
  - 18 reglas activas: bienvenida, follow-up, catálogo, cotización, quejas, etc.
- [x] **Bot: Upgrade a GPT-5.2** - Mar 18, 2026: Modelo actualizado de gpt-4o a gpt-5.2
- [x] **Frontend served from FastAPI** - Mar 18, 2026: SPA catch-all for Railway production deploy
- [x] Editable quote prices in QuoteBuilder
- [x] Discount calculation fix (stale closure bug)
- [x] Persistent image storage (MongoDB product_images collection)
- [x] Independent PO numbering (counters collection, starting 4712)
- [x] Enhanced PO PDF with editable client fields modal
- [x] Client filtering & predictive search in quotes
- [x] **P0 Performance fix** - Mar 9, 2026:
  - SecurityHeadersMiddleware: skip Cache-Control override for image/upload routes
  - RequestSizeLimitMiddleware: 10MB -> 25MB
  - Image endpoint: ETag + immutable cache headers
  - PDF generation: direct MongoDB read for images (no HTTP roundtrip)
- [x] **PDF image fetch robustness** - Mar 9, 2026:
  - Handle "N/A", empty, null image URLs gracefully
  - Google Drive: 3 fallback URL strategies (lh3.googleusercontent.com, thumbnail, uc?export)
  - Increased timeout from 5s to 10s for external image fetches
  - Skip Google Drive folder URLs (not fetchable)
  - Validate content-type is image before embedding
  - Non-HTTP URLs safely skipped
- [x] **Persistencia de datos de Factura/OC** - Mar 18, 2026:
  - Nuevo campo `po_header_data` en quotes_v2 para guardar datos del modal
  - Endpoints: PUT/GET `/api/quotes-v2/{id}/po-header`
  - Modal carga datos guardados al abrir, botón "Guardar Datos" junto a "Generar PDF"
- [x] **Font size OC PDF +3pts** - Mar 18, 2026:
  - Campos header del PDF de Orden de Compra: 9pt → 12pt (etiquetas y valores)
  - 29 products had absolute URLs to `quotepro-14.emergent.host` (non-existent) → converted to relative paths
  - Frontend `getImageUrl` now extracts relative paths from any full URL with `/api/uploads/` or `/api/inventory/images/`
  - Backend startup migration auto-fixes old deployment URLs on any new deploy
  - Google Drive URLs now use `lh3.googleusercontent.com` format (more reliable from servers)
  - Migrated 5 local filesystem images to MongoDB's `product_images` collection

## Remaining Tasks
1. **P1 - Generate 3 Demo WhatsApp Conversations**: Simulate with curl
2. **P2 - Refactor bot_service.py**: Split into smaller modules
3. **P2 - Refactor large frontend components**: Extract modals
4. **P3 - Asesor permission audit**: Full audit of role permissions
5. **P3 - Deploy to Railway**: Save to GitHub and redeploy

## Key DB Collections
- `counters`: `{ _id: str, seq: int }` (PO numbering)
- `product_images`: `{ id: str, data: bytes, content_type: str }` (image storage)
- `quotes_v2`: `{ ..., factura: Optional[str] }` (quotes/POs)

## Test Credentials
- Admin: admin@gimmicks.com / admin123456
- Developer: aicreator@emprenovus.com / Jlsb*1082
