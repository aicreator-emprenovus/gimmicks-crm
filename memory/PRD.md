# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP (aicreator@emprenovus.com)
- **WhatsApp Notifications**: Alertas al 593963266566

## Completed Tasks

### Core System (Feb 18, 2026)
- Fusión Proyecto A + B, Inventory V2, Quotes V2, Clientes, Dashboard, Bot WhatsApp

### UI/UX (Feb 18-19, 2026)
- Imágenes, QuoteBuilder, Catálogo público, tildes/colores

### Fix Bot + Chat + SMTP (Feb 19, 2026)
- emergentintegrations limpio, Inbox polling 5s, Gmail SMTP

### Cotizaciones Bot + Notificaciones (Feb 19, 2026)
- Field aliases, match_qty(), Notificaciones WhatsApp al staff

### Sección "Interesados" (Feb 19, 2026)
- Campo `source` ("manual" | "whatsapp"), Interesados.jsx, botón promover

### Flujo Interesado → Cliente (Feb 19, 2026)
- **Bot cotiza → Interesado**: Al crear cotización desde WhatsApp, el registro queda como `source: "whatsapp"` (interesado). NO se promueve automáticamente
- **Lead "Entregado" → Cliente**: Solo cuando el lead se mueve manualmente a "Entregado" en el Kanban, el interesado se promueve a `source: "manual"` (cliente)
- **Papelera → Re-registro**: Si un interesado/cliente se envía a papelera (`is_deleted: True`), al escribir de nuevo por WhatsApp se re-registra como nuevo interesado desde cero
- `_create_client_from_lead` busca interesado existente y lo promueve en vez de crear duplicado
- Test E2E verificado: cotización → interesado → entregado → cliente → papelera → re-registro

## Key Files
- `backend/bot_service.py` - Bot AI, auto_create_client (source=whatsapp)
- `backend/server.py` - _create_client_from_lead (promote on entregado)
- `backend/routes/clients_routes.py` - CRUD + promote + source filter
- `frontend/src/pages/Interesados.jsx` - WhatsApp prospects
- `frontend/src/pages/Clients.jsx` - Manual clients
- `frontend/src/components/Layout.jsx` - Nav con Interesados

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com
- Staff: 593963266566

## Remaining Tasks
1. **P0 - Deploy to Railway**: Guardar en GitHub y redesplegar
2. **P2 - Refactoring**: Split bot_service.py y Leads.jsx
3. **P3 - Asesor role**: Finalizar restricciones
