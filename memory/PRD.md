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

### Mejora: Carga de Imágenes con Compresión en Modal de Producto - COMPLETADA (Feb 18, 2026)
- Sección "Imagen del Producto" rediseñada en ProductModal (Inventory.jsx)
- Vista previa grande de imagen con placeholder cuando no existe
- Botón "Subir Imagen" con fondo celeste (bg-sky-50) y compresión client-side via browser-image-compression (max 1200px ancho)
- Campo URL con soporte Google Drive (auto-conversión de enlaces)
- Tip informativo sobre Google Drive
- Botón "Guardar" oscuro (bg-gray-800) al fondo del modal
- Compresión doble: client-side (browser-image-compression) + server-side (Pillow)
- Testing iteration 9: 100% pass rate (11 backend + all frontend tests)

### Mejora: Ícono "Ver" en Clientes para Información Completa - COMPLETADA (Feb 18, 2026)
- Botón "Ver" con ícono Eye agregado en cada tarjeta de cliente
- Modal ClientDetailModal muestra TODA la información registrada: nombre, contacto, emails, teléfono, ciudad, dirección, RUC/CI, sector, notas y fecha de creación
- Campos vacíos mostrados como "No registrado" en gris cursiva

### Mejora: Rediseño Cotizaciones/Ordenes de Compra - COMPLETADA (Feb 19, 2026)
- Menú lateral dividido en 4 accesos: Cotizaciones, Órdenes de Compra, Nueva Cotización, Nueva Orden
- QuoteBuilder rediseñado: catálogo de productos a la izquierda (buscador, filtro categorías, precio min/max, limpiar filtros, grid de productos con imagen/código/nombre/precio/Agregar/Detalles)
- Panel de cotización a la derecha con selector de cliente, carrito, subtotal/total, guardar
- Modal "Detalles del Producto" con imagen, info completa, categorías y navegación prev/next
- Comportamiento "Agregar": DUPLICA el producto en el cotizador (no suma cantidad)
- Botón "Duplicar" en cada item del carrito
- QuoteHistory usa rutas separadas: /quotes (QUOTE) y /purchase-orders (PO)
- Testing iteration 10: 100% pass rate (14 tests frontend)

## Remaining/Future Tasks
1. **P1 - SMTP credentials**: Configure SMTP/Gmail/Resend for real email sending (cotizaciones)
2. **P2 - Refactoring**: Split bot_service.py and Leads.jsx into smaller modules
3. **P3 - Asesor role**: Finalize role restrictions
4. **P3 - PublicCatalog improvements**: Integrate improvements from Project B
5. **P3 - Deploy to Railway**: Deploy latest code to production
