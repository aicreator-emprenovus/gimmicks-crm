# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público. Fusionado con Cotizador Gimmicks para módulos avanzados de inventario, cotizaciones con PDF, clientes y órdenes de compra.

## Architecture
- **Backend**: FastAPI (Python) - `/app/backend/server.py` + modular routes in `/app/backend/routes/`
- **Frontend**: React + Shadcn/UI + TailwindCSS + Recharts
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT (bcrypt)
- **Bot**: GPT-4o via Emergent LLM Key (emergentintegrations library)
- **PDF**: ReportLab
- **Email**: Gmail SMTP (aicreator@emprenovus.com) - CONFIGURED AND WORKING

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
- **emergentintegrations limpio**: Eliminados todos los fallbacks try/except ImportError a openai SDK en bot_service.py y server.py. Ahora usa emergentintegrations directamente
- **requirements.txt**: Correcto con --extra-index-url y emergentintegrations==0.1.0
- **Chat en tiempo real**: Inbox.jsx ahora hace polling de mensajes cada 5 segundos con indicador visual de sincronización y scroll inteligente solo en mensajes nuevos
- **SMTP configurado**: Gmail SMTP (aicreator@emprenovus.com) funcionando. Envío de cotizaciones por correo verificado
- Testing iteration 11: 100% pass rate

## Key Files
### Backend
- `/app/backend/server.py` - Main server
- `/app/backend/bot_service.py` - WhatsApp bot AI logic
- `/app/backend/routes/inventory_routes.py` - Inventory V2 API
- `/app/backend/routes/quotes_routes.py` - Quotes V2 API with PDF
- `/app/backend/routes/clients_routes.py` - Clients CRUD API
- `/app/backend/routes/dashboard_routes.py` - Dashboard V2 real stats
- `/app/backend/services/email_service.py` - Email service (Gmail SMTP)
- `/app/backend/models_b.py` - Pydantic models for V2 modules

### Frontend
- `/app/frontend/src/pages/Dashboard.jsx` - Real metrics dashboard
- `/app/frontend/src/pages/Inventory.jsx` - Inventory V2
- `/app/frontend/src/pages/Clients.jsx` - Clients module
- `/app/frontend/src/pages/QuoteBuilder.jsx` - Quote builder with cart
- `/app/frontend/src/pages/QuoteHistory.jsx` - Quote/PO history with PDF
- `/app/frontend/src/pages/Inbox.jsx` - WhatsApp Inbox with real-time polling
- `/app/frontend/src/pages/Leads.jsx` - Leads Kanban

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com (Gmail App Password configured)

## Remaining/Future Tasks
1. **P1 - Deploy to Railway**: Guardar cambios en GitHub y redesplegar en Railway para que el bot funcione en producción
2. **P2 - Refactoring**: Split bot_service.py y Leads.jsx en módulos más pequeños
3. **P3 - Asesor role**: Finalizar restricciones del rol asesor
4. **P3 - PublicCatalog improvements**: Integrar mejoras del Proyecto B
