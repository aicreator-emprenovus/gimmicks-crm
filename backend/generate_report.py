import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm, inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

def build_report():
    output_path = "/app/backend/static_frontend/INFORME_TECNICO_GIMMICKS_CRM.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=22, 
                                  textColor=HexColor('#1a5c4c'), spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle2', parent=styles['Normal'], fontSize=11,
                                     textColor=HexColor('#666666'), spaceAfter=20, alignment=TA_CENTER)
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, 
                         textColor=HexColor('#1a5c4c'), spaceBefore=20, spaceAfter=10,
                         borderWidth=0, borderPadding=0)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, 
                         textColor=HexColor('#2d7a6a'), spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle('Body2', parent=styles['Normal'], fontSize=10, 
                           leading=14, spaceAfter=8, alignment=TA_JUSTIFY)
    bullet = ParagraphStyle('Bullet2', parent=body, leftIndent=20, 
                             bulletIndent=8, spaceAfter=4)
    accent = ParagraphStyle('Accent', parent=body, textColor=HexColor('#1a5c4c'),
                             fontSize=10, leading=14)
    
    green = HexColor('#63AC9A')
    dark_green = HexColor('#1a5c4c')
    light_bg = HexColor('#f0f9f6')
    white = HexColor('#ffffff')
    gray = HexColor('#e0e0e0')
    
    elements = []
    
    # ==================== PORTADA ====================
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("INFORME TECNICO", title_style))
    elements.append(Paragraph("Plataforma CRM Gimmicks Marketing Services", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=green, spaceAfter=15))
    elements.append(Paragraph("Documento preparado para: <b>Gimmicks Marketing Services</b>", body))
    elements.append(Paragraph("Fecha: Marzo 2026", body))
    elements.append(Paragraph("Version: 2.0", body))
    elements.append(Spacer(1, 1*cm))
    
    # ==================== 1. RESUMEN EJECUTIVO ====================
    elements.append(Paragraph("1. RESUMEN EJECUTIVO", h1))
    elements.append(HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10))
    elements.append(Paragraph(
        "La plataforma Gimmicks CRM es un sistema integral de gestion comercial que combina un CRM (Customer Relationship Management) "
        "con un asistente virtual inteligente integrado a WhatsApp Business. El sistema permite gestionar todo el ciclo de ventas: "
        "desde la captacion de clientes potenciales por WhatsApp, pasando por la cotizacion automatizada de productos, hasta la "
        "generacion de ordenes de compra con documentos PDF profesionales.", body))
    elements.append(Paragraph(
        "El asistente virtual, impulsado por inteligencia artificial GPT-5.2 (el modelo mas avanzado de OpenAI), atiende a los "
        "clientes las 24 horas del dia, responde consultas, envia catalogos de productos y genera cotizaciones de forma automatica.", body))
    
    # ==================== 2. MODULOS DEL SISTEMA ====================
    elements.append(Paragraph("2. MODULOS Y FUNCIONALIDADES", h1))
    elements.append(HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10))
    
    # 2.1 WhatsApp Bot
    elements.append(Paragraph("2.1 Asistente Virtual de WhatsApp (Bot IA)", h2))
    elements.append(Paragraph(
        "El corazon del sistema es un asistente virtual inteligente que atiende a los clientes directamente por WhatsApp, "
        "sin necesidad de intervencion humana en la mayoria de los casos.", body))
    bullets_bot = [
        "<b>Modelo de IA:</b> GPT-5.2 de OpenAI, el mas avanzado disponible actualmente, capaz de entender contexto, intenciones y mantener conversaciones naturales.",
        "<b>Identidad:</b> Se presenta como 'Ana de Gimmicks Marketing Services'.",
        "<b>Flujo de atencion:</b> Saludo > Solicitud de nombre > Identificacion de producto > Envio de catalogo > Recopilacion de datos > Generacion de cotizacion.",
        "<b>Catalogo inteligente:</b> Cuando un cliente menciona un tipo de producto (jarros, termos, gorras, etc.), el bot busca automaticamente en el inventario y envia un enlace filtrado al catalogo en linea.",
        "<b>Catalogo completo:</b> Si el cliente solicita ver todos los productos, el bot envia el enlace a la web oficial de Gimmicks (gimmicks.com.ec).",
        "<b>Cotizacion automatica:</b> Una vez recopilados todos los datos (producto, cantidad, correo, empresa, ciudad, fecha), el sistema genera y envia una cotizacion formal por correo electronico.",
        "<b>18 reglas de automatizacion:</b> El bot sigue reglas configurables como mensajes de bienvenida, seguimiento automatico (4h, 24h, 48h), escalamiento a humano ante quejas, y mas.",
        "<b>Clasificacion de clientes:</b> Automaticamente clasifica al contacto como caliente, tibio o frio segun su interes.",
        "<b>Memoria de conversacion:</b> Recuerda datos previos del cliente y no repite preguntas ya respondidas.",
    ]
    for b in bullets_bot:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.2 Inbox
    elements.append(Paragraph("2.2 Bandeja de Entrada (Inbox)", h2))
    elements.append(Paragraph(
        "Panel centralizado donde los administradores pueden ver y gestionar todas las conversaciones de WhatsApp en tiempo real.", body))
    bullets_inbox = [
        "<b>Vista de conversaciones:</b> Lista todas las conversaciones con nombre del contacto, ultimo mensaje, hora y contador de mensajes no leidos.",
        "<b>Chat en tiempo real:</b> Visualizacion completa del historial de mensajes entre el bot y cada cliente.",
        "<b>Respuesta manual:</b> Los administradores pueden intervenir y responder directamente desde el sistema.",
        "<b>Conversaciones destacadas:</b> Posibilidad de marcar conversaciones importantes con estrella.",
        "<b>Clasificacion visual:</b> Cada conversacion muestra el estado del lead (Nuevo, Potencial, Cotizado, Calificado).",
        "<b>Sincronizacion automatica:</b> Las conversaciones se sincronizan automaticamente cada 2 minutos entre el entorno de desarrollo y produccion.",
    ]
    for b in bullets_inbox:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.3 Dashboard
    elements.append(Paragraph("2.3 Panel de Control (Dashboard)", h2))
    elements.append(Paragraph(
        "Vista general con metricas clave del negocio en tiempo real.", body))
    bullets_dash = [
        "<b>Total de productos:</b> Cantidad de productos registrados en el inventario.",
        "<b>Total de clientes:</b> Numero de clientes activos en el sistema.",
        "<b>Cotizaciones generadas:</b> Conteo de cotizaciones creadas.",
        "<b>Leads activos:</b> Numero de contactos potenciales capturados por WhatsApp.",
        "<b>Actividad reciente:</b> Ultimas interacciones y movimientos en el sistema.",
    ]
    for b in bullets_dash:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.4 Inventario
    elements.append(Paragraph("2.4 Gestion de Inventario", h2))
    elements.append(Paragraph(
        "Modulo completo para administrar el catalogo de mas de 5,400 productos.", body))
    bullets_inv = [
        "<b>Catalogo de productos:</b> Visualizacion con imagen, codigo, nombre, precio, categoria y disponibilidad.",
        "<b>Busqueda rapida:</b> Filtrado instantaneo por nombre, codigo o categoria.",
        "<b>Imagenes persistentes:</b> Las imagenes de productos se almacenan en la base de datos (no en archivos temporales), garantizando que nunca se pierdan tras una actualizacion del sistema.",
        "<b>Subida de imagenes:</b> Soporte para subir imagenes de hasta 25 MB por producto.",
        "<b>Compatibilidad con Google Drive:</b> Carga automatica de imagenes desde enlaces de Google Drive con 3 estrategias de respaldo.",
        "<b>Catalogo publico:</b> Pagina web publica donde los clientes pueden ver productos filtrados por categoria, accesible desde los enlaces que envia el bot.",
    ]
    for b in bullets_inv:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.5 Clientes e Interesados
    elements.append(Paragraph("2.5 Gestion de Clientes e Interesados", h2))
    elements.append(Paragraph(
        "El sistema separa claramente entre 'Interesados' (contactos que aun no han comprado) y 'Clientes' (contactos con compras realizadas).", body))
    bullets_cli = [
        "<b>Registro completo:</b> Nombre, empresa, correo, telefono, direccion, RUC, persona de contacto.",
        "<b>Promocion automatica:</b> Cuando un interesado realiza una compra, el sistema lo promueve automaticamente a cliente.",
        "<b>Busqueda predictiva:</b> Al crear cotizaciones, el sistema sugiere clientes mientras se escribe el nombre.",
        "<b>Filtro por cliente:</b> Las cotizaciones y ordenes de compra se pueden filtrar por cliente especifico.",
    ]
    for b in bullets_cli:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.6 Leads
    elements.append(Paragraph("2.6 Gestion de Leads", h2))
    elements.append(Paragraph(
        "Seguimiento automatizado de contactos potenciales capturados por el bot de WhatsApp.", body))
    bullets_leads = [
        "<b>Captura automatica:</b> Cada persona que escribe al WhatsApp se registra automaticamente como lead.",
        "<b>Datos recopilados:</b> Nombre, telefono, correo, empresa, productos de interes, ciudad, presupuesto estimado.",
        "<b>Clasificacion por temperatura:</b> Caliente (muy interesado), Tibio (interesado), Frio (poco interes).",
        "<b>Historial de interacciones:</b> Registro completo de toda la comunicacion.",
    ]
    for b in bullets_leads:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.7 Cotizaciones
    elements.append(Paragraph("2.7 Sistema de Cotizaciones", h2))
    elements.append(Paragraph(
        "Herramienta completa para crear, editar y enviar cotizaciones profesionales.", body))
    bullets_quotes = [
        "<b>Constructor de cotizaciones:</b> Interfaz visual para agregar productos, definir cantidades y personalizar precios.",
        "<b>Precios editables:</b> Los precios de cada producto se pueden ajustar directamente en la cotizacion, sin modificar el precio del inventario.",
        "<b>Descuentos:</b> Aplicacion de descuentos por porcentaje o monto fijo sobre el total.",
        "<b>Generacion de PDF:</b> Documentos profesionales tipo Proforma con imagen de productos, datos del cliente y desglose de precios.",
        "<b>Envio por correo:</b> Las cotizaciones se envian automaticamente al correo del cliente.",
        "<b>Busqueda predictiva de clientes:</b> Al seleccionar el cliente, el sistema sugiere nombres mientras se escribe.",
    ]
    for b in bullets_quotes:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.8 Ordenes de Compra
    elements.append(Paragraph("2.8 Ordenes de Compra", h2))
    elements.append(Paragraph(
        "Modulo para convertir cotizaciones aprobadas en ordenes de compra formales.", body))
    bullets_po = [
        "<b>Numeracion independiente:</b> Las ordenes de compra tienen su propia secuencia numerica (iniciando en 4712), separada de las cotizaciones.",
        "<b>PDF profesional:</b> Documento con campos detallados: Fecha, Orden de Compra, Cliente, Factura, Direccion, Telefono, Solicitado Por, Correo y RUC. Todos los campos del encabezado en tamano de letra 12pt para mejor legibilidad.",
        "<b>Datos persistentes:</b> Los datos ingresados en el formulario de Factura se guardan automaticamente. Al reabrir el formulario, los datos previos se cargan para editarlos o generar un nuevo PDF sin tener que volver a escribirlos.",
        "<b>Modal editable:</b> Antes de generar el PDF, se abre un formulario con todos los campos editables para personalizar la orden.",
    ]
    for b in bullets_po:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.9 Usuarios
    elements.append(Paragraph("2.9 Gestion de Usuarios y Roles", h2))
    elements.append(Paragraph(
        "Sistema de control de acceso basado en roles con tres niveles de permisos.", body))
    
    # Roles table
    role_data = [
        ["Funcion", "Admin", "Asesor", "Desarrollador"],
        ["Ver Dashboard", "Si", "No", "No"],
        ["Ver Inbox y responder", "Si", "Si (solo lectura)", "No"],
        ["Crear cotizaciones/OC", "Si", "Si", "No"],
        ["Eliminar registros", "Si", "No", "No"],
        ["Exportar datos", "Si", "No", "No"],
        ["Gestionar usuarios", "Si", "No", "No"],
        ["Ver Leads", "Si", "No", "No"],
        ["Configuracion del sistema", "Si", "No", "Si"],
    ]
    role_table = Table(role_data, colWidths=[3.5*cm, 3*cm, 3.5*cm, 3*cm])
    role_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), dark_green),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(role_table)
    elements.append(Spacer(1, 10))
    
    # 2.10 Correo Electronico
    elements.append(Paragraph("2.10 Integracion de Correo Electronico", h2))
    elements.append(Paragraph(
        "El sistema envia correos electronicos de forma automatica a traves de Gmail SMTP para las siguientes acciones:", body))
    bullets_email = [
        "Envio de cotizaciones al cliente tras su generacion.",
        "Envio del catalogo completo cuando el bot lo solicita.",
        "Notificaciones al equipo de ventas sobre nuevos leads calientes.",
    ]
    for b in bullets_email:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # 2.11 Configuracion
    elements.append(Paragraph("2.11 Configuracion y Reglas de Automatizacion", h2))
    elements.append(Paragraph(
        "Panel de administracion donde se configuran las 18 reglas de automatizacion del bot y otros parametros del sistema.", body))
    bullets_config = [
        "<b>Mensaje de bienvenida:</b> Configurable para nuevos contactos.",
        "<b>Seguimientos automaticos:</b> A las 4 horas, 24 horas y 48 horas sin respuesta.",
        "<b>Respuestas por intencion:</b> Reglas para solicitud de catalogo, cotizacion directa, datos completos, quejas.",
        "<b>Escalamiento a humano:</b> Transferencia automatica cuando se detecta una queja o insatisfaccion.",
        "<b>Todas las reglas son editables:</b> Se pueden activar, desactivar y modificar desde la interfaz sin necesidad de tocar codigo.",
    ]
    for b in bullets_config:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # ==================== 3. SEGURIDAD ====================
    elements.append(Paragraph("3. MEDIDAS DE SEGURIDAD", h1))
    elements.append(HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10))
    
    elements.append(Paragraph("3.1 Autenticacion y Control de Acceso", h2))
    bullets_auth = [
        "<b>Contrasenas encriptadas:</b> Todas las contrasenas se almacenan con cifrado bcrypt (estandar de la industria). Nadie, ni siquiera los administradores del sistema, pueden ver las contrasenas reales.",
        "<b>Tokens JWT:</b> Cada sesion de usuario se gestiona con tokens JWT (JSON Web Tokens) con expiracion de 8 horas. Despues de ese tiempo, el usuario debe iniciar sesion nuevamente.",
        "<b>Proteccion contra ataques de fuerza bruta:</b> El sistema bloquea automaticamente una direccion IP despues de 5 intentos fallidos de inicio de sesion en un periodo de 5 minutos.",
        "<b>Limitacion de peticiones:</b> Maximo 60 solicitudes por minuto por IP para prevenir ataques de denegacion de servicio.",
        "<b>Roles con privilegios minimos:</b> Cada rol (Admin, Asesor, Desarrollador) solo tiene acceso a las funciones estrictamente necesarias.",
        "<b>Usuario desarrollador protegido:</b> La cuenta del desarrollador no puede ser eliminada ni modificada por ningun administrador, garantizando acceso de soporte tecnico en todo momento.",
    ]
    for b in bullets_auth:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    elements.append(Paragraph("3.2 Proteccion de Datos en Transito", h2))
    bullets_transit = [
        "<b>HTTPS obligatorio:</b> Toda la comunicacion entre el navegador del usuario y el servidor esta cifrada con certificado SSL/TLS.",
        "<b>Cabeceras de seguridad HTTP:</b> El sistema implementa cabeceras de proteccion contra: inyeccion de contenido (X-Content-Type-Options), clickjacking (X-Frame-Options), ataques XSS (X-XSS-Protection), y filtracion de informacion del navegador (Referrer-Policy).",
        "<b>CORS restringido:</b> Solo los origenes autorizados pueden comunicarse con el servidor.",
    ]
    for b in bullets_transit:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    elements.append(Paragraph("3.3 Proteccion de Datos en Reposo", h2))
    bullets_rest = [
        "<b>Base de datos en la nube:</b> MongoDB con acceso restringido por credenciales unicas.",
        "<b>Imagenes persistentes:</b> Las imagenes de productos se almacenan directamente en la base de datos (no en archivos temporales), evitando perdida de datos tras actualizaciones.",
        "<b>Variables de entorno:</b> Todas las credenciales sensibles (tokens de WhatsApp, claves de API, contrasenas de correo) se almacenan como variables de entorno, nunca en el codigo fuente.",
        "<b>Limite de tamano de archivos:</b> Proteccion contra subida de archivos maliciosos con limite de 25 MB.",
    ]
    for b in bullets_rest:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    elements.append(Paragraph("3.4 Seguridad del Bot de WhatsApp", h2))
    bullets_wa = [
        "<b>Verificacion de webhook:</b> Los mensajes entrantes se validan con un token secreto para garantizar que provienen de Meta (Facebook).",
        "<b>Filtrado de numeros:</b> El sistema filtra mensajes de numeros no autorizados o desactivados.",
        "<b>Sesiones independientes:</b> Cada conversacion tiene su propia sesion de IA, evitando que datos de un cliente se mezclen con los de otro.",
    ]
    for b in bullets_wa:
        elements.append(Paragraph(b, bullet, bulletText="\u2022"))
    
    # ==================== 4. ARQUITECTURA ====================
    elements.append(Paragraph("4. ARQUITECTURA DEL SISTEMA", h1))
    elements.append(HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10))
    
    arch_data = [
        ["Componente", "Tecnologia", "Descripcion"],
        ["Servidor", "FastAPI (Python)", "Motor principal que procesa todas las solicitudes"],
        ["Interfaz Web", "React + TailwindCSS", "Aplicacion web moderna y responsiva"],
        ["Base de Datos", "MongoDB", "Almacenamiento de datos en la nube"],
        ["Inteligencia Artificial", "GPT-5.2 (OpenAI)", "Modelo de lenguaje para el bot conversacional"],
        ["Mensajeria", "WhatsApp Cloud API", "Conexion oficial con WhatsApp Business"],
        ["Correo", "Gmail SMTP", "Envio automatizado de cotizaciones y notificaciones"],
        ["Hosting", "Emergent", "Plataforma de despliegue en la nube"],
    ]
    arch_table = Table(arch_data, colWidths=[3*cm, 4*cm, 8*cm])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), dark_green),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(arch_table)
    
    # ==================== 5. RESUMEN DE MEJORAS RECIENTES ====================
    elements.append(Paragraph("5. MEJORAS RECIENTES (MARZO 2026)", h1))
    elements.append(HRFlowable(width="100%", thickness=1, color=gray, spaceAfter=10))
    
    improvements = [
        "<b>Actualizacion a GPT-5.2:</b> Migracion del modelo de IA de GPT-4o al mas reciente GPT-5.2, mejorando la comprension y calidad de las respuestas del bot.",
        "<b>Integracion de reglas de automatizacion:</b> El bot ahora lee y aplica las 18 reglas configuradas en el panel de Configuracion, en lugar de seguir un flujo fijo.",
        "<b>Optimizacion de rendimiento:</b> Mejoras en la carga de imagenes, generacion de PDFs y tiempos de respuesta de la aplicacion.",
        "<b>Persistencia de datos de Ordenes de Compra:</b> Los datos del formulario de Factura ahora se guardan y se recuperan automaticamente.",
        "<b>Mejora en tamano de letra de PDFs:</b> Los campos del encabezado de las Ordenes de Compra ahora son mas legibles (12pt).",
        "<b>Catalogo completo via web:</b> El bot ahora envia el enlace a gimmicks.com.ec cuando se solicita el catalogo completo.",
        "<b>Migracion de WhatsApp:</b> Configuracion exitosa del nuevo numero de WhatsApp (+593 96 356 0326) para el sistema.",
        "<b>Correccion de imagenes:</b> Solucion definitiva para la persistencia de imagenes de productos tras actualizaciones del sistema.",
    ]
    for imp in improvements:
        elements.append(Paragraph(imp, bullet, bulletText="\u2022"))
    
    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=green, spaceAfter=10))
    elements.append(Paragraph(
        "<i>Este documento es confidencial y esta destinado exclusivamente para uso interno de Gimmicks Marketing Services.</i>",
        ParagraphStyle('Footer', parent=body, fontSize=8, textColor=HexColor('#999999'), alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    print(f"PDF generado: {output_path}")
    return output_path

if __name__ == "__main__":
    build_report()
