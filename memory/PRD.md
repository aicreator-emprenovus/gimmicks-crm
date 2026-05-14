# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-5.2), gestion de leads, cotizaciones dinamicas, catalogo publico.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-5.2)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP
- **Database**: Emergent-managed MongoDB (local). Esta copia alterna ya NO depende de Railway.

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
- [x] **6 features de fortalecimiento del CRM** — May 14, 2026:
  - F1: Promoción Interesado→Cliente con detección de duplicados (HTTP 409 con mensaje claro indicando si choca por correo o teléfono).
  - F2: Tarjetas de leads ahora muestran `codigos_producto` (códigos exactos del catálogo).
  - F3: Tarjetas de leads ahora muestran badge `Cot. #N` cuando el bot ya generó cotización.
  - F4: Numeración consecutiva de cotizaciones **blindada** mediante contador atómico en `counters._id="quote_number"`, sembrado con MAX(quote_number) actual (101725 → continúa 101726+). Bug grave detectado: el método anterior (`count + 4698`) generaba colisiones masivas con cotizaciones existentes.
  - F5: Mensajes del agente humano persisten `attended_by_name`/`attended_by_email`. Inbox muestra "Atendido por …" debajo de cada burbuja humana; los mensajes del bot no llevan esta etiqueta.
  - F6: Acceso a "Configuración" oculto del menú para admin y asesor — visible solo para desarrollador. Route guard ya bloqueaba la URL directa.
  - Testing: 12/12 nuevos tests pytest + 29/29 invariantes del bot pasan. Sin regresiones.


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
- [x] **P0 — Agente humano no recibía alertas (ventana 24h de WhatsApp + plantilla inexistente)** - May 14, 2026:
  - **Causa raíz**: el agente +593 99 944 0910 nunca escribe primero al business → la ventana de 24h SIEMPRE está cerrada → WhatsApp rechaza cualquier mensaje libre con error `131047`. Las funciones `notify_staff_new_quote`, `send_escalation_summary`, `notify_staff_bot_confused` enviaban texto libre directo sin fallback a template.
  - **Fix**: las 4 funciones de notificación (`notify_staff_new_quote`, `send_escalation_summary`, `notify_staff_catalog_request`, `notify_staff_bot_confused`) ahora usan el helper compartido `_send_to_human_agent()` que:
    1. Intenta texto libre primero
    2. Si Meta rechaza con error 131047/131026/24-hour → fallback automático a template `alerta_agente_humano`
    3. **Siempre** persiste la alerta en `db.pending_agent_alerts` con `delivered_via` = `"text" | "template" | "none"` → ninguna alerta se pierde aunque ambos envíos fallen.
  - **Endpoints nuevos** para el CRM:
    - `GET /api/agent-alerts?only_unread=true&limit=50` lista alertas
    - `POST /api/agent-alerts/{id}/read` marca leída
    - `POST /api/agent-alerts/read-all` marca todas leídas
  - **Plantilla requerida en Meta Business Manager** (formato propuesto):
    - Nombre: `alerta_agente_humano`
    - Categoría: `UTILITY`
    - Idioma: `es`
    - Body: `🔔 {{1}}\n\n{{2}}\n\n{{3}}`
    - Variables: 3 (título, datos del cliente, próximo paso)
  - **Tests**: `/app/backend/tests/test_agent_alerts_fallback.py` con 3 escenarios PASS (text OK, template fallback, full failure → still persisted).


  - **Síntoma**: cuando el cliente enviaba una imagen por WhatsApp, en el chat aparecía el dump completo del webhook (`{"raw":{"from":"...","type":"image","image":{...}}}`) en vez de la imagen.
  - **Causa**: el webhook handler guardaba `content = {"raw": message}` para cualquier tipo de mensaje que no fuera "text", sin descargar la media.
  - **Fix**: nuevo helper `persist_inbound_media()` en `server.py` que cuando el webhook recibe `image / video / audio / document / sticker / voice`:
    1. Resuelve el `url` real vía Graph API (`GET /v18.0/{media_id}`)
    2. Descarga los bytes con el `WHATSAPP_ACCESS_TOKEN`
    3. Los persiste en Object Storage en `gimmicks-crm/inbox-attachments/{uuid}.{ext}`
    4. Guarda el mensaje con el MISMO formato que los attachments salientes (`media_kind`, `storage_path`, `mime_type`, `filename`, `size`) → el `<AttachmentRenderer>` existente los pinta sin cambios en el frontend.
  - El caption (si existe) se preserva en `content.text` para que el bot lo procese como texto (un cliente puede subir foto con "necesito cotizar 8 de estos" y el bot busca producto).
  - **Sidebar preview** ahora muestra `🖼️ Imagen · caption` / `🎥 Video` / `📄 Documento` en lugar del JSON.
  - **Fallback robusto**: si la descarga falla (token expirado, Meta caído, etc.), guarda el caption + `_download_failed: true` y NO bloquea el flujo. El mensaje queda en BD para revisión.
  - **Imagen sin caption** → bot NO responde (antes: con placeholder podría dispararse erróneamente).
  - Test `/app/backend/tests/test_inbound_media_flow.py` con 3 escenarios PASS.


  - **Síntoma reportado**: las notificaciones de nuevas cotizaciones/leads no llegaban al agente humano.
  - **Causa raíz**: en una iteración anterior (test_iteration36) un agente cambió `STAFF_NOTIFICATION_PHONE` de `593999440910` (correcto, agente humano) a `593963560326` (incorrecto, el propio número del bot). El bot intentaba auto-notificarse → ningún humano recibía nada.
  - **Fix**: corregido a `STAFF_NOTIFICATION_PHONE = "593999440910"` (WhatsApp del agente humano +593 99 944 0910). El bot sigue usando su propio número +593 96 356 0326 sin cambios.
  - **Blindaje permanente**:
    - Comentario crítico en línea del constante explicando los 2 números y el por qué del routing.
    - `run_bot_regression.py` ampliada: 27 → **29 invariantes** (2 nuevas para validar el routing).
    - Self-check startup: 14 → **16 invariantes** (2 nuevas).
    - Docstring crítico de `bot_service.py` actualizado.
    - Test `test_iteration36_strengthened_prompts.py` corregido — tenía la aserción equivocada que permitió el error original.


  - **Síntoma reportado**: en la conversación de Patricia Tito, tras dar su correo, el bot respondió con el dump JSON completo de la respuesta del LLM (incluyendo `extracted_data`, `intent`, `lead_quality`, `conversation_summary`, etc.) en vez del campo `response`.
  - **Causa raíz**: el LLM emitió JSON con coma final inválida (`"...", \n}`), `json.loads()` falló, y el fallback en `call_llm` retornaba `{"response": response_text, ...}` con el TEXTO CRUDO completo. Luego se enviaba al cliente sin sanear.
  - **Fix (3 capas de defensa)** en `bot_service.py`:
    1. **Tier 1 — `_repair_json()`**: repara errores comunes (trailing commas antes de `}`/`]`, smart quotes Unicode) antes del segundo intento de `json.loads`.
    2. **Tier 2 — `_extract_response_field()`**: regex que pesca solo el valor del campo `response` aún de JSON irrecuperable, decodifica escapes `\n`, `\"`, `\uXXXX`.
    3. **Tier 3 — `_looks_like_json()` + final guard**: detector heurístico que se ejecuta DOS veces (después del parsing y justo antes del `send_message_fn`). Si detecta un dump JSON, intenta extraer el campo `response`; si falla, reemplaza por mensaje seguro: *"Permíteme un momento, estoy revisando tu requerimiento."*
  - **Tests** (`/app/backend/tests/test_json_leak_safety.py`, 8/8 PASS):
    - Reproducción exacta del JSON malformado de Patricia Tito → recuperado correctamente
    - Smart quotes Unicode → reparadas
    - Texto legítimo en español → NO false positive
    - JSON irrecuperable → fallback seguro
  - **Blindaje permanente**:
    - `run_bot_regression.py` ampliada: 22 → **27 invariantes** (5 nuevas para JSON leak).
    - Self-check al startup: 11 → **14 invariantes** (3 nuevas: leak detector, repair, extract).
    - Docstring crítico de `bot_service.py` actualizado con la regla de las 3 capas.
  - Verificado: producción reciente vio el bug; preview ya no puede reproducirlo bajo ningún escenario testeado.


  - **Bug del preview**: `<img src="...attachments/{id}">` fallaba con `{"detail":"Token requerido"}` porque el browser no envía el JWT en el Authorization header. Fix: nuevo hook `useAuthenticatedAttachment` en `Inbox.jsx` que hace `axios.get(... { responseType: 'blob' })` con el JWT y crea blob URLs. Aplica para imágenes, videos, audios y documentos. Blob URLs cacheadas en memoria por `attachmentId`.
  - **Botón de descarga**: clic en imagen/documento ahora descarga el archivo (manteniendo el filename original).
  - **Bot blindado** (a prueba de regresiones futuras):
    - Master regression suite: `/app/backend/tests/run_bot_regression.py` — 22 invariantes en un solo comando (estáticas SYSTEM_PROMPT, resolver, accent post-processor, forbidden personalization stripper, e2e con LLM real para escenarios críticos).
    - Self-check al startup: `_verify_bot_invariants()` corre en cada boot del backend y loguea CRITICAL si algo se rompió. Visible en supervisor logs.
    - Comentario CRÍTICO al inicio de `bot_service.py` con el listado completo de invariantes y referencias al runner + self-check. Cualquier futuro agente que toque el archivo verá la advertencia primero.
  - Tests: 22/22 PASS. Self-check al startup: 11/11 OK. Test de adjuntos blob (upload + GET sin/con auth): PASS.


  - **Problema**: el usuario no puede actualizar `WHATSAPP_PHONE_NUMBER_ID` en producción y reportó que aún tras el redeploy el sistema fallaba (screenshot mostró "Reglas activas: 12" en producción vs 13 en preview, confirmando que producción tenía código viejo).
  - **Solución estructural**: nueva colección `system_config` en MongoDB y endpoint `PUT /api/admin/system-config/whatsapp_phone_number_id` que persiste un override editable desde la UI.
  - **Resolver actualizado** (`_resolve_phone_number_id`): nueva prioridad: contextvar → DB override (`SYSTEM_CONFIG_CACHE`) → env var → hardcoded `CURRENT_WHATSAPP_PHONE_NUMBER_ID`. El cache se carga en startup vía `load_system_config_cache()` y se refresca inmediatamente al guardar desde la UI — toma efecto sin redeploy.
  - **Validación**: el endpoint rechaza con 400 cualquier intento de guardar un ID que esté en `RETIRED_PHONE_NUMBER_IDS` y exige formato numérico.
  - **UI**: tarjeta "Diagnóstico de WhatsApp" en `Configuración → tab WhatsApp` ampliada con bloque "Override del Phone Number ID (sin redeploy)" — input + botones "Guardar override" y "Forzar ID actual" (preset al ID `965777766626628` del número +593 96 356 0326).
  - **Acceso**: la sección Configuración ahora es visible para roles `admin` y `desarrollador` (antes solo desarrollador).
  - **Activity log**: cada cambio de configuración queda auditado con `system_config_update`.
  - Tests: smoke curl con login admin → set/get/list/reject-retired (4/4 PASS).


  - **Problema reportado**: el env var `WHATSAPP_PHONE_NUMBER_ID` en producción apunta al ID retirado `994356967089829` y el usuario no puede actualizarlo. Necesitaba que el sistema funcionara sin tocar producción.
  - **Fix**: agregada constante `CURRENT_WHATSAPP_PHONE_NUMBER_ID = "965777766626628"` (corresponde al número actual +593 96 356 0326). El helper `_resolve_phone_number_id()` ahora cae a este valor por defecto cuando contextvar y env var están vacíos o retirados. Resultado: los envíos siempre salen del número correcto, sin importar la configuración del entorno.
  - El env var sigue ganando si tiene un ID válido no-retirado, así que migrar a un nuevo número en el futuro solo requiere actualizar el env var.
  - **Diagnóstico en CRM**: nueva tarjeta "Diagnóstico de WhatsApp" en `Configuración → tab WhatsApp` que muestra estado en verde/amarillo/rojo, expone `effective_phone_id` (lo que realmente se usa) vs `whatsapp_phone_id` (lo que dice el env), y un botón "Refrescar diagnóstico". No requiere curl ni token manual.
  - El endpoint `/api/webhook/whatsapp/diagnostics` ahora retorna ambos campos: `whatsapp_phone_id` (lo configurado) y `effective_phone_id` (lo resuelto).
  - Mensaje de toast del Inbox `"WhatsApp rechazó el mensaje: WhatsApp phone_number_id no configurado o ID retirado."` ya no debería aparecer porque el resolver nunca lanza por config retirada.
  - Tests: `/app/backend/tests/test_retired_phone_safety.py` actualizado con 5/5 escenarios PASS (contextvar retirado, env retirado + contextvar retirado → fallback hardcoded, env vacío → fallback hardcoded, env válido → usa env, migración limpia BD).

