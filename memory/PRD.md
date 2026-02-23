# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestion de leads, cotizaciones dinamicas, catalogo publico. Fusion de Proyecto A (CRM) con Proyecto B (cotizaciones).

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP (aicreator@emprenovus.com)
- **WhatsApp Notifications**: Alertas al 593963266566
- **Production DB**: Railway MongoDB (metro.proxy.rlwy.net:40305)

## Core Features
1. **WhatsApp Bot (Ana)**: Multi-step conversational flow for quoting
2. **Interesados vs Clientes**: WhatsApp prospects vs manual clients
3. **Lead-to-Client Promotion**: Auto-promote when lead reaches "Entregado"
4. **Production Data Sync**: Background sync every 2min from Railway MongoDB
5. **Email Quotes**: SMTP integration for sending quotes/orders
6. **Dashboard Analytics**: Activity charts with quotes, orders, leads
7. **Security**: Rate limiting, security headers, password validation
8. **Role-based Permissions**: Asesor cannot delete/clear conversations

## Security Implementation
- JWT secret (64 chars hex)
- Token expiration: 8h
- Rate limiting: 5 login attempts = 5min block per IP
- Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- Password validation: min 8 chars, letters + numbers
- Input sanitization against NoSQL injection
- Request size limit: 10MB
- CORS restricted
- Asesor role: read + respond only in Inbox (no delete/clear)

## Completed Tasks
- [x] Core system merge (Project A + B)
- [x] WhatsApp Bot with multi-step flow
- [x] Interesados/Clientes separation
- [x] Lead-to-Client auto-promotion
- [x] SMTP email integration
- [x] Dashboard analytics fix
- [x] Security hardening
- [x] Bot flow refinements (no redundant text, no re-asking name, quote after empresa)
- [x] Production data sync (background + manual button) - Feb 20, 2026
- [x] Bot E2E verification (17/17 tests passed) - Feb 20, 2026
- [x] Railway deploy fix (emergentintegrations extra-index-url) - Feb 20, 2026
- [x] Asesor role: no delete/clear in Inbox (frontend + backend) - Feb 20, 2026
- [x] Starred conversations filter fix (is_starred in list API) - Feb 20, 2026

## Key Files
- `backend/server.py` - Main FastAPI app, middleware, routes
- `backend/bot_service.py` - Bot AI conversation logic
- `backend/services/sync_service.py` - Production MongoDB sync
- `backend/services/email_service.py` - SMTP email
- `backend/routes/clients_routes.py` - CRUD + promote
- `frontend/src/pages/Inbox.jsx` - Chat inbox with sync button + role permissions
- `frontend/src/pages/Interesados.jsx` - WhatsApp prospects
- `frontend/src/pages/Dashboard.jsx` - Analytics

## Key API Endpoints
- `POST /api/webhook/whatsapp` - WhatsApp bot entry point
- `GET /api/conversations` - List conversations (now includes is_starred)
- `DELETE /api/conversations/{id}` - Delete conversation (admin only)
- `DELETE /api/conversations/{id}/messages` - Clear messages (admin only)
- `GET /api/sync/status` - Background sync status
- `POST /api/sync/production` - Manual sync trigger
- `GET /api/interesados` - WhatsApp prospects
- `GET /api/clients` - Manual clients
- `POST /api/auth/login` - Login (rate limited)

## Credentials
- Admin: admin@gimmicks.com / admin123456
- Asesor test: asesor@gimmicks.com / asesor12345
- SMTP: aicreator@emprenovus.com

## Remaining Tasks (Backlog)
1. **P2 - Refactor bot_service.py**: Split into state manager, prompt builder, DB service
2. **P3 - Deploy to Railway**: Save to GitHub and redeploy
