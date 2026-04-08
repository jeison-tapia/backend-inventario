import io
from django.core.mail import EmailMessage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.conf import settings

def generar_pdf_en_memoria(transaccion):
    """
    Dibuja el PDF de la factura/cotización usando ReportLab en un objeto BytesIO
    para nunca tocar el FileSystem del servidor.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Cabecera
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, f"DOCUMENTO: {transaccion.numero_documento or 'Borrador'}")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"TIPO: {transaccion.get_tipo_documento_display()}")
    p.drawString(50, height - 100, f"FECHA: {transaccion.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")
    
    # Cliente
    if transaccion.cliente:
        p.drawString(50, height - 130, f"CLIENTE: {transaccion.cliente.first_name} {transaccion.cliente.last_name}")
        p.drawString(50, height - 150, f"EMAIL: {transaccion.cliente.email}")
        
    p.line(50, height - 170, width - 50, height - 170)
    
    # Detalle
    y = height - 200
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "PRODUCTO")
    p.drawString(300, y, "CANTIDAD")
    p.drawString(400, y, "P. UNITARIO")
    p.drawString(500, y, "SUBTOTAL")
    
    y -= 20
    p.setFont("Helvetica", 10)
    for det in transaccion.detalles.all():
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 10)
            
        p.drawString(50, y, str(det.producto.nombre)[:35])
        p.drawString(300, y, str(det.cantidad))
        p.drawString(400, y, f"${det.precio_historico_venta}")
        p.drawString(500, y, f"${det.subtotal_linea}")
        y -= 20

    p.line(50, y - 10, width - 50, y - 10)
    
    # Total
    p.setFont("Helvetica-Bold", 14)
    p.drawString(380, y - 35, "TOTAL B2B:")
    p.drawString(500, y - 35, f"${transaccion.total_final}")
    
    p.save()
    buffer.seek(0)
    return buffer

def despachar_factura_correo(transaccion):
    """
    Genera el PDF y envía el E-mail al cliente usando la configuración de Django
    """
    if not transaccion.cliente or not transaccion.cliente.email:
        return False, "El cliente no tiene un correo electrónico válido registrado."
        
    try:
        buffer_pdf = generar_pdf_en_memoria(transaccion)
        
        asunto = f"Tu {transaccion.get_tipo_documento_display().lower()} de B2B Sistema ({transaccion.numero_documento})"
        cuerpo = f"""
        Hola {transaccion.cliente.first_name},
        
        Agradecemos tu confianza. Adjuntamos el documento físico en formato PDF correspondiente a tu {transaccion.get_tipo_documento_display().lower()}.
        
        Total a Cancelar/Cancelado: ${transaccion.total_final}
        
        Atentamente,
        El Equipo de B2B Sistema.
        """
        
        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[transaccion.cliente.email]
        )
        
        # Adjuntar PDF
        nombre_archivo = f"{transaccion.numero_documento or 'documento'}.pdf"
        email.attach(nombre_archivo, buffer_pdf.read(), 'application/pdf')
        email.send()
        
        return True, "Correo despachado correctamente"
    except Exception as e:
        return False, str(e)

def alerta_stock_admin(producto, nueva_cantidad):
    """
    Despacha un SOS al staff cuando se quiebra el stock.
    (Simulado para imprimir en consola)
    """
    asunto = f"[ALERTA URGENTE] Quiebre de Stock: {producto.nombre}"
    cuerpo = f"""
    SISTEMA AUTOMÁTICO B2B
    
    El producto {producto.codigo_sku} - {producto.nombre} ha caído por debajo de su límite mínimo operacional.
    
    Mínimo Configurado: {producto.stock_minimo}
    Nivel Actual Registrado: {nueva_cantidad}
    
    Por favor emite una Orden de Compra urgente para restituir el abastecimiento en bodegas.
    """
    email = EmailMessage(
        subject=asunto,
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['administrador@b2bsistema.com'] # Dirección de prueba estática para simulación en consola
    )
    email.send()