- [x] **P0 — Adjuntos enviados desde número WhatsApp retirado + agente envía mensajes que no llegan** - May 8, 2026:
  - **Causa raíz común**: el ID retirado `994356967089829` aparece como `WHATSAPP_PHONE_NUMBER_ID` env var en producción. Todas las llamadas a la WhatsApp Cloud API (texto del agente, adjuntos, media upload) usaban ese ID y el envío fallaba silenciosamente.
  - **Bug 2 secundario**: el endpoint `POST /api/conversations/{id}/messages` retornaba `status: "sent"` aunque la API de WhatsApp rechazara el mensaje. El agente creía que se había enviado.
  - **Fix #1 (defensivo, código)**: nuevo set `RETIRED_PHONE_NUMBER_IDS = {"994356967089829"}` y helper `_resolve_phone_number_id()` que filtra cualquier ID retirado tanto del contextvar como del env var. Si ambos son retirados o vacíos, lanza excepción clara con instrucciones.
  - **Fix #2**: los 5 helpers de envío (`send_whatsapp_message`, `send_whatsapp_template`, `send_whatsapp_document`, `upload_whatsapp_media`, `send_whatsapp_media_message`) ahora usan `_resolve_phone_number_id()` — bloquea a nivel de código cualquier intento de usar el ID retirado.
  - **Fix #3**: `POST /api/conversations/{id}/messages` y `POST /api/conversations/{id}/messages/attachment` ahora retornan **502 con detalle del error** cuando WhatsApp falla (antes retornaban 200 con `status: "sent"` engañoso). El frontend ya muestra `error.response.data.detail` en el toast → el agente ve el error real.
  - **Fix #4**: la conversación NO se marca con `last_message` actualizado cuando el envío falla (antes se actualizaba aunque el cliente no recibiera nada).
  - **Fix #5 (migración idempotente)**: nueva función `migrate_retired_phone_number_ids()` que se ejecuta en startup y limpia `wa_phone_number_id` de cualquier conversación que aún apunte a un ID retirado.
  - **Fix #6 (diagnóstico)**: el endpoint `/api/webhook/whatsapp/diagnostics` ahora marca explícitamente `RETIRED (...)` si el env var apunta a un ID retirado, con instrucciones de actualización.
  - **Acción requerida del usuario**: en producción, abrir `https://cotizador.gimmicks.com.ec/api/webhook/whatsapp/diagnostics` (autenticado). Si `whatsapp_phone_id` muestra `RETIRED`, actualizar la variable de entorno de producción al ID actual de +593 96 356 0326 y rediplegar.
  - Tests: `/app/backend/tests/test_retired_phone_safety.py` (4/4 PASS).


  - **Feature 1 — Alertas titilantes (handoff a humano)**:
    - Backend: `ConversationResponse` ahora expone `transferred_to_human`, `bot_paused`, `transfer_reason` (cargados en batch desde `conversation_states`).
    - Frontend: Punto rojo titilante (`animate-ping`) en avatar + badge "Derivada a humano" con `animate-pulse` en sidebar y header del chat.
  - **Feature 2 — Sidebar: teléfono + hora en lugar de último mensaje**:
    - El preview de mensaje se reemplaza por `+593...` con icono Phone.
    - Hora relativa: HH:mm hoy / "ayer" / día de semana / "dd MMM" (`formatRelativeTime`).
  - **Feature 3 — Adjuntos en chat**:
    - Backend: `POST /api/conversations/{id}/messages/attachment` (multipart, FastAPI UploadFile). Helpers `upload_whatsapp_media()` + `send_whatsapp_media_message()` para subir media a WhatsApp Cloud API y enviar con media_id.
    - `GET /api/conversations/attachments/{id}` para re-renderizar adjuntos previamente enviados.
    - Almacenamiento: Emergent Object Storage (`gimmicks-crm/inbox-attachments/{uuid}.{ext}`).
    - Compresión client-side de imágenes con `browser-image-compression` (5 MB max, 1920px máx). Videos ≤16 MB (límite WhatsApp). Otros archivos ≤64 MB.
    - Frontend: Botón Paperclip + `<AttachmentRenderer>` que muestra image/video/audio/documento inline en la burbuja del mensaje.
  - **Feature 4 — Control humano del bot (toma/devolución)**:
    - Backend: `POST /api/conversations/{id}/bot-control` con `{"action":"pause"|"resume"}`. Persiste `bot_paused`, `bot_paused_at`, `bot_paused_by` en `conversation_states`.
    - `bot_service.py`: chequeo temprano `if state.get("bot_paused"): return` — guarda el mensaje del cliente en BD pero NO genera respuesta.
    - Frontend: Botón "Tomar control" / "Reactivar bot" en header del chat. Badge "Bot pausado" + banner amarillo explicativo en cada conversación pausada.
  - Tests de regresión: `/app/backend/tests/test_bot_pause.py` (2/2 PASS). Smoke curl: pause/resume + attachment upload + GET — todos 200 OK.


  - **Síntoma reportado en producción**: tras enviar el mensaje de cierre exitoso, el cliente respondió "gracias" y el bot replicó "Permíteme revisar eso y en un momento te atendemos." (frase reservada para `needs_human=true`).
  - **Causa raíz**: tras generar la cotización, el estado queda `quote_generated=true` y `transferred_to_human=true`. La siguiente conversación reactiva el estado y llama al LLM. El LLM clasificaba un simple "gracias" como ambiguo → `needs_human=true` → escalado.
  - **Fix**: handler determinístico ANTES del LLM en `_process_ai_conversation_inner`. Si `state.quote_generated` y el mensaje es un agradecimiento/despedida corta (`gracias`, `muchas gracias`, `ok`, `listo`, `perfecto`, `vale`, `chao`, `hasta luego`, etc., ≤3 tokens o frases en lista cerrada), responde con un cierre cordial: *"¡A ti, [nombre]! Quedo atento si necesitas algo más."* y NO llama al LLM.
  - Tokenización limpia puntuación (`re.sub(r"[^\w\s]", " ", ...)`), por lo que `gracias!`, `muchas gracias.`, `ok!!!` se manejan igual.
  - Garantía: peticiones legítimas posteriores ("necesito gorras", "tienen otras opciones", etc.) siguen llegando al LLM normalmente.
  - Test de regresión: `/app/backend/tests/test_post_quote_farewell.py` (4/4 escenarios PASS).


  - **Síntoma reportado en producción**: Cliente escribe "tienen jarros?" y el bot responde "Aquí puedes ver las opciones de jarros con fotos y códigos: Revísalos..." pero la URL no aparece (queda el `:` huérfano).
  - **Causa raíz #1**: el tokenizador hacía `set(msg_lower.split())` sin limpiar puntuación → `"jarros?"` no matcheaba `"jarros"` en `PRODUCT_KEYWORDS` → `has_product_keyword = False`.
  - **Causa raíz #2**: con `has_product_keyword=False`, la heurística `is_answer_to_question` se activaba (mensaje ≤6 palabras + último msg del bot termina en `?`) → `should_search = False` → `catalog_link=""`.
  - **Causa raíz #3**: la IA inventaba una URL pero el regex `re.sub(r'https?://\S+', '')` la borraba porque `catalog_link` estaba vacío → quedaba "Aquí puedes ver las opciones... : Revísalos".
  - **Fix #1**: tokenización ahora limpia puntuación: `{w.strip(",.;:!?¿¡()\"'") for w in msg_lower.split()}`. Lo mismo para los `clean_terms` que arman el query del link.
  - **Fix #2**: red de seguridad post-heurísticas: si `has_product_keyword` es True, se fuerza `should_search=True` ignorando todo lo demás (excepto data input / código).
  - **Fix #3**: fallback hardcoded de URL de producción (`https://cotizador.gimmicks.com.ec`) cuando ninguna env var produce un base_url válido — el link nunca queda vacío.
  - **Fix #4**: regex final más conservadora: si `catalog_link` ya está vacío en algún edge case, NO se borran URLs `*.gimmicks.com.ec` que la IA haya incluido.
  - Verificado en 3 escenarios: producto existe (`jarros` → link filtrado), puntuación múltiple (`quiero termos!!!` → link filtrado), producto inexistente (`helicópteros teledirigidos` → link con query, sin escalado prematuro).
  - Test de regresión: `/app/backend/tests/test_jarros_link_bug.py` (3/3 escenarios PASS).

