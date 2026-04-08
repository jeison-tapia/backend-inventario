from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaViewSet, ProductoViewSet, UsuarioViewSet, 
    TransaccionViewSet, DetalleTransaccionViewSet, ProveedorViewSet,
    AuditLogViewSet, PagoViewSet,
    BodegaViewSet, InventarioBodegaViewSet,
    TurnoCajaViewSet, MovimientoCajaViewSet, PlanViewSet,
    EmpresaClienteViewSet
)

router = DefaultRouter()
router.register(r'planes', PlanViewSet)
router.register(r'empresas', EmpresaClienteViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'usuarios', UsuarioViewSet)
router.register(r'transacciones', TransaccionViewSet, basename='transaccion')
router.register(r'detalles', DetalleTransaccionViewSet, basename='detalle')
router.register(r'proveedores', ProveedorViewSet)
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')
router.register(r'pagos', PagoViewSet, basename='pago')  # [Hito 6]
router.register(r'bodegas', BodegaViewSet, basename='bodega')
router.register(r'inventario-bodegas', InventarioBodegaViewSet, basename='inventariobodega')
router.register(r'turnos-caja', TurnoCajaViewSet, basename='turnocaja')
router.register(r'movimientos-caja', MovimientoCajaViewSet, basename='movimientocaja')

urlpatterns = [
    path('', include(router.urls)),
]
