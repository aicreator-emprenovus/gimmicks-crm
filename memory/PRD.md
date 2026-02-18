# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público y ahora módulos avanzados del Cotizador Gimmicks.

## Architecture
- **Backend**: FastAPI (Python) - `/app/backend/server.py` + modular routes in `/app/backend/routes/`
- **Frontend**: React + Shadcn/UI + TailwindCSS - `/app/frontend/src/`
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT (bcrypt)
- **Bot**: GPT-4o via Emergent LLM Key
- **Hosting**: Railway (production), Emergent (preview)

## Core Modules (Proyecto A - Intactos)
- Auth (login/registro JWT)
- WhatsApp Inbox (conversations + bot)
- Leads Kanban Board
- Users Management
- Settings (automation rules)
- Public Catalog (/catalog)

## Merged Modules from Proyecto B (FASE 2 - Completado Feb 18, 2026)
- **Inventory V2** (`/api/inventory/`): Pagination, categories array, cost/supplier, image upload, Excel upload, export
- **Clients** (`/api/clients/`): Full CRUD, soft delete, trash, restore, history, activity log, sectors
- **Quotes V2** (`/api/quotes-v2/`): QuoteBuilder with cart, discounts, additional values, PDF generation (reportlab), email sending, Quotes/PO tabs, trash/restore, activity log
- **Dashboard V2** (`/api/dashboard-v2/`): Real stats (products, clients, quotes, POs, leads), activity chart, top products, top clients

## Key Files
### Backend
- `/app/backend/server.py` - Main server (routes + bot logic + WhatsApp webhook)
- `/app/backend/routes/inventory_routes.py` - Inventory V2 API
- `/app/backend/routes/quotes_routes.py` - Quotes V2 API with PDF
- `/app/backend/routes/clients_routes.py` - Clients CRUD API
- `/app/backend/routes/dashboard_routes.py` - Dashboard V2 stats
- `/app/backend/services/email_service.py` - Email service (Gmail SMTP + Resend)
- `/app/backend/models_b.py` - Pydantic models for V2 modules
- `/app/backend/bot_service.py` - WhatsApp bot AI logic

### Frontend
- `/app/frontend/src/pages/Inventory.jsx` - Inventory (replaced with B)
- `/app/frontend/src/pages/Clients.jsx` - Clients (NEW from B)
- `/app/frontend/src/pages/QuoteBuilder.jsx` - Quote Builder (NEW from B)
- `/app/frontend/src/pages/QuoteHistory.jsx` - Quote History (NEW from B)
- `/app/frontend/src/pages/Inbox.jsx` - WhatsApp Inbox (A intact)
- `/app/frontend/src/pages/Leads.jsx` - Leads Kanban (A intact)
- `/app/frontend/src/components/Layout.jsx` - Sidebar navigation

## DB Collections
- `users`, `leads`, `conversations`, `messages` (Proyecto A)
- `products` (shared - both schemas supported)
- `quotes` (old - for bot compatibility)
- `quotes_v2` (new - Proyecto B quotes/POs)
- `clients`, `client_activities`, `document_activities` (new from B)
- `automation_rules` (Proyecto A)

## Mocked/Pending
- **Email sending**: MOCKED (no SMTP/Resend/Gmail credentials configured)
- **Dashboard (old)**: Still returns mocked data at `/api/dashboard/metrics`

## API Endpoints
### V2 (New from Proyecto B)
- `GET/POST /api/inventory/` - Products with pagination
- `POST /api/inventory/upload` - Excel upload
- `GET /api/inventory/categories` - Product categories
- `POST /api/inventory/upload-image` - Image upload
- `PUT/DELETE /api/inventory/{code}` - Product CRUD
- `GET/POST /api/clients/` - Clients CRUD
- `PUT/DELETE /api/clients/{id}` - Client update/delete
- `POST /api/clients/{id}/restore` - Restore from trash
- `GET /api/clients/{id}/history` - Client history
- `GET/POST /api/quotes-v2/` - Quotes/POs CRUD
- `PUT/DELETE /api/quotes-v2/{id}` - Quote update/delete
- `POST /api/quotes-v2/{id}/generate-pdf` - PDF generation
- `POST /api/quotes-v2/{id}/convert-to-po` - Convert to PO
- `POST /api/quotes-v2/{id}/send-quote` - Send quote email
- `POST /api/quotes-v2/{id}/send-po` - Send PO email
- `GET /api/quotes-v2/activities/all` - Document activities
- `GET /api/dashboard-v2/stats` - Dashboard stats
- `GET /api/dashboard-v2/activity-chart` - Activity chart
- `GET /api/dashboard-v2/top-products` - Top products
- `GET /api/dashboard-v2/top-clients` - Top clients

### Legacy (Proyecto A - kept for bot compatibility)
- `/api/products` - Old product endpoints
- `/api/quotes` - Old quote endpoints
- `/api/catalog/public` - Public catalog

## Credentials
- Admin: admin@gimmicks.com / admin123456

## Completed Tasks
- [x] FASE 1: Auditoría y plan de integración
- [x] FASE 2: Reemplazo de Catálogo y Cotizaciones (Inventory V2, Quotes V2, Clients, Dashboard V2)
- [x] Testing FASE 2: 100% pass rate

## Upcoming Tasks (Priority Order)
1. **P1 - FASE 3**: Integrar módulos restantes del Proyecto B (mejorar Dashboard UI con métricas reales V2)
2. **P1 - FASE 4**: Migración/adaptación de base de datos
3. **P1 - FASE 5**: Pruebas End-to-End completas
4. **P2 - Bot adaptation**: Adaptar bot_service.py para usar quotes_v2 en lugar de quotes
5. **P2 - Email SMTP/Resend**: Configurar credenciales de email
6. **P3 - Refactoring**: Dividir server.py en módulos más pequeños
