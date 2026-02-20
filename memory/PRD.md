# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestión de leads, cotizaciones dinámicas, catálogo público.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP (aicreator@emprenovus.com)
- **WhatsApp Notifications**: Alertas al 593963266566

## Security Implementation (Feb 20, 2026)
- JWT secret fuerte (64 chars hex, auto-generado si no existe)
- Token expiration reducido de 24h a 8h
- Rate limiting en login: 5 intentos fallidos = bloqueo 5 minutos por IP
- Security headers: X-Content-Type-Options, X-Frame-Options (DENY), X-XSS-Protection, Referrer-Policy, Permissions-Policy, Cache-Control
- Validación de contraseñas: mín 8 chars, letras + números obligatorios
- Sanitización de inputs contra NoSQL injection
- Request size limit: 10MB máximo
- CORS restringido a métodos específicos

## Completed Tasks
- Core System, UI/UX, Bot WhatsApp, SMTP, Interesados/Clientes flow, Dashboard fix, Security

## Key Files
- `backend/server.py` - SecurityHeadersMiddleware, RequestSizeLimitMiddleware, check_login_attempts, validate_password_strength, sanitize_input
- `backend/bot_service.py` - Bot AI
- `backend/routes/clients_routes.py` - CRUD + promote
- `frontend/src/pages/Interesados.jsx` - WhatsApp prospects

## Credentials
- Admin: admin@gimmicks.com / admin123456
- SMTP: aicreator@emprenovus.com

## Remaining Tasks
1. **P0 - Deploy to Railway**: Guardar en GitHub y redesplegar
2. **P2 - Refactoring**: Split bot_service.py y Leads.jsx
3. **P3 - Asesor role**: Finalizar restricciones
