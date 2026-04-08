import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.views import ProductoViewSet
from inventario.models import Usuario
from rest_framework.test import APIRequestFactory, force_authenticate

factory = APIRequestFactory()
request = factory.get('/api/productos/bajo_stock/')

admin = Usuario.objects.filter(username='admin').first()
force_authenticate(request, user=admin)

view = ProductoViewSet.as_view({'get': 'bajo_stock'})
response = view(request)

if hasattr(response, 'render'):
    response.render()
print("Status:", response.status_code)
print("Data:", response.content.decode('utf-8'))
