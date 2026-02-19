# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público. Fusionado con Cotizador Gimmicks para módulos avanzados de inventario, cotizaciones con PDF, clientes y órdenes de compra.

## Architecture
- **Backend**: FastAPI (Python) - `/app/backend/server.py` + modular routes in `/app/backend/routes/`
- **Frontend**: React + Shadcn/UI + TailwindCSS + Recharts
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT (bcrypt)
- **Bot**: GPT-4o via Emergent LLM Key (`emergentintegrations` library)
- **PDF**: ReportLab
- **Email**: Gmail SMTP (aicreator@emprenovus.com) - CONFIGURED AND WORKING
- **WhatsApp Notifications**: Staff alerts to 593963266566 on new/updated quotes

## Completed Tasks

### FASE 1-5: Core System - COMPLETADA (Feb 18, 2026)
- Auditoría y fusión de Proyecto A (CRM) y Proyecto B (Cotizador)
- Inventory V2, Quotes V2 con PDF, Clientes CRUD, Dashboard con métricas reales
- Dual schema support, Testing E2E 100% pass rate
- Bot WhatsApp adaptado para quotes_v2 + auto-crear clientes

### Mejoras UI/UX - COMPLETADAS (Feb 18-19, 2026)
- Carga de imágenes con compresión en modal de producto
- Ver detalle de clientes, exportar Excel
- Rediseño completo QuoteBuilder (catálogo izquierda + cotización derecha)
- Catálogo público con filtro de categorías y UI mejorada
- Corrección de tildes y colores en toda la aplicación

### Fix Bot Producción + Chat Tiempo Real + SMTP - COMPLETADO (Feb 19, 2026)
- **emergentintegrations limpio**: Eliminados todos los fallbacks try/except ImportError
- **requirements.txt**: Correcto con --extra-index-url y emergentintegrations==0.1.0
- **Chat en tiempo real**: Inbox.jsx polling cada 5 segundos con indicador de sincronización
- **SMTP configurado**: Gmail (aicreator@emprenovus.com) funcionando

### Fix Cotizaciones Bot + Notificaciones WhatsApp - COMPLETADO (Feb 19, 2026)
- **Field aliases expandidos**: 27+ aliases para normalizar variantes del LLM (correo_electronico→correo, cantidad_unidades→cantidad, ciudad_de_entrega→ciudad, etc.)
- **Matching flexible de cantidades**: Función `match_qty()` que resuelve códigos parciales (ej: "JARVID00020" matchea con "JARVID00020 - AZ")
- **has_full_data mejorado**: Acepta tanto `cantidad` como `cantidades_por_producto` para validar datos completos
- **Keyword detection**: Detecta cuando el usuario pide cotizar/actualizar sin depender del LLM setting `needs_quote`
- **Notificaciones WhatsApp al staff**: Envía alertas automáticas al 593963266566 con detalles de cotización NUEVA o ACTUALIZADA
- **Quote update sin duplicados**: Cotizaciones existentes se actualizan en lugar de crear nuevas
- Testing iteration 12: 100% pass rate (13/13 tests)

## Key Files
### Backend
- `/app/backend/server.py` - Main server
- `/app/backend/bot_service.py` - WhatsApp bot AI logic (field_aliases, upsert_quote, match_qty, notify_staff_new_quote)
- `/app/backend/routes/inventory_routes.py` - Inventory V2 API
- `/app/backend/routes/quotes_routes.py` - Quotes V2 API with PDF
- `/app/backend/routes/clients_routes.py` - Clients CRUD API
- `/app/backend/services/email_service.py` - Email service (Gmail SMTP)

### Frontend
- `/app/frontend/src/pages/Inbox.jsx` - WhatsApp Inbox with real-time polling (5s)
- `/app/frontend/src/pages/QuoteBuilder.jsx` - Quote builder with cart
- `/app/frontend/src/pages/Clients.jsx` - Clients module
- `/app/frontend/src/pages/Inventory.jsx` - Inventory V2

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com (Gmail App Password configured)
- Staff notification: 593963266566

## Remaining/Future Tasks
1. **P0 - Deploy to Railway**: Guardar cambios en GitHub y redesplegar para que funcione en producción
2. **P2 - Refactoring**: Split bot_service.py (~1000 líneas) y Leads.jsx en módulos más pequeños
3. **P3 - Asesor role**: Finalizar restricciones del rol asesor
