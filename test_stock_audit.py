import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_ventas.settings')
django.setup()

from inventario.models import Bodega, Producto, InventarioBodega, AuditLog, Usuario

def test_stock_edit_audit():
    print("--- Testing Stock Edit Audit ---")
    
    # Get user
    user = Usuario.objects.first()
    if not user:
        print("No user found")
        return

    # Get a bodega and product
    bodega = Bodega.objects.first()
    producto = Producto.objects.first()
    
    if not bodega or not producto:
        print("Missing data: bodega or product")
        return

    # Get or create inventory record
    inv, created = InventarioBodega.objects.get_or_create(
        bodega=bodega,
        producto=producto,
        defaults={'cantidad': 10.0}
    )
    
    # Update quantity
    old_qty = inv.cantidad
    new_qty = float(old_qty) + 5.0
    print(f"Updating stock for {producto.nombre} in {bodega.nombre} from {old_qty} to {new_qty}...")
    
    inv.cantidad = new_qty
    inv.save()
    
    # Check audit log
    last_log = AuditLog.objects.filter(tabla_afectada='InventarioBodega').first()
    if last_log and 'EDITAR STOCK BODEGA' in last_log.accion:
        print(f"✅ Success: Stock edit audited. Log: {last_log.descripcion}")
    else:
        print("❌ Error: Stock edit NOT audited or log not found")

if __name__ == "__main__":
    test_stock_edit_audit()
