# Gimmicks CRM - WhatsApp Business - PRD

## Problema Original
Sistema CRM con bot conversacional inteligente para WhatsApp Business, enfocado en flujo de ventas comerciales para Gimmicks Marketing Services (Ecuador).

## Arquitectura
- **Backend**: FastAPI + MongoDB (Motor async)
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **IA**: OpenAI (gpt-4o-mini) via Emergent LLM Key
- **Produccion**: Railway (solo backend)
- **Preview**: Emergent (frontend + backend)

## Funcionalidades Implementadas
- Bot conversacional con IA (bot_service.py)
- Sistema de cotizaciones con revision admin (Quotes.jsx)
- Catalogo publico sin login (PublicCatalog.jsx + /catalog endpoint HTML)
- Pipeline de leads automatizado
- Gestion de usuarios (admin/asesor)
- Webhook WhatsApp Business API
- Carga de inventario via Excel
- Dashboard con metricas basicas
- Manejo de conversaciones inactivas (12h resume, 4h reminder, 24h perdido)
- Resilencia del bot (fallback sin errores tecnicos)

## Completado (Feb 2026)
- [x] P0: Fix enlace catalogo publico (URL encoding + limpieza datos test + verificacion flujo completo)
- [x] P0: Reconectar frontend a Railway (produccion) para mostrar conversaciones reales
- [x] Bot no repetitivo: carga datos previos del lead (load_known_client_data), historial ampliado a 20 msgs, prompt reforzado para NO repetir datos
- [x] Recordatorios inteligentes: skip conversaciones cotizadas, reminder_count (0->1->2->perdido), 4h->24h->24h->marca perdido
- [x] Etiquetas funnel_stage en Inbox: filtros por Lead/Potencial/Cotizado/Pedido/Perdido, badges por conversacion
- [x] Configuracion: 10 reglas del sistema sembradas (bienvenida, catalogo, recopilacion datos, cotizacion, recordatorios, perdido, reanudacion, transferencia humano, consulta precios)
- [x] Configuracion: edicion completa de reglas (nombre, trigger, accion, valor, activa/inactiva) via dialogo
- [x] Bot IA con recopilacion de datos paso a paso
- [x] Correccion requirements.txt (emergentintegrations)
- [x] Sistema de cotizaciones pendientes
- [x] Ortografia impecable (tildes)
- [x] Sin emojis en respuestas del bot
- [x] Logica de reanudacion 12h+

## Completado (Feb 17-18, 2026)
- [x] Sincronización nombre lead -> chat: fix normalización formato telefónico (+593 vs 593)
- [x] Corrección ortográfica de las 10 reglas de automatización
- [x] Bot anti-repetición: historial ampliado a 50 msgs, modelo gpt-4o, sesión persistente
- [x] Inventario: paginación con total real (5412+ productos)
- [x] Cotizaciones dinámicas: upsert_quote crea/actualiza, nombre desde lead, productos acumulativos

## Pendiente
- [ ] P1: Configuracion SMTP para envio de cotizaciones (necesita credenciales)
- [ ] P1: Mejorar UI de carga de inventario (Inventory.jsx)
- [ ] P2: Dashboard con metricas reales
- [ ] Restricciones completas rol "Asesor"
- [ ] Refactorizar server.py en modulos (routes, models, services)

## Credenciales Test
- Email: admin@gimmicks.com
- Password: admin123456

## Nota Critica
Los cambios NO estan desplegados en Railway. El usuario debe hacer "Save to GitHub" para desplegar.
