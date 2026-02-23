# PRD - Gimmicks CRM WhatsApp Business

## Problem Statement
CRM para ventas comerciales con WhatsApp Business que integra bot IA (GPT-4o), gestion de leads, cotizaciones dinamicas, catalogo publico.

## Architecture
- **Backend**: FastAPI + MongoDB + emergentintegrations (GPT-4o)
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Email**: Gmail SMTP
- **Production DB**: Railway MongoDB

## Roles y Permisos

### Admin
- Acceso completo a todo el sistema
- Puede crear, editar, eliminar clientes/interesados/cotizaciones/ordenes
- Puede exportar datos, ver papelera, dashboard, leads, usuarios
- NO puede ver, editar ni eliminar al usuario desarrollador

### Asesor
- Puede: crear y editar clientes, interesados, ordenes de compra, cotizaciones
- NO puede: eliminar nada (clientes, interesados, cotizaciones, ordenes)
- NO puede: descargar/exportar datos, ver papelera
- NO puede: ver Dashboard, Leads, Usuarios, Configuracion
- Inbox: solo leer y responder (no eliminar/limpiar conversaciones)

### Desarrollador
- SOLO acceso a Configuracion
- No puede ser eliminado ni modificado por admin
- No aparece en listado de usuarios para admin
- No tiene acceso a ninguna otra data del sistema
- Credenciales: aicreator@emprenovus.com / Jlsb*1082

## Completed Tasks
- [x] Core system merge (Project A + B)
- [x] WhatsApp Bot multi-step flow
- [x] Interesados/Clientes separation
- [x] Lead-to-Client auto-promotion
- [x] SMTP email integration
- [x] Dashboard analytics
- [x] Security hardening
- [x] Bot flow refinements
- [x] Production data sync
- [x] Bot E2E verification (17/17)
- [x] Railway deploy fix
- [x] Inbox: asesor read-only (no delete/clear)
- [x] Starred conversations filter fix
- [x] Role-based permissions (admin/asesor/desarrollador) - Feb 23, 2026
- [x] Asesor: no delete/export, no dashboard/leads
- [x] Desarrollador: only Configuracion access, protected user

## Remaining Tasks
1. **P2 - Refactor bot_service.py**: Split into smaller modules
2. **P3 - Deploy to Railway**: Save to GitHub and redeploy
