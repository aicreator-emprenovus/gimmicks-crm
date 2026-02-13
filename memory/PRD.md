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

### Completed (January 2026)
- [x] Backend API with FastAPI
- [x] JWT-based authentication with Admin/Asesor roles
- [x] User management (Admin can create/manage users)
- [x] WhatsApp webhook configured and verified with Meta
- [x] Core UI pages: Login, Dashboard, Inbox, Leads, Inventory, Settings, Users
- [x] Real-time conversation display in Inbox
- [x] Message sending from CRM to WhatsApp
- [x] Basic automation rules feature (keyword-based, new lead triggers)
- [x] AI analysis integration (GPT for lead classification)
- [x] Advanced conversational bot logic in backend
- [x] UI Dark Theme redesign
- [x] Conversation management (star/save, clear, delete)

### Completed (February 13, 2026)
- [x] Sidebar cleanup: Removed Cotizaciones, Ordenes de Compra, Nueva Cotizacion, Nueva Orden
- [x] Sidebar width reduced ~30% (288px -> 200px)
- [x] Removed "MARKETING SERVICES" subtitle under logo
- [x] Collapsible sidebar with icon-only mode (toggle button)

## Pending Tasks

### P0 - High Priority
- [ ] Test bot conversational flow E2E
- [ ] Fix frontend JS errors (Select components, navigation)

### P1 - Medium Priority
- [ ] Implement Excel inventory upload (UI + backend connection)
- [ ] AI-powered product recommendations
- [ ] Dashboard real metrics implementation

### P2 - Lower Priority
- [ ] Finalize Asesor role restrictions
- [ ] Refactor server.py into modules (routes, models, services)

## Database Schema

### users
```json
{ "email": "string", "name": "string", "hashed_password": "string", "role": "admin|asesor", "created_at": "datetime" }
```

### conversations
```json
{ "phone_number": "string", "contact_name": "string", "stage": "lead|pedido|produccion|entregado|perdido", "is_starred": "bool", "last_message": "string", "last_message_time": "datetime" }
```

### messages
```json
{ "conversation_id": "uuid", "sender": "user|business", "content": {"text": "string"}, "timestamp": "datetime" }
```

### conversation_states (New)
```json
{ "phone_number": "string", "current_step": "string", "collected_data": {}, "request_type": "string" }
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Conversations
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}/messages` - Get messages
- `POST /api/conversations/{id}/messages` - Send message
- `POST /api/conversations/{id}/star` - Toggle star
- `DELETE /api/conversations/{id}/messages` - Clear messages
- `DELETE /api/conversations/{id}` - Delete conversation

### WhatsApp
- `GET /api/webhook/whatsapp` - Webhook verification
- `POST /api/webhook/whatsapp` - Receive messages

## Access Credentials (Development)
- **Email**: admin@gimmicks.com
- **Password**: admin123456

## URLs
- **Preview**: https://gimmicks-bot-test.preview.emergentagent.com
- **Backend (Railway)**: https://gimmicks-crm-production.up.railway.app
