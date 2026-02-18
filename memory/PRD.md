# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público. Fusionado con Cotizador Gimmicks para módulos avanzados de inventario, cotizaciones con PDF, clientes y órdenes de compra.

## Architecture
- **Backend**: FastAPI (Python) - `/app/backend/server.py` + modular routes in `/app/backend/routes/`
- **Frontend**: React + Shadcn/UI + TailwindCSS + Recharts
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT (bcrypt)
- **Bot**: GPT-4o via Emergent LLM Key
- **PDF**: ReportLab
- **Email**: Gmail SMTP / Resend (MOCKED - needs credentials)

## Completed Tasks (Feb 18, 2026)

### FASE 1: Auditoría - COMPLETADA
- Análisis completo de ambos proyectos A y B
- Plan de integración aprobado por usuario

### FASE 2: Reemplazo Catálogo y Cotizaciones - COMPLETADA
- Inventory V2 con paginación, categorías array, costo/proveedor, upload imágenes, exportar Excel
- Quotes V2 con QuoteBuilder (carrito, descuentos, valores adicionales), PDF generation, email, tabs Cotizaciones/OC
- Clientes CRUD con soft delete, trash, restore, historial, sectores

### FASE 3: Integración módulos restantes - COMPLETADA
- Dashboard con métricas REALES (recharts BarChart): productos, clientes, cotizaciones, OC, leads, conversaciones
- Gráfico de actividad 14 días, Top productos cotizados, Top clientes

### FASE 4: Base de datos - COMPLETADA
- Dual schema support: productos old (category_1/2/3) + new (categories array)
- Nuevas colecciones: quotes_v2, clients, client_activities, document_activities
- Colecciones existentes intactas: users, leads, conversations, messages, quotes

### FASE 5: Pruebas E2E - COMPLETADA
- Testing agent iterations 7 y 8: 100% pass rate
- Backend: 24/24 tests, Frontend: todas las páginas verificadas
- Módulos existentes intactos verificados

### Mejora: Bot WhatsApp → quotes_v2 + auto-crear clientes - COMPLETADA
- bot_service.py adaptado para guardar cotizaciones en quotes_v2
- Función auto_create_client() crea/actualiza clientes automáticamente desde WhatsApp
- Búsqueda de productos soporta ambos esquemas

## Key Files
### Backend
- `/app/backend/server.py` - Main server
- `/app/backend/bot_service.py` - WhatsApp bot AI logic (adapted for quotes_v2 + auto-create clients)
- `/app/backend/routes/inventory_routes.py` - Inventory V2 API
- `/app/backend/routes/quotes_routes.py` - Quotes V2 API with PDF
- `/app/backend/routes/clients_routes.py` - Clients CRUD API
- `/app/backend/routes/dashboard_routes.py` - Dashboard V2 real stats
- `/app/backend/services/email_service.py` - Email service (Gmail SMTP + Resend)
- `/app/backend/models_b.py` - Pydantic models for V2 modules

### Frontend
- `/app/frontend/src/pages/Dashboard.jsx` - Real metrics dashboard with recharts
- `/app/frontend/src/pages/Inventory.jsx` - Inventory V2
- `/app/frontend/src/pages/Clients.jsx` - Clients module
- `/app/frontend/src/pages/QuoteBuilder.jsx` - Quote builder with cart
- `/app/frontend/src/pages/QuoteHistory.jsx` - Quote/PO history with PDF
- `/app/frontend/src/pages/Inbox.jsx` - WhatsApp Inbox (intact)
- `/app/frontend/src/pages/Leads.jsx` - Leads Kanban (intact)

## Mocked
- **Email sending**: MOCKED (no SMTP/Resend/Gmail credentials)

## Credentials
- Admin: admin@gimmicks.com / admin123456

## Remaining/Future Tasks
1. **P2 - Email credentials**: Configure SMTP/Gmail/Resend for real email sending
2. **P2 - Refactoring**: Split server.py into smaller modules
3. **P3 - Asesor role**: Finalize role restrictions
4. **P3 - Deploy to Railway**: Deploy latest code to production
