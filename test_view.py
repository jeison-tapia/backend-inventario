import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.views import TransaccionViewSet
from inventario.models import Usuario
from rest_framework.test import APIRequestFactory

try:
    factory = APIRequestFactory()
    request = factory.get('/api/transacciones/exportar_csv/?fecha_inicio=2026-03-19&fecha_fin=2026-03-26')
    
    user = Usuario.objects.filter(rol='ADMIN').first()
    if not user:
        print("No admin user found")
    else:
        from rest_framework.request import Request
        request.user = user
        view = TransaccionViewSet.as_view({'get': 'exportar_csv'})
        response = view(request)
        print("Status code:", response.status_code)
        print("Content sample:", response.content[:100])
except Exception as e:
    import traceback
    traceback.print_exc()