- [x] **Bot rules update + OBJETIVO_GENERAL_BOT panel rule** - May 6, 2026:
  - Nuevo bloque "OBJETIVO GENERAL DEL AGENTE" en `SYSTEM_PROMPT` como primera fuente de intención
  - Mensaje de cierre de cotización actualizado: "Nuestro equipo se pondrá en contacto contigo para los siguientes pasos" (antes: "la revisará pronto"). Aplicado tanto en prompt como en cadena hardcoded `confirm_msg`.
  - Máximo de líneas por mensaje: 3-4 → **5** (regla 2 de formato)
  - URL del catálogo explicitada en prompt: `https://cotizador.gimmicks.com.ec/catalog?q=producto` como ejemplo literal de formato
  - Lista ampliada de tipos de producto reconocidos (cuadernos, bolígrafos, camisetas, polos, paraguas, morrales, lapiceros, tomatodos, etc.)
  - Refuerzo de tono y cierre: "Quedo atento si necesitas algo más." formalizado
  - **Nueva regla del panel `OBJETIVO_GENERAL_BOT`** (insertada idempotentemente en startup vía `ensure_objetivo_general_bot()`):
    - Aparece en Configuración → Automatización (editable sin tocar código)
    - El bot la separa de las reglas regulares y la inyecta al **inicio** del `user_prompt` con la marca "PRIORIDAD MÁXIMA - PRIMERA FUENTE DE INTENCIÓN"
    - Si el admin la edita, la siguiente conversación ya respeta la nueva directriz
  - Test de regresión: `/app/backend/tests/test_objetivo_general_bot.py` (verifica BD + inyección en prompt + cambios SYSTEM_PROMPT)
  - Smoke E2E vivo: bot saluda con tildes y envía link real del catálogo cuando cliente pide "quiero termos"

