import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import Transaccion

try:
    qs = Transaccion.objects.all()
    for tr in qs:
        actor = tr.cliente.username if tr.cliente else (tr.proveedor.razon_social if tr.proveedor else 'N/A')
        print([tr.id, tr.tipo_documento, tr.estado, actor, tr.total_final, tr.fecha_creacion.strftime('%Y-%m-%d %H:%M')])
    print("SUCCESS: El script de CSV termino sin errores.")
except Exception as e:
    import traceback
    traceback.print_exc()
