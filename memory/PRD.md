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
- **Email**: Gmail SMTP (aicreator@emprenovus.com)
- **WhatsApp Notifications**: Staff alerts to 593963266566

## Completed Tasks

### FASE 1-5: Core System (Feb 18, 2026)
- Fusión de Proyecto A (CRM) y Proyecto B (Cotizador)
- Inventory V2, Quotes V2, Clientes CRUD, Dashboard, Bot WhatsApp

### Mejoras UI/UX (Feb 18-19, 2026)
- Imágenes con compresión, QuoteBuilder rediseño, Catálogo público, tildes/colores

### Fix Bot + Chat Tiempo Real + SMTP (Feb 19, 2026)
- emergentintegrations limpio, Inbox polling 5s, Gmail SMTP configurado

### Fix Cotizaciones Bot + Notificaciones WhatsApp (Feb 19, 2026)
- 27+ field aliases, match_qty() flexible, has_full_data mejorado
- Notificaciones WhatsApp NUEVA/ACTUALIZADA al 593963266566
- Testing iteration 12: 100% pass rate

### Sección "Interesados" - COMPLETADO (Feb 19, 2026)
- Nuevo campo `source` en modelo Client ("manual" | "whatsapp")
- `GET /api/clients/?source=manual` para Clientes, `?source=whatsapp` para Interesados
- `POST /api/clients/{id}/promote` para mover de Interesados → Clientes
- Nueva página `Interesados.jsx` con cards + botón "Promover a Cliente"
- Menú actualizado con "Interesados" entre Clientes y Leads
- `_create_client_from_lead` ahora crea con `source: "whatsapp"`
- Migración de datos existentes completada
- Testing iteration 13: 100% pass rate

## Key Files
### Backend
- `/app/backend/server.py` - Main server
- `/app/backend/bot_service.py` - WhatsApp bot AI logic
- `/app/backend/routes/clients_routes.py` - Clients CRUD + promote endpoint
- `/app/backend/routes/inventory_routes.py` - Inventory V2
- `/app/backend/routes/quotes_routes.py` - Quotes V2 with PDF
- `/app/backend/services/email_service.py` - Gmail SMTP
- `/app/backend/models_b.py` - Pydantic models (Client has source field)

### Frontend
- `/app/frontend/src/pages/Interesados.jsx` - WhatsApp prospects page
- `/app/frontend/src/pages/Clients.jsx` - Manual clients (filtered source=manual)
- `/app/frontend/src/pages/Inbox.jsx` - WhatsApp Inbox with polling
- `/app/frontend/src/pages/QuoteBuilder.jsx` - Quote builder
- `/app/frontend/src/components/Layout.jsx` - Nav with Interesados item
- `/app/frontend/src/App.js` - Routes including /interesados

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com
- Staff notification: 593963266566

## Remaining/Future Tasks
1. **P0 - Deploy to Railway**: Guardar en GitHub y redesplegar
2. **P2 - Refactoring**: Split bot_service.py y Leads.jsx
3. **P3 - Asesor role**: Finalizar restricciones del rol asesor