## Resolved Issues
- [x] **P0 - Bot dejó de enviar el link del catálogo cuando cliente pide producto** - May 6, 2026:
  - **Síntoma reportado**: tras el deploy, el bot decía "Aquí puedes ver las opciones de cuadernos en nuestro catálogo:" pero la URL no aparecía. Cliente confundido pregunta "¿dónde puedo ver?" y el bot escala a humano.
  - **Causa raíz #1**: la heurística `is_answer_to_question` (en `bot_service.py`) marcaba como "respuesta a pregunta" cualquier mensaje ≤6 palabras enviado después de un mensaje del bot que terminaba con "?". Esto bloqueaba `should_search` y dejaba `catalog_link=""`. El AI inventaba una URL del dominio (visto en el ejemplo del prompt) y el regex `re.sub(r'https?://\S+', '')` la borraba porque catalog_link estaba vacío.
  - **Causa raíz #2**: incluso cuando la búsqueda en BD no encontraba coincidencia, no se construía un link general como fallback.
  - **Fix #1**: agregada lista `PRODUCT_KEYWORDS` (60+ palabras: cuadernos, libretas, termos, gorras, etc.) y excepción en `is_answer_to_question`: si el mensaje contiene un keyword de producto, NO se considera respuesta a pregunta.
  - **Fix #2**: `catalog_link` ahora se construye SIEMPRE que `should_search=True`, antes de evaluar si hay productos en BD. Si no hay coincidencia exacta, se sigue enviando el link al catálogo general (con el query del cliente) y el AI dice: "aquí está el catálogo, revísalo y comparte los códigos que te gusten".
  - Verificado e2e: cliente saluda → bot saluda; cliente da nombre → bot pide producto sin link; cliente dice "quiero cuadernos" → bot envía link con `?q=cuadernos`.


