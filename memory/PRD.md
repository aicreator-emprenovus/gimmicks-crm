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

### Core System
- [x] Backend API with FastAPI + JWT auth
- [x] WhatsApp webhook with permanent token
- [x] Core UI: Login, Dashboard, Inbox, Leads, Inventory, Settings, Users
- [x] Real-time conversations, message sending
- [x] Collapsible sidebar, light theme, teal palette (#7BA899)

### AI Bot (bot_service.py)
- [x] GPT-4o-mini powered conversational bot via emergentintegrations
- [x] Human-like tone - acts as sales advisor "Ana"
- [x] Natural language understanding - no rigid state machine
- [x] Progressive lead data extraction: nombre, empresa, ciudad, correo, producto, codigos_producto, cantidad, fecha_entrega, personalizacion
- [x] Lead quality scoring: caliente / tibio / frio
- [x] Auto-categorization: cotizacion_directa, solicitud_catalogo, consulta_ideas, pedido_estacional, otra
- [x] **Dynamic catalog links**: When client asks about a product, sends public catalog URL
- [x] **Code-based quoting**: Validates product codes, creates pending quote for admin review
- [x] Redirects any question back to commercial action

### Public Catalog (/catalog?q=keyword)
- [x] Public page - NO login required
- [x] Shows filtered products with photo, name, description, and CODE
- [x] Responsive design (mobile-friendly for WhatsApp users)
- [x] Search functionality
- [x] Backend: /api/catalog/public endpoint (no auth)
- [x] Placeholder for products without images

### Quotes Management (/quotes)
- [x] Quotes page for admin review
- [x] Pending/Sent status badges
- [x] View detail dialog with all client data and products
- [x] Edit dialog (total, notes)
- [x] "Enviar" button to send quote via email (requires SMTP config)
- [x] Delete quote functionality

### Pipeline CRM (Auto)
- [x] 5 stages: Lead > Cliente Potencial > Cotizacion Generada > Pedido > Perdido
- [x] Bot auto-updates pipeline based on conversation progress
- [x] Kanban board in Leads page with all stages
- [x] Legacy data migrated to new stages

### Follow-up System
- [x] Background task checks every 30 minutes
- [x] 4-hour reminder via WhatsApp
- [x] 24-hour mark as "Perdido"
- [x] Auto-reactivation when client responds
- [x] Manual trigger: POST /api/followup/check
- [x] Audit logs for all actions

### Bot Flow
1. Client writes -> AI understands intent
2. If asks about products -> sends public catalog LINK with photos and codes
3. Client reviews catalog -> shares codes back
4. Bot collects: codes + cantidad + correo + ciudad + personalizacion + fecha
5. Creates pending quote for admin review
6. Admin reviews -> edits total/notes -> sends to client email

## Pending Tasks

### P0 - Immediate
- [ ] Configure SMTP credentials for email sending
- [ ] Deploy to production (Save to GitHub -> Railway)

### P1 - Medium Priority
- [ ] Excel inventory upload UI
- [ ] Dashboard real metrics
- [ ] CATALOG_BASE_URL update for production domain

### P2 - Lower Priority
- [ ] Asesor role restrictions
- [ ] Refactor server.py into modules

## Key Files
- `/app/backend/server.py` - Main API server
- `/app/backend/bot_service.py` - AI bot service
- `/app/frontend/src/pages/PublicCatalog.jsx` - Public catalog
- `/app/frontend/src/pages/Quotes.jsx` - Quotes management
- `/app/frontend/src/pages/Leads.jsx` - Leads with pipeline
- `/app/frontend/src/components/Layout.jsx` - Sidebar

## Access
- **Email**: admin@gimmicks.com / **Password**: admin123456
- **Preview**: https://whatsapp-crm-flow.preview.emergentagent.com
- **Public Catalog**: https://whatsapp-crm-flow.preview.emergentagent.com/catalog?q=jarro
- **Backend (Railway)**: https://gimmicks-crm-production.up.railway.app
