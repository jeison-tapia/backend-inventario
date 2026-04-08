import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import Producto
from django.db.models import F

bajos = Producto.objects.filter(stock_actual__lte=F('stock_minimo'))
print("Count from DB lookup:", bajos.count())
for b in bajos:
    print(b.nombre, b.stock_actual, b.stock_minimo)

all_p = Producto.objects.all()
cnt = 0
for p in all_p:
    if p.stock_actual <= p.stock_minimo:
        cnt += 1
print("Count from loop:", cnt)