- [x] **P0 - Bot no debe preguntar tipos de personalización adicionales después del logo** - May 6, 2026:
  - **Regla**: una vez que el bot pregunta "¿logo a uno o varios colores?", PROHIBIDO preguntar por serigrafía, sublimación, bordado, grabado, vinil, tampografía, transfer, UV, láser, full color o cualquier otra técnica.
  - **Fix 1 — System prompt**: bloque "REGLA ABSOLUTA — UNA SOLA PREGUNTA SOBRE PERSONALIZACIÓN" añadido en la sección "CARACTERÍSTICAS DEL LOGOTIPO" con lista exhaustiva de términos prohibidos. Refuerzo también en sección "COTIZACIÓN".
  - **Fix 2 — Red de seguridad post-procesamiento**: nueva función `strip_forbidden_personalization()` que detecta menciones a esos términos en la respuesta del LLM y las elimina. Si toda la respuesta era sobre personalización, la sustituye por un mensaje seguro pidiendo el siguiente dato faltante (correo / empresa / cantidad).
  - **Inteligencia URL-aware**: la red de seguridad NO confunde palabras dentro de URLs (ej. `?q=bordado` queda intacto). Solo limpia menciones en la prosa del bot.
  - Verificado e2e: bot ya no pide "serigrafía o sublimación" cuando el cliente pregunta "¿qué más necesitas?".


