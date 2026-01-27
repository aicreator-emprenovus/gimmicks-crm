# Gimmicks CRM - WhatsApp Business PRD

## Problema Original
CRM WEB basado en funnel conversacional con WhatsApp Business para Gimmicks Marketing Services. Sistema capaz de:
- Recibir mensajes de WhatsApp Business (leads de Meta Ads u otros canales)
- Gestionar funnel de ventas conversacional automatizado
- Responder automáticamente usando reglas e IA
- Conectarse al sistema de inventario para recomendaciones personalizadas

## User Personas
1. **Agente de Ventas**: Gestiona conversaciones, responde leads, mueve leads por el funnel
2. **Administrador**: Configura reglas de automatización, gestiona inventario
3. **Lead/Cliente**: Contacta vía WhatsApp buscando productos promocionales

## Arquitectura
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Shadcn UI + Tailwind CSS
- **IA**: GPT-5.2 via Emergent LLM Key
- **Estilo**: Gimmicks Theme (fondo oscuro #09090b, cards blancas, emerald #10b981)

## Features Implementadas (Fecha: 2026-01-27)

### Autenticación
- [x] Registro de usuarios (JWT)
- [x] Login con email/password
- [x] Protección de rutas

### Dashboard
- [x] Métricas principales (total leads, mensajes hoy, conversión, tiempo respuesta)
- [x] Gráfico de leads por etapa del funnel
- [x] Gráfico de leads por fuente
- [x] Datos demo para testing

### Inbox (Chat WhatsApp)
- [x] Lista de conversaciones con búsqueda
- [x] Vista de mensajes en tiempo real (estilo WhatsApp)
- [x] Envío de mensajes
- [x] Análisis de mensajes con IA
- [x] Badge de mensajes no leídos

### Gestión de Leads (Funnel Kanban)
- [x] Vista Kanban de 6 etapas: Lead, Pedido, Producción, Entregado, Perdido, Cierre
- [x] CRUD completo de leads
- [x] Clasificación: Frío, Tibio, Caliente
- [x] Fuentes: WhatsApp, Meta Ads, Web, Orgánico
- [x] Filtros por etapa y clasificación
- [x] Actualización de etapa desde tarjeta

### Inventario
- [x] Tabla de productos con búsqueda
- [x] **Carga masiva de productos via Excel**
- [x] Categorías múltiples
- [x] CRUD completo

### Automatización
- [x] Reglas con triggers: keyword, new_lead, funnel_change, no_response
- [x] Acciones: send_message, change_stage, assign_agent, recommend_product
- [x] Activar/desactivar reglas
- [x] Reglas de demostración pre-configuradas

### Integración IA (GPT-5.2)
- [x] Análisis de intención de mensajes
- [x] Clasificación automática de leads
- [x] Sugerencias de respuestas
- [x] Recomendación de productos basada en texto

### WhatsApp Business API
- [x] Webhook de verificación configurado
- [x] Endpoint para recibir mensajes (SIMULADO - sin conexión real)
- [x] Procesamiento de mensajes entrantes

## Backlog Priorizado

### P0 (Crítico)
- [ ] Conexión real a WhatsApp Business Cloud API
- [ ] Envío de mensajes vía API oficial de Meta

### P1 (Alta prioridad)
- [ ] Notificaciones en tiempo real (WebSockets)
- [ ] Envío de archivos e imágenes en chat
- [ ] Templates de WhatsApp para mensajes fuera de 24h
- [ ] Dashboard de analytics avanzado

### P2 (Media prioridad)
- [ ] Asignación de agentes a conversaciones
- [ ] Respuestas automáticas completas
- [ ] Exportación de reportes
- [ ] Historial de cambios en leads

## Próximas Acciones
1. Cargar el catálogo completo de productos usando el Excel proporcionado
2. Configurar WhatsApp Business API con credenciales reales de Meta
3. Probar flujo completo de mensajes entrantes/salientes
4. Configurar reglas de automatización personalizadas
