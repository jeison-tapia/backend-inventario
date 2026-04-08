import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.views import UsuarioViewSet
from inventario.models import Usuario
from rest_framework.test import APIRequestFactory, force_authenticate

try:
    factory = APIRequestFactory()
    
    data = {
        "id": 1, "username": "admin", "email": "javier@admin.com", 
        "rol": "ADMIN", "telefono": None, "first_name": "Jeison", "last_name": "Tapia"
    }
    request = factory.patch('/api/usuarios/mi_perfil/', data, format='json')
    
    user = Usuario.objects.filter(rol='ADMIN').first()
    if not user:
        print("No admin user found")
    else:
        force_authenticate(request, user=user)
        view = UsuarioViewSet.as_view({'patch': 'mi_perfil'})
        response = view(request)
        print("Status code:", response.status_code)
        
        if hasattr(response, 'render'):
            response.render()
        print("Content:", response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