- [x] **P0 - Bot responde sin tildes / acentos en español** - May 6, 2026:
  - **Causa raíz**: el `user_prompt` enviado al LLM en cada turno (en `bot_service.py`) estaba escrito SIN tildes ("INSTRUCCION", "codigos", "agente enviara catalogo", "Dirigete", etc.). El modelo imitaba el estilo del prompt y respondía sin acentos.
  - **Fix 1 — User prompt**: reescrito con todas las tildes correctas (INSTRUCCIÓN, códigos, dirígete, había, quedó, etc.).
  - **Fix 2 — System prompt**: añadido un bloque "RECORDATORIO CRÍTICO DE TILDES" justo antes del JSON de salida, con lista exhaustiva de palabras y obligación explícita de releer el campo "response" antes de responder.
  - **Fix 3 — Red de seguridad post-procesamiento**: nueva función `fix_spanish_accents()` que reemplaza ~80 palabras unívocas sin tilde por su forma correcta (cotización, atención, también, después, código, día, etc.). Conservadora: NO toca palabras ambiguas (esta/está, como/cómo, mas/más). Las palabras interrogativas solo se corrigen dentro de bloques `¿...?`.
  - **Fix 4 — Cadenas hardcodeadas**: `confirm_msg`, fallback de error y mensaje de escalamiento corregidos con tildes.
  - Verificado con conversación e2e: bot ahora responde "¿En qué puedo ayudarte?", "códigos", "catálogo", "Cuántas unidades", etc.


- [x] **P0 - Templates WhatsApp para mensajes fuera de 24h** - Abr 2026:
  - 3 plantillas creadas en Meta Business Manager: `alerta_producto_no_encontrado` (3 variables), `recordatorio_seguimiento_1`, `recordatorio_seguimiento_2`
  - Nueva función `send_whatsapp_template()` en server.py para enviar mensajes template via WhatsApp Cloud API
  - Nueva función `send_whatsapp_message_or_template()`: intenta mensaje normal primero, si falla por ventana 24h (error 131047/131026) automáticamente usa el template correspondiente
  - Recordatorio 1 (4h) → fallback a `recordatorio_seguimiento_1`
  - Recordatorio 2 (23h) → fallback a `recordatorio_seguimiento_2`
  - Alerta al agente → fallback a `alerta_producto_no_encontrado` con parámetros (nombre, teléfono, búsqueda)
  - Testing: 23/23 backend 100% (iteration_38)
- [x] **P0 - Reglas de Automatización limpiadas + Bot conectado al panel** - Abr 2026:
  - Eliminados 28 duplicados. 13 reglas finales: 10 activas + 3 desactivadas para revisión manual
  - Seed actualizado: solo inserta si `count == 0` (no más duplicados en reinicio)
  - **Bot ahora LEE reglas del panel DB**: `bot_service.py` carga `automation_rules` activas y las inyecta como "REGLAS DE AUTOMATIZACIÓN DEL SISTEMA (OBLIGATORIAS)" en el prompt de la IA
  - Si la IA no encuentra respuesta adecuada → `needs_human=true` → alerta al agente humano
  - Testing: 14/14 backend PASS (iteration_37)
- [x] **P0 - Bot no envía link del catálogo y no entiende saludos** - Abr 2026:
  - **Causa raíz 1**: `base_url` vacío en producción → link NUNCA se generaba. Fix: lee `REACT_APP_BACKEND_URL` de `os.environ`
  - **Causa raíz 2**: "Hola" activaba búsqueda → "asesor se comunicará". Fix: detección de saludos `GREETING_WORDS`
  - **Causa raíz 3**: PASO 1 no era estricto → bot pedía códigos al saludar. Fix: "UNICAMENTE saludo cordial, NO pidas codigos, NO menciones cotizaciones"
  - **Causa raíz 4**: Bot decía "agente enviará catálogo" aunque SÍ había productos. Fix: "PROHIBIDO decir agente enviará catalogo si hay productos. TU envías el link"
  - **Reglas implementadas**: (1) Saludo cordial + "¿En qué puedo ayudarte hoy?", (2) Leer 20+ msgs, (3) SIEMPRE link interno OBLIGATORIO, (4) Códigos solo después del link, (5) "agente enviará catálogo" SOLO sin productos
  - **Número agente actualizado**: +593 96 356 0326
  - Testing: 30/30 backend 100% (iteration_35 + iteration_36)
- [x] **P0 - Múltiples usuarios no pueden ingresar simultáneamente** - Abr 2026:
  - **Causa raíz**: Rate limiter usaba `request.client.host` que devuelve la IP del proxy (Railway). Todos los usuarios compartían la misma IP → 15 intentos totales entre TODOS → bloqueo (429)
  - **Fix**: Nuevo helper `get_client_ip()` que lee `X-Forwarded-For` y `X-Real-IP` para obtener la IP real de cada usuario
  - **Fix**: `MAX_LOGIN_ATTEMPTS` aumentado de 15 a 50
  - Testing: 20 logins rápidos consecutivos todos exitosos (iteration_34)
