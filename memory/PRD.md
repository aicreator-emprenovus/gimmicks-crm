# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público. Fusionado con Cotizador Gimmicks.

## Architecture
- **Backend**: FastAPI + MongoDB (motor async) + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP (aicreator@emprenovus.com)
- **WhatsApp Notifications**: Alertas al 593963266566

## Completed Tasks

### Core System (Feb 18, 2026)
- Fusión Proyecto A + B, Inventory V2, Quotes V2 con PDF, Clientes CRUD, Dashboard, Bot WhatsApp

### UI/UX (Feb 18-19, 2026)
- Imágenes con compresión, QuoteBuilder rediseño, Catálogo público, tildes/colores

### Fix Bot + Chat + SMTP (Feb 19, 2026)
- emergentintegrations limpio, Inbox polling 5s, Gmail SMTP

### Fix Cotizaciones Bot + Notificaciones (Feb 19, 2026)
- 27+ field aliases, match_qty() flexible, has_full_data mejorado
- Notificaciones WhatsApp NUEVA/ACTUALIZADA al 593963266566

### Sección "Interesados" + Test E2E (Feb 19, 2026)
- Campo `source` en Client ("manual" | "whatsapp")
- `POST /api/clients/{id}/promote` para mover Interesados → Clientes
- `Interesados.jsx` con cards + botón promover
- Prompt del bot mejorado: extrae TODOS los datos de cada mensaje
- auto_create_client y upsert_quote con source="whatsapp" y client_name desde empresa
- **Test E2E exitoso**: 2 clientes simulados (Laura García, Roberto Mendoza) - flujo completo conversación → cotización → interesado → notificación staff
- Testing iterations 11-13: 100% pass rate

## Key Files
- `backend/bot_service.py` - Bot AI (prompt, field_aliases, upsert_quote, notify_staff, auto_create_client)
- `backend/routes/clients_routes.py` - CRUD + promote
- `frontend/src/pages/Interesados.jsx` - WhatsApp prospects
- `frontend/src/pages/Clients.jsx` - Manual clients (source=manual)
- `frontend/src/pages/Inbox.jsx` - Chat con polling 5s
- `frontend/src/components/Layout.jsx` - Nav con Interesados

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com
- Staff: 593963266566

## Remaining Tasks
1. **P0 - Deploy to Railway**: Guardar en GitHub y redesplegar
2. **P2 - Refactoring**: Split bot_service.py y Leads.jsx
3. **P3 - Asesor role**: Finalizar restricciones
