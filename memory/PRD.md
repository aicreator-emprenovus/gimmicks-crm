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
- [x] **Máquina de estados conversacional v2 (reescritura completa)** - Abr 6, 2026:
  - Reescritura completa de bot_service.py con 9 estados estrictos:
    saludo → captura_nombre → busqueda_producto → esperando_codigos → validando_codigos → tipo_logo → recopilando_datos → confirmacion → escalado_humano
  - BUGS CORREGIDOS:
    1. Bot ahora SIEMPRE saluda y pide nombre primero
    2. Nombre del cliente NUNCA se confunde con producto (búsqueda de productos solo en estado busqueda_producto)
    3. Links inválidos (railway.app) ELIMINADOS - productos se muestran inline, gimmicks.com.ec como fallback
    4. Datos de leads COMPLETOS: nombre, email, ciudad, empresa obligatorios antes de generar cotización
  - Nuevo estado "tipo_logo": pregunta tipo de logo antes de datos personales
  - Orden de recopilación: códigos → cantidades → logo → email → ciudad → empresa
  - Eliminado: build_catalog_url (links internos), load_automation_rules (reglas inyectadas), determine_stage (recálculo automático), reanudación de conversación por inactividad
  - Mantenido: anti-duplicación, auto-creación de clientes, pipeline tracking, escalamiento, notificaciones staff
  - Normalización mejorada de cantidades_por_producto y codigos_producto (maneja dict/list del AI)
  - Testing: 8/8 backend + bot flow 100% (iteration_19)
- [x] **Code Quality Review Fixes** - Abr 6, 2026:
  - **httpOnly Cookies**: Auth tokens migrados de localStorage a httpOnly cookies (secure, samesite=lax, path=/api)
    - Backend: login/register setean cookie, get_current_user lee cookie, /auth/logout limpia cookie
    - Frontend: axios.defaults.withCredentials=true, CERO localStorage para tokens
    - Dashboard, Inventory, Clients, Quotes routes actualizados para soportar cookies
  - **Empty Catch Blocks**: 8 catch {} vacíos reemplazados con console.error() en QuoteHistory, QuoteBuilder, Inventory
  - **React Key Anti-patterns**: 8 usos de key={i} reemplazados con IDs únicos en Quotes, QuoteHistory, Dashboard, Inventory
  - **Test File Secrets**: 6 archivos de test actualizados para cargar credenciales de variables de entorno
  - **Bot Service Refactoring**: Extraídas 4 funciones helper (_build_stage_context, _merge_extracted_data, _determine_next_stage, _is_quote_ready) para reducir complejidad
  - **CORS**: Actualizado para allow_credentials con orígenes específicos
  - Testing: 13/13 backend + frontend completo 100% (iteration_20)

## Resolved Issues (Latest)
- [x] **Link del inventario filtrado en el bot + email para catalogo** - Abr 8, 2026:
  - Cuando hay productos: bot envia link `/catalog?q=keyword` filtrado para que cliente vea opciones y copie codigos
  - Cuando NO hay productos: bot pide email, NUNCA dice "no tenemos", alerta al staff
  - Filtro STOPWORDS en URL del catalogo (quita "necesito", "para", etc.)
  - URLs inventadas por la IA son eliminadas automaticamente; solo se mantiene el link real
  - Fallback: si la IA no incluye el link, se agrega automaticamente al final
  - Testing: 10/10 backend + frontend 100% (iteration_28)
- [x] **5 alertas WhatsApp al agente humano** - Abr 8, 2026:
  - Alerta 1: NUEVA COTIZACION con nombre del cliente (ya existia, verificada)
  - Alerta 2: COTIZACION ACTUALIZADA con nombre del cliente (ya existia, verificada)
  - Alerta 3: ESCALAMIENTO cuando cliente pide hablar con agente humano (ya existia, verificada)
  - Alerta 4: BOT NO PUEDE CONTINUAR - nueva funcion `notify_staff_bot_confused()` cuando LLM falla
  - Alerta 5: SOLICITUD DE CATALOGO POR EMAIL - cuando producto no encontrado + email capturado
  - Bot NUNCA dice "no tenemos" o "no encontre" - pide email para catalogo
  - Filtro STOPWORDS en busqueda para evitar falsos positivos ("para", "con", etc.)
  - Estado `no_products_found_pending` para alertar cuando email llega en turno posterior
  - Testing: 9/9 backend 100% (iteration_27)
- [x] **Reemplazo completo del flujo conversacional del bot WhatsApp** - Abr 8, 2026:
  - **Nuevo flujo de 5 pasos**: 1) Saludo, 2) Nombre, 3) Producto (busqueda), 4) Codigos + cantidades, 5) Datos adicionales uno a uno (personalizacion, email, empresa, ciudad, fecha entrega)
  - **Cotizacion automatica**: Se genera cuando tiene codigos + cantidad + email + empresa
  - **Eliminado**: State machine de etapas rigidas, reemplazada por flujo secuencial inteligente
  - **Eliminado**: campos `escalate`, `escalate_reason`, `next_stage` del JSON de respuesta AI
  - **Renombrado**: `color_logo` → `personalizacion` en todo el sistema
  - **Preservado**: Todas las funciones existentes (notificaciones, cotizaciones, escalamiento, anti-duplicacion)
  - **Testing**: 14/14 backend + frontend 100% (iteration_26)
  - **Nota**: GPT-5.2 tiene errores temporales de conexion; el flujo fue validado con gpt-4o