- [x] **P0 - Sistema no funciona en Firefox ni Edge** - Abr 2026:
  - **Causa raíz**: CORS configurado con `allow_credentials=True` + `allow_origins=["*"]` → INVÁLIDO per spec CORS. Chrome lo tolera, Firefox/Edge lo bloquean completamente
  - **Fix**: Auth migrado de cookies a Bearer token via `localStorage` como mecanismo principal
  - **Fix**: CORS simplificado: `allow_origins=["*"]` SIN `allow_credentials` → compatible con TODOS los navegadores
  - **Fix**: `AuthContext.js`: token persiste en `localStorage`, se restaura al recargar, se envía como `Authorization: Bearer` header
  - **Fix**: Eliminado `withCredentials=true` de axios (causaba el bloqueo CORS)
  - Testing: sesión persiste tras refresh, login/logout funcional, 6/6 UI tests (iteration_34)
- [x] **P0 - Refactorización flujo conversacional bot WhatsApp** - Abr 2026:
  - **Regla 1**: PASO 1 saluda SIN pedir nombre. "Hola, soy Ana de Gimmicks. En que puedo ayudarte?"
  - **Regla 2**: PASO 2 prioriza búsqueda de producto y envío de link interno `/catalog?q=keyword` ANTES de pedir nombre o datos
  - **Regla 2b**: Cuando NO hay productos → alerta inmediata al agente humano (+593999440910) por WhatsApp. NO se pide email para catálogo
  - **Regla 3**: NUNCA se menciona número de cotización. `quote_context` eliminó `#{quote_number}`. Regla estricta en prompt
  - PASO reordenado: Saludo → Producto → Nombre → Códigos → Datos adicionales
  - Testing: 15/15 backend 100% (iteration_32)
- [x] **P0 - 4 reglas nuevas del bot WhatsApp** - Abr 2026:
  - Regla 1: Mensajes cortos, de manera natural, sin emojis (PERSONALIDAD actualizada)
  - Regla 2: Pide "nombre y apellido" (PASO 3), datos personales SOLO después de entender artículos (PASO 5)
  - Regla 3: Primer recordatorio a las 4h solo para etapas "Lead"/"Cliente potencial" con mensaje exacto del usuario
  - Regla 4: Segundo recordatorio a las 23h solo para etapas "Lead"/"Cliente potencial" con mensaje exacto del usuario
  - Filtro de etapas: recordatorios NO se envían a "cotizacion_generada", "pedido", "perdido"
  - Testing: 15/15 backend 100% (iteration_33)
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
- [x] **P0 - Fix Railway deploy: emergentintegrations** - Abr 8, 2026
- [x] **P0 - Bot fallback LLM (gpt-5.2 → gpt-4o)** - Abr 8, 2026
- [x] **P0 - Bot enviando mensajes repetidos en loop** - Abr 8, 2026
- [x] **P0 - Error autenticación tras deploy Railway** - Abr 8, 2026
- [x] **P0 - Login intermitente** - Abr 8, 2026: Cookie SameSite=None→Lax, path=/→/, Bearer backup en frontend, rate limit 5→15
- [x] **P1 - Auditoría completa rendimiento + datos** - Abr 8, 2026
- [x] **Ajuste PDF Proforma (logo -30%, espacio -50%)** - Abr 8, 2026
- [x] **P0 - PDF grande bloquea servidor completo** - Abr 8, 2026:
  - **Causa raíz**: Generación PDF síncrona bloqueaba event loop → servidor dejaba de responder → sesión expirada → errores en cascada
  - **Fix**: `asyncio.to_thread()` para PDF, ThreadPoolExecutor(5 workers) para imágenes, timeout 15s global
  - **Verificado**: Server responde en 12-79ms DURANTE generación de PDF con 67 items

## Resolved Issues (Security)
- [x] **P0 - Vulnerabilidad DoS en activity-chart** - Abr 2026:
  - **Causa raíz**: `days` parámetro controlado por usuario usado directamente en `range(days)` sin validación → loop de millones de iteraciones + queries MongoDB masivas
  - **Fix**: `restricted_days = max(1, min(90, days))` — limita rango a 1-90 días
  - **Verificado**: 6/6 tests (normal, default, max, DoS attack, zero, negative) todos correctos
- [x] **P0 - Orden incorrecto de middleware CORS** - Abr 2026:
  - **Fix**: Reordenado para que CORS sea la última llamada (capa más externa)
- [x] **P0 - Bot envía [LINK] literal en vez de URL real del catálogo** - Abr 2026:
  - **Causa raíz**: System prompt y user prompt usaban `[LINK]` como ejemplo → AI lo copiaba literalmente en vez de la URL
  - **Fix 1**: Prompts actualizados con prohibición explícita de placeholders y ejemplos con URL real
  - **Fix 2**: Post-procesamiento: regex reemplaza `[LINK]`, `[link]`, `(link)`, `{link}` por la URL real del catálogo
  - **Fix 3**: Regla de automatización "Link catalogo obligatorio - prohibido [LINK]" creada en panel
  - **Triple red de seguridad**: (1) Prompt prohíbe placeholders, (2) regex los reemplaza, (3) fallback appends URL si falta
