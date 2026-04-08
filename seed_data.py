import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import Categoria, Producto
from decimal import Decimal

cat_elect, _ = Categoria.objects.get_or_create(nombre='Electronica', defaults={'descripcion': 'Equipos electronicos'})
cat_ofic, _ = Categoria.objects.get_or_create(nombre='Oficina', defaults={'descripcion': 'Suministros de oficina'})
cat_herr, _ = Categoria.objects.get_or_create(nombre='Herramientas', defaults={'descripcion': 'Herramientas'})

productos = [
    dict(categoria=cat_elect, codigo_sku='ELEC-001', nombre='Laptop HP 15 Core i5', precio_costo=Decimal('600.00'), precio_venta=Decimal('899.99'), stock_actual=Decimal('15'), unidad_medida='Unidad'),
    dict(categoria=cat_elect, codigo_sku='ELEC-002', nombre='Monitor Samsung 24 FHD', precio_costo=Decimal('150.00'), precio_venta=Decimal('229.99'), stock_actual=Decimal('8'), unidad_medida='Unidad'),
    dict(categoria=cat_elect, codigo_sku='ELEC-003', nombre='Teclado Mecanico Redragon', precio_costo=Decimal('35.00'), precio_venta=Decimal('59.99'), stock_actual=Decimal('25'), unidad_medida='Unidad'),
    dict(categoria=cat_elect, codigo_sku='ELEC-004', nombre='Mouse Inalambrico Logitech', precio_costo=Decimal('18.00'), precio_venta=Decimal('34.99'), stock_actual=Decimal('30'), unidad_medida='Unidad'),
    dict(categoria=cat_ofic, codigo_sku='OFIC-001', nombre='Resma de Papel A4 500 hojas', precio_costo=Decimal('4.50'), precio_venta=Decimal('7.99'), stock_actual=Decimal('100'), unidad_medida='Resma'),
    dict(categoria=cat_ofic, codigo_sku='OFIC-002', nombre='Archivador Palanca Grande', precio_costo=Decimal('2.00'), precio_venta=Decimal('4.50'), stock_actual=Decimal('50'), unidad_medida='Unidad'),
    dict(categoria=cat_herr, codigo_sku='HERR-001', nombre='Taladro Inalambrico Bosch 18V', precio_costo=Decimal('80.00'), precio_venta=Decimal('139.99'), stock_actual=Decimal('12'), unidad_medida='Unidad'),
    dict(categoria=cat_herr, codigo_sku='HERR-002', nombre='Juego de Llaves Stanley', precio_costo=Decimal('25.00'), precio_venta=Decimal('44.99'), stock_actual=Decimal('20'), unidad_medida='Set'),
]

creados = 0
for data in productos:
    _, created = Producto.objects.get_or_create(codigo_sku=data['codigo_sku'], defaults=data)
    if created:
        creados += 1

print(f'Categorias: {Categoria.objects.count()}')
print(f'Productos creados ahora: {creados}')
print(f'Total productos en DB: {Producto.objects.count()}')
