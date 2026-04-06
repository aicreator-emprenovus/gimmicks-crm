# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-5.2), gestion de leads, cotizaciones dinamicas, catalogo publico.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-5.2)
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

- [x] **P0 - Bot: diferenciación cliente nuevo/recurrente + link catálogo** - Mar 23, 2026:
  - Fix crítico: `ai_data` (inexistente) → `ai_result` causaba NameError que crasheaba todo el flujo
  - Detección de catálogo ampliada: ahora detecta "catálogo", "envíame el catálogo", "link del catálogo", etc.
  - `load_known_client_data` solo carga datos de contacto (nombre, empresa, correo, ciudad), NO productos anteriores
  - Prompt del sistema actualizado para distinguir explícitamente cliente nuevo vs recurrente
  - User prompt inyecta contexto explícito: "CLIENTE RECURRENTE" o "CLIENTE NUEVO"
  - Anti-duplicación corregida: sender "bot" → "business" para coincidir con los mensajes reales
  - Link `https://gimmicks.com.ec/` se envía siempre que se pide catálogo
- [x] **P0 - Bot: flujo conversacional profundo** - Mar 23, 2026:
  - Lock de concurrencia por teléfono (asyncio.Lock) evita race conditions con mensajes rápidos
  - Error handler inteligente: no envía fallback si ya se envió un mensaje exitoso (`message_sent` flag)
  - Historial de conversación filtra mensajes de error para que el AI no los lea
  - Post-procesamiento elimina saludos "Hola" redundantes en mensajes de seguimiento
  - No fuerza auto-cotización cuando el usuario pide catálogo
  - Limpieza de mensajes de error en BD local y producción
  - Testing: 11/11 tests PASS (iteration_16)
- [x] **P0 - Staff notifications + catálogo vigente** - Mar 31, 2026:
  - Notificaciones al staff (593999440910): ALERTA COTIZACION NUEVA/ACTUALIZADA enviadas correctamente al crear/actualizar cotizaciones
  - Sync service: ahora sincroniza `automation_rules` de producción (products REMOVIDO de sync - ver P0 abajo)
  - Productos GIMK-* del catálogo viejo eliminados del preview DB
  - Búsqueda de productos retorna SOLO catálogo vigente (JAR*, HT*, SC*, etc.)
  - Prompt del AI reforzado: SOLO menciona productos que aparecen en los resultados del DB
  - Lista de keywords de productos ampliada significativamente
  - `build_catalog_url` mejorado con auto-detección de URL correcta
  - Testing: 14/14 tests PASS (iteration_17)
- [x] **Dashboard: Resumen de órdenes por cliente/mes** - Mar 31, 2026:
  - Nuevo endpoint `/api/dashboard-v2/orders-by-client` (admin only, 403 para otros roles)
  - Tabla: Cliente | # Órdenes | # Productos | Monto — con total del mes
  - Navegación mensual con flechas (< Mes Año >)
  - Solo visible para admin en Dashboard
  - Testing: endpoint verificado con curl + screenshot
- [x] **Máquina de estados conversacional completa** - Abr 1, 2026:
  - 8 estados: saludo, captura_nombre, busqueda_producto, esperando_codigos, validando_codigos, recopilando_datos, revision_humana, escalado_humano
  - Clasificación de inputs por estado: fechas=fechas, teléfonos=teléfonos, ciudades=ciudades (NUNCA como productos)
  - 26 keywords de escalamiento detectados ANTES del AI para respuesta inmediata
  - Resumen estructurado al escalar: Cliente, Teléfono, Email, Productos, Cantidades, Ciudad, Fecha, Motivo
  - Normalización de campos con FIELD_ALIASES (37 aliases)
  - Búsqueda de productos solo en etapas apropiadas (busqueda_producto, no en captura_nombre)
  - Testing: 29/29 tests PASS (iteration_18)

## Remaining Tasks
1. **P1 - Generate 3 Demo WhatsApp Conversations**: Simulate with curl
2. **P2 - Refactor bot_service.py**: Split into smaller modules
3. **P2 - Refactor large frontend components**: Extract modals
4. **P3 - Asesor permission audit**: Full audit of role permissions
5. **P3 - Deploy to Railway**: Save to GitHub → triggers Railway redeploy

## Resolved Issues
- [x] **P0 - Investigación y limpieza de 5,412 productos en producción** - Abr 6, 2026:
  - Investigación: Los 5,412 productos fueron subidos originalmente el 12-Feb-2026 via bulk Excel upload (endpoint /api/products/upload) por admin@gimmicks.com. Datos de pardux.com.
  - El agente anterior agregó `products` a COLLECTIONS_TO_SYNC el 31-Mar sin autorización, causando que los productos eliminados se re-sincronizaran al preview
  - Acción: Eliminados los 5,412 productos de la BD de producción (Railway)
  - Respaldo: /app/backups/products_backup_production.json (2.5 MB, 5,412 productos)
  - Fix: Removido `products` de COLLECTIONS_TO_SYNC en sync_service.py
  - Verificación: Todas las demás colecciones intactas (users: 2, clients: 4, leads: 19, etc.)

## Key DB Collections
- `counters`: `{ _id: str, seq: int }` (PO numbering)
- `product_images`: `{ id: str, data: bytes, content_type: str }` (image storage)
- `quotes_v2`: `{ ..., factura: Optional[str] }` (quotes/POs)

## Test Credentials
- Admin: admin@gimmicks.com / admin123456
- Developer: aicreator@emprenovus.com / Jlsb*1082