- [x] **Feature - Gestión masiva de Reglas de Automatización** - Abr 2026:
  - **Descargar Excel**: `GET /api/automation-rules/export-excel` genera .xlsx con estilo, todas las columnas
  - **Cargar Excel**: `POST /api/automation-rules/import-excel` importa reglas desde .xlsx (agrega a existentes)
  - **Borrar Todas**: `DELETE /api/automation-rules-bulk/delete-all` elimina todas las reglas con confirmación
  - Frontend: 3 botones en panel Configuración > Automatización con confirmaciones y toasts
- [x] **P0 - Limpieza de reglas de automatización + fix sync duplicación** - Abr 2026:
  - Eliminadas 68 reglas (masivamente duplicadas por sync_service que re-insertaba 18 reglas de producción)
  - Curadas exactamente 12 reglas esenciales para el flujo del bot
  - **Fix sync_service**: `automation_rules` removido de COLLECTIONS_TO_SYNC (ya no se pull de producción)
  - **Sync bidireccional**: Nueva función `_sync_rules_to_production()` — cada CRUD en el panel replica INMEDIATAMENTE a producción
  - El bot en producción AHORA lee las mismas reglas del panel del usuario
  - Backup guardado en `/app/backups/reglas_backup_antes_limpieza.xlsx`
- [x] **P0 - Error autenticación tras deploy Railway** - Abr 2026:
  - **Causa raíz**: `static_frontend` se construía con `REACT_APP_BACKEND_URL=https://...preview.emergentagent.com` del preview → en producción Railway, el frontend enviaba API calls al preview en vez del servidor local
  - **Fix**: Build con `REACT_APP_BACKEND_URL=""` → rutas relativas (`/api/...`) que funcionan en cualquier dominio
  - Verificado: 0 referencias a preview URL en el build, rutas API relativas confirmadas
  - 3 mensajes de producción (18:21-18:26) no recibieron respuesta del bot
  - **Causa**: Redeploy automático de Railway durante cambios de código (servidor reiniciándose)
  - **Verificado**: Webhook funcional, LLM (GPT-5.2) funcional, API WhatsApp funcional, flujo completo testeado
  - `static_frontend` reconstruido para próximo deploy estable

## Remaining Tasks
1. **P0 - Re-subir inventario con imágenes**: Esta copia alterna usa solo Emergent local. Las imágenes de los 1,284 productos referencian UUIDs que no existen en `product_images`. Re-cargar Excel + imágenes vía la página de Inventario.
2. **P1 - Validación end-to-end del bot**: Confirmar que el bot consulta inventario solo desde la DB local y que el link del catálogo muestra los productos esperados.
3. **P2 - Refactor bot_service.py**: Split into smaller modules
4. **P2 - Refactor large frontend components**: Extract modals
5. **P3 - Asesor permission audit**: Full audit of role permissions

## Resolved Issues (May 2026 - Copia alterna en Emergent)
- [x] **Imágenes de productos migradas a Emergent Object Storage** - May 4, 2026:
  - Causa: Las URLs `/api/inventory/images/<UUID>` del Excel apuntaban a binarios que no existían en MongoDB local ni en Railway. Los binarios sí existían en otra instancia de Emergent (`merged-platform-3.emergent.host`)
  - Implementado **Emergent Object Storage** (`services/object_storage.py`) — almacenamiento seguro en la nube, escalable, separado de MongoDB
  - `init_storage()` se llama una vez al startup; `storage_key` reutilizable en memoria
  - Endpoint `POST /api/inventory/upload-image` ahora guarda primero en Object Storage, con fallback a MongoDB si Object Storage no disponible
  - Endpoint `GET /api/inventory/images/{id}` lee de Object Storage si hay `storage_path`, si no usa el binario en Mongo (compatibilidad total con flujo existente)
  - Migración: 1,520/1,520 (100%) imágenes copiadas desde `merged-platform-3` → Object Storage. 0 errores tras retry
  - Esquema `product_images` ahora: `{id, storage_path, content_type, size, is_deleted, created_at}` + soft-delete soportado
  - Verificado: catálogo público, página Inventario y endpoints de imagen funcionan en 200 con tiempos ~300ms (más cache de 1 año en navegador via Cache-Control header)

- [x] **Eliminada dependencia de Railway** - May 4, 2026:
  - Removido `services/sync_service.py` y `BackgroundSyncTask` (que jalaba leads/conversations/messages/product_images desde Railway cada 120s)
  - Removido `get_prod_db()` y `_sync_rules_to_production()` ahora es no-op
  - Removidas variables de entorno `PROD_MONGO_URL` / `PROD_DB_NAME` del `backend/.env`
  - Removidos archivos de Railway: `railway.toml`, `Procfile`, `start.py`
  - Endpoints `/api/sync/production` y `/api/sync/status` retornan ahora `{"disabled": true, "message": "Railway sync deshabilitado..."}` (mantenidos como stubs para no romper UI antiguo)
  - Esta instancia ahora usa **únicamente** la MongoDB local de Emergent (`MONGO_URL`)
  - El sistema de producción (publicado) NO fue tocado

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
