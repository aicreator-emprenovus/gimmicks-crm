# Gimmicks CRM - WhatsApp Business Integration

## Original Problem Statement
Build a web-based CRM integrated with WhatsApp Business to manage a conversational sales funnel for Gimmicks Marketing Services.

## Tech Stack
- **Backend**: FastAPI, Python, Motor (async MongoDB), JWT Auth
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Database**: MongoDB
- **Integrations**: WhatsApp Business Cloud API, OpenAI GPT-4o-mini (via Emergent LLM Key)
- **AI Library**: emergentintegrations (LlmChat)

## What's Been Implemented

### Completed (January 2026)
- [x] Backend API with FastAPI + JWT auth
- [x] WhatsApp webhook configured with permanent token
- [x] Core UI pages: Login, Dashboard, Inbox, Leads, Inventory, Settings, Users
- [x] Real-time conversation display and message sending
- [x] Automation rules (keyword-based, new lead triggers)
- [x] Conversation management (star/save, clear, delete)

### Completed (February 13, 2026)
- [x] Sidebar cleanup + collapsible sidebar
- [x] Light theme for content areas + teal color palette (#7BA899)
- [x] Rule-based bot flow (now superseded by AI bot)

### Completed (February 13, 2026 - AI Bot)
- [x] **AI-powered conversational bot** (bot_service.py):
  - Uses GPT-4o-mini via emergentintegrations LlmChat
  - Natural language understanding - no rigid state machine
  - Extracts lead data progressively from conversation: nombre, empresa, ciudad, correo, producto, cantidad, fecha_entrega, presupuesto, personalizacion
  - Classifies lead quality: caliente / tibio / frio
  - Auto-categorizes: cotizacion_directa / solicitud_catalogo / consulta_ideas / pedido_estacional / otra
  - Generates quotes when enough data collected (nombre + empresa + correo + producto + cantidad)
  - Auto-transfers to Ana Maria with summary after quote
  - Updates lead record in real-time with AI-extracted data
- [x] **Lead model enhanced** with new fields: ai_category, empresa, ciudad, correo, producto_interes, cantidad_estimada, presupuesto
- [x] **Leads UI updated** (Leads.jsx):
  - Quality badges (Frio/Tibio/Caliente) with color-coded dots
  - AI category tags visible on cards
  - Empresa, ciudad, producto shown on cards
  - Detail dialog (eye icon) showing all collected data
  - All existing functionality preserved (Kanban, filters, search, edit, delete)

## Bot Flow (AI-Driven)
1. Customer writes anything -> AI understands intent naturally
2. AI responds conversationally, asks for missing data
3. Extracts entities from each message (name, company, email, etc.)
4. Updates lead quality and category in real-time
5. When 5 required fields collected -> Generates quote -> Sends to customer
6. Transfers to Ana Maria with full summary -> Lead marked as "pedido"

## Pending Tasks

### P1 - Medium Priority
- [ ] Implement Excel inventory upload (UI + backend connection)
- [ ] Dashboard real metrics implementation
- [ ] Deploy AI bot to production Railway (currently local only)

### P2 - Lower Priority
- [ ] Finalize Asesor role restrictions
- [ ] Refactor server.py into modules (routes, models, services)

## Access Credentials
- **Email**: admin@gimmicks.com
- **Password**: admin123456

## URLs
- **Preview**: https://whatsapp-crm-flow.preview.emergentagent.com
- **Backend (Railway)**: https://gimmicks-crm-production.up.railway.app

## Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/bot_service.py` - AI bot service (NEW)
- `/app/frontend/src/pages/Leads.jsx` - Leads page with AI data
- `/app/frontend/src/components/Layout.jsx` - Sidebar layout