- [x] **Eliminacion completa de Catalogo PDF + Nuevo flujo bot email** - Abr 6, 2026:
  - **Eliminado**: Página CatalogPdf.jsx, ruta /catalog-pdf, menú sidebar, tab en Settings
  - **Eliminado**: Endpoints backend: /api/catalog/upload-pdf, /api/catalog/pdf, /api/catalog/info, DELETE /api/catalog/pdf
  - **Eliminado**: Toda lógica de detección y envío de PDF en bot_service.py (get_catalog_pdf_url, should_send_catalog_pdf)
  - **Nuevo flujo bot**: Si no hay productos o el cliente pide catálogo → pide email → notifica al asesor por WhatsApp
  - **Alerta staff**: `notify_staff_catalog_request()` envía WhatsApp a 593999440910 con nombre, teléfono y email
  - **Protección**: Override de `needs_human/escalate` para solicitudes de catálogo (no se escala)
  - **Testing**: 10/10 backend + frontend 100% (iteration_25)
- [x] **P0 - Bot envía URL del catálogo en texto en lugar de adjuntar PDF** - Abr 6, 2026:
  - **Causa raíz**: `send_document_fn` fallaba porque la URL del catálogo no era accesible públicamente para los servidores de WhatsApp
  - **Fix**: Eliminado el intento de adjuntar documento. El bot ahora incluye la URL del catálogo directamente en el texto del mensaje
  - **Cambios**: 3 modificaciones en `bot_service.py`:
    1. System prompt actualizado para instruir al AI que incluya URL_CATALOGO en su respuesta
    2. `catalog_pdf_context` ahora pasa la URL real al AI para que la use
    3. Lógica de envío de documento reemplazada por append de URL al texto como fallback
  - **Testing**: 11/11 tests PASS (iteration_24)
- [x] **P0 - Fix "error de autenticación" en producción** - Abr 6, 2026:
  - **Causa raíz**: `static_frontend/` (build del 18-Mar) usaba `localStorage` para auth, pero el backend fue migrado a httpOnly cookies
  - **Fix**: Reconstruido `static_frontend/` con el código actualizado (cookies, withCredentials, sin localStorage)
  - **Fix adicional**: CORS middleware mejorado con orígenes dinámicos desde env vars
  - **Fix adicional**: `start.py` ahora detecta builds desactualizados y reconstruye automáticamente
  - **Testing**: 14/14 backend + todos los flujos frontend verificados (iteration_21)
- [x] **Bug - Escritura continua en formularios de reglas** - Abr 6, 2026:
  - `RuleFormFields` definido como componente dentro de `Settings` causaba pérdida de foco. Convertido a JSX variable.
- [x] **Feature - 4 nuevas funcionalidades** - Abr 6, 2026:
  1. **Catálogo PDF en menú principal**: Nueva página `/catalog-pdf` para admin/asesor con upload/ver/eliminar
  2. **Catálogo muestra quién lo subió**: Info completa (archivo, tamaño, usuario, fecha). Upload nuevo elimina el anterior
  3. **Historial de actividad (admin)**: Nueva página `/activity-log` con filtros (usuario, acción, fecha), badges por tipo, paginación. Registra: login, catalog upload/delete, product create/delete, inventory upload/download, quote update
  4. **Alertas de descarga de inventario**: Cada 15 días el usuario debe descargar inventario antes de poder subir productos. Banner de alerta en Inventario, bloqueo 403 en backend
  - Testing: 21/21 backend + todos los flujos frontend (iteration_23)

## Resolved Issues (Latest cont.)
- [x] **P0 - Fix Railway deploy: emergentintegrations** - Abr 8, 2026:
  - Railway build fallaba con `ERROR: No matching distribution found for emergentintegrations==0.1.1`
  - Fix: Agregado `--extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/` al inicio de `requirements.txt`
  - Pendiente: Usuario debe hacer "Save to GitHub" para triggear nuevo deploy
- [x] **P0 - Bot fallback LLM (gpt-5.2 → gpt-4o)** - Abr 8, 2026:
  - GPT-5.2 tenía errores de conexión persistentes, bot respondía siempre "Disculpa, tuve un problema"
  - Fix: `call_llm()` ahora intenta gpt-5.2 primero, si falla automáticamente reintenta con gpt-4o
- [x] **P0 - Bot enviando mensajes repetidos en loop** - Abr 8, 2026:
  - **Causa raíz**: WhatsApp reintentaba webhooks porque el handler era síncrono (esperaba LLM ~15s)
  - **Fix 1**: Webhook ahora retorna 200 inmediatamente con `asyncio.create_task`
  - **Fix 2**: Deduplicación por `whatsapp_message_id` (wamid) - mensajes ya procesados se ignoran
  - **Fix 3**: Cooldown de 8 segundos por teléfono - si el bot ya respondió hace <8s, no envía
  - **Fix 4**: Anti-overlap 70% ahora OMITE el mensaje duplicado en vez de reformularlo con LLM
  - Verificado: 3 webhooks con mismo wamid → solo 1 respuesta enviada

## Remaining Tasks
1. **P2 - Refactor bot_service.py**: Split into smaller modules
2. **P2 - Refactor large frontend components**: Extract modals
3. **P3 - Asesor permission audit**: Full audit of role permissions

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
