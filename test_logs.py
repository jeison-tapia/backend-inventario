import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import AuditLog, Usuario
print("Logs:", AuditLog.objects.count())

admin = Usuario.objects.filter(username='admin').first()
if admin:
    print("Admin is_staff:", admin.is_staff)
    print("Admin rol:", admin.rol)
