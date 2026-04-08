import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import Transaccion, DetalleTransaccion
import traceback

try:
    venta = Transaccion.objects.filter(tipo_documento='VENTA', estado='EMITIDA').last()
    if not venta:
        print("No hay venta emitida para probar")
    else:
        item = venta.detalles.first()
        devolucion = Transaccion.objects.create(
            tipo_documento='DEVOLUCION',
            estado='BORRADOR',
            cliente=venta.cliente,
            transaccion_origen=venta,
            observaciones='test',
        )
        d = DetalleTransaccion.objects.create(
            transaccion=devolucion,
            producto=item.producto,
            cantidad=1,
        )
        print("Success")
except Exception as e:
    with open('err.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
