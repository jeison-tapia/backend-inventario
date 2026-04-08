import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.views import AuditLogViewSet
from inventario.models import Usuario
from rest_framework.test import APIRequestFactory, force_authenticate

try:
    factory = APIRequestFactory()
    request = factory.get('/api/audit-logs/')
    
    user = Usuario.objects.filter(username='admin').first()
    force_authenticate(request, user=user)
    view = AuditLogViewSet.as_view({'get': 'list'})
    response = view(request)
    
    if hasattr(response, 'render'):
        response.render()
    print("Status:", response.status_code)
    print("Data:", response.content.decode('utf-8')[:500])
except Exception as e:
    import traceback
    traceback.print_exc()
