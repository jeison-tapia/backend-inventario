from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AuditLog, Transaccion, Producto, Categoria, Proveedor, Usuario, InventarioBodega, TurnoCaja, MovimientoCaja
from django.db.models import Sum
from .middleware import get_current_user
from .utils_mail import alerta_stock_admin

MODELS_TO_AUDIT = [Transaccion, Producto, Categoria, Proveedor, Usuario, TurnoCaja, MovimientoCaja, InventarioBodega]

def register_audit_log(sender, instance, acc_type, **kwargs):
    if sender == AuditLog:
        return
        
    user = get_current_user()
    
    # Personalización de mensajes para hacerlo más amigable y rastreable
    accion_str = acc_type
    descripcion = f"[{acc_type}] {sender.__name__} (ID: {instance.pk})"
    
    if sender.__name__ == 'Transaccion':
        tipo = getattr(instance, 'tipo_documento', 'TRANSACCION')
        if acc_type == 'CREATE':
            accion_str = f'NUEVA {tipo}'
            descripcion = f"Se registró una nueva {tipo} con ID {instance.pk} por un total de ${instance.total_final}"
        elif acc_type == 'UPDATE':
            accion_str = f'ACTUALIZAR {tipo}'
            descripcion = f"Se modificó la {tipo} ID {instance.pk} (Estado: {instance.estado})"
        elif acc_type == 'DELETE':
            accion_str = f'ELIMINAR {tipo}'
            descripcion = f"Se eliminó la {tipo} ID {instance.pk}"
            
    elif sender.__name__ == 'Producto':
        nombre = getattr(instance, 'nombre', 'Producto')
        if acc_type == 'CREATE':
            accion_str = 'NUEVO PRODUCTO'
            descripcion = f"Se añadió el producto '{nombre}' al catálogo"
        elif acc_type == 'UPDATE':
            accion_str = 'ACTUALIZAR PRODUCTO'
            descripcion = f"Se actualizaron los datos o stock del producto '{nombre}'"
        elif acc_type == 'DELETE':
            accion_str = 'ELIMINAR PRODUCTO'
            descripcion = f"Se eliminó el producto '{nombre}' del catálogo"
            
    elif sender.__name__ == 'Usuario':
        username = getattr(instance, 'username', 'Usuario')
        if acc_type == 'UPDATE':
            accion_str = 'EDITAR PERFIL'
            descripcion = f"El usuario u operario '{username}' actualizó su perfil o credenciales"
    
    elif sender.__name__ == 'TurnoCaja':
        if acc_type == 'CREATE':
            accion_str = 'APERTURA DE CAJA'
            descripcion = f"Apertura de turno #{instance.pk} por {instance.apertura_por} con ${instance.monto_inicial}"
        elif acc_type == 'UPDATE':
            if instance.estado == 'CERRADO':
                accion_str = 'CIERRE DE CAJA'
                descripcion = f"Cierre de turno #{instance.pk}. Diferencia: ${instance.diferencia}. Obs: {instance.observaciones_cierre or 'Ninguna'}"
            else:
                accion_str = 'ACTUALIZAR TURNO'
                descripcion = f"Se actualizaron los datos del turno #{instance.pk}"
        elif acc_type == 'DELETE':
            accion_str = 'ELIMINAR TURNO'
            descripcion = f"Se eliminó el registro del turno #{instance.pk}"

    elif sender.__name__ == 'MovimientoCaja':
        if acc_type == 'CREATE':
            accion_str = f'MOVIMIENTO {instance.tipo}'
            descripcion = f"Se registró un {instance.tipo.lower()} de ${instance.monto} por: {instance.motivo} (Turno #{instance.turno.pk})"
        elif acc_type == 'UPDATE':
            accion_str = 'ACTUALIZAR MOVIMIENTO'
            descripcion = f"Se modificó el movimiento #{instance.pk} ({instance.tipo}): {instance.motivo}"
        elif acc_type == 'DELETE':
            accion_str = 'ELIMINAR MOVIMIENTO'
            descripcion = f"Se eliminó el movimiento #{instance.pk}"

    elif sender.__name__ == 'InventarioBodega':
        if acc_type == 'CREATE':
            accion_str = 'ASIGNAR STOCK BODEGA'
            descripcion = f"Se asignaron {instance.cantidad} unidades de '{instance.producto.nombre}' a '{instance.bodega.nombre}'"
        elif acc_type == 'UPDATE':
            accion_str = 'EDITAR STOCK BODEGA'
            descripcion = f"Se actualizó el stock de '{instance.producto.nombre}' en '{instance.bodega.nombre}' a {instance.cantidad} unidades"
        elif acc_type == 'DELETE':
            accion_str = 'REMOVER STOCK BODEGA'
            descripcion = f"Se eliminó el registro de stock de '{instance.producto.nombre}' en '{instance.bodega.nombre}'"
            
    AuditLog.objects.create(
        usuario=user,
        accion=accion_str[:50].upper(),
        tabla_afectada=sender.__name__,
        registro_id=str(instance.pk),
        descripcion=descripcion
    )

for model in MODELS_TO_AUDIT:
    @receiver(post_save, sender=model, dispatch_uid=f"audit_save_{model.__name__}")
    def audit_post_save(sender, instance, created, **kwargs):
        accion = 'CREATE' if created else 'UPDATE'
        register_audit_log(sender, instance, accion, **kwargs)

    @receiver(post_delete, sender=model, dispatch_uid=f"audit_delete_{model.__name__}")
    def audit_post_delete(sender, instance, **kwargs):
        register_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_save, sender=InventarioBodega)
@receiver(post_delete, sender=InventarioBodega)
def sync_stock_actual(sender, instance, **kwargs):
    """Mantiene el stock_actual estático equivalente a la suma distribuida en todas las bodegas."""
    producto = instance.producto
    stock_anterior = producto.stock_actual
    total = InventarioBodega.objects.filter(producto=producto).aggregate(total=Sum('cantidad'))['total'] or 0
    producto.stock_actual = total
    producto.save(update_fields=['stock_actual'])

    # [Hito 7] Alerta de correo si el producto cruza silenciosamente el umbral mínimo
    if stock_anterior >= producto.stock_minimo and total < producto.stock_minimo:
        try:
            alerta_stock_admin(producto, total)
        except Exception as e:
            print(f"Error silencioso al enviar correo de alerta SOS: {e}")
