# Gimmicks CRM - WhatsApp Business Integration

## Original Problem Statement
Build a web-based CRM integrated with WhatsApp Business to manage a conversational sales funnel for Gimmicks Marketing Services.

## Core Requirements

### 1. Lead Entry
- Automatically receive and register incoming messages from WhatsApp Business Cloud API
- Capture lead's number, name, source, and timestamp

### 2. Conversational Funnel
- Send automatic welcome messages
- Ask guided questions to qualify leads
- Use rules and AI to interpret messages and classify leads (cold, warm, hot)

### 3. Inventory Integration
- Connect to internal inventory system (loaded from Excel)
- Auto-search and recommend products based on customer messages
- Send product details (name, description, availability)

### 4. Response Automation
- Personalized automatic responses
- Escalate to human agent when necessary

### 5. CRM Functionality
- Log entire conversation history
- Track lead status (In Conversation, Quoted, Converted, Lost)
- Automatic follow-ups via WhatsApp

### 6. Web Interface
- Centralized WhatsApp inbox with real-time conversations
- Customer profile view with history
- Configuration panel for automatic responses and funnel rules
- Dashboard with metrics (leads received, conversion, response time)

### 7. User Roles
- **Admin**: Full access to all features
- **Asesor (Agent)**: Limited access (view catalog, access chat)

## Tech Stack
- **Backend**: FastAPI, Python, Motor (async MongoDB), JWT Auth
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Database**: MongoDB
- **Integrations**: WhatsApp Business Cloud API, OpenAI API

## What's Been Implemented

### ✅ Completed (January 2026)
- [x] Backend API with FastAPI
- [x] JWT-based authentication with Admin/Asesor roles
- [x] User management (Admin can create/manage users)
- [x] WhatsApp webhook configured and verified with Meta
- [x] Core UI pages: Login, Dashboard, Inbox, Leads, Inventory, Settings, Users
- [x] Real-time conversation display in Inbox
- [x] Message sending from CRM to WhatsApp
- [x] Basic automation rules feature (keyword-based, new lead triggers)
- [x] AI analysis integration (GPT for lead classification)

### 🔧 Bug Fixes (January 29, 2026)
- [x] Fixed invisible text in Inbox message input (CSS color issue)
- [x] Fixed message sending from CRM UI (verified backend endpoint works)

## Pending Tasks

### P0 - High Priority
- [ ] Test automation rules end-to-end
- [ ] Configure WhatsApp credentials in production

### P1 - Medium Priority
- [ ] Implement Excel inventory upload
- [ ] AI-powered product recommendations

### P2 - Lower Priority
- [ ] Dashboard real metrics implementation
- [ ] Finalize Asesor role restrictions
- [ ] Refactor server.py into modules

## Database Schema

### users
```json
{
  "id": "uuid",
  "email": "string",
  "password": "hashed_string",
  "name": "string",
  "role": "admin|asesor",
  "created_at": "datetime"
}
```

### conversations
```json
{
  "id": "uuid",
  "phone_number": "string",
  "contact_name": "string",
  "source": "string",
  "stage": "lead|pedido|produccion|entregado|perdido",
  "classification": "frio|tibio|caliente",
  "last_message": "string",
  "last_message_time": "datetime",
  "unread_count": "int",
  "created_at": "datetime"
}
```

### messages
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "phone_number": "string",
  "sender": "user|business",
  "message_type": "text",
  "content": {"text": "string"},
  "status": "sent|delivered|failed|received",
  "timestamp": "datetime"
}
```

### automation_rules
```json
{
  "id": "uuid",
  "name": "string",
  "trigger_type": "keyword|new_lead",
  "keywords": ["array"],
  "action_type": "send_message|classify_lead",
  "action_value": "string",
  "is_active": "boolean",
  "created_at": "datetime"
}
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Users (Admin only)
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `DELETE /api/users/{id}` - Delete user

### Conversations
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}/messages` - Get messages
- `POST /api/conversations/{id}/messages` - Send message

### Automations
- `GET /api/automations` - List rules
- `POST /api/automations` - Create rule
- `PUT /api/automations/{id}` - Update rule
- `DELETE /api/automations/{id}` - Delete rule

### WhatsApp
- `GET /api/webhook/whatsapp` - Webhook verification
- `POST /api/webhook/whatsapp` - Receive messages

## Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=gimmicks_crm
JWT_SECRET_KEY=your-secret-key
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_VERIFY_TOKEN=your-verify-token
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://your-backend-url
```

## Access Credentials (Development)
- **Email**: admin@gimmicks.com
- **Password**: admin123456

---

## 🔴 TAREAS PENDIENTES (Última actualización: Enero 29, 2026)

### 1. Configuración del Robot de Automatización
- [ ] Probar reglas de automatización end-to-end
- [ ] Crear reglas en Configuración → respuestas automáticas por palabras clave
- [ ] Configurar mensaje de bienvenida automático para nuevos leads
- [ ] Verificar que las reglas se activen cuando lleguen mensajes al webhook

### 2. Configuración del Número de WhatsApp para Producción
- [ ] Migrar de número de prueba (+1 555 167 4338) a número real de Gimmicks
- [ ] Publicar la app en Meta para recibir mensajes de producción
- [ ] Configurar webhook para recibir mensajes entrantes reales

### 3. Credenciales de WhatsApp Configuradas
- **WHATSAPP_PHONE_NUMBER_ID**: 932135423324087
- **WHATSAPP_ACCESS_TOKEN**: Configurado en Railway
- **Webhook URL**: https://gimmicks-crm-production.up.railway.app/api/webhook/whatsapp

### 4. URLs de Acceso
- **Preview (Emergent)**: https://chatwiz-manager.preview.emergentagent.com
- **Backend (Railway)**: https://gimmicks-crm-production.up.railway.app
