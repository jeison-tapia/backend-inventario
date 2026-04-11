from rest_framework import permissions

class HasPlanPermission(permissions.BasePermission):
    """
    Verifica si el usuario tiene acceso a los módulos según el plan de su empresa.
    Si es superusuario (dueño del sistema), tiene todos los permisos.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # El superusuario (dueño del sistema) siempre tiene permiso
        if request.user.is_superuser:
            return True
            
        # Bloqueo por falta de pago (Empresa inactiva)
        if request.user.empresa and not request.user.empresa.activo:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Su acceso ha sido suspendido. Por favor, contacte al administrador para regularizar su pago.")

        # Si el usuario no pertenece a una empresa, no tiene acceso a módulos de negocio
        if not request.user.empresa:
            return request.method in permissions.SAFE_METHODS
            
        plan = request.user.empresa.plan
        
        # Mapeo de vistas a módulos del plan
        view_name = str(view.__class__)
        
        if any(v in view_name for v in ['ProductoViewSet', 'CategoriaViewSet', 'BodegaViewSet', 'InventarioBodegaViewSet']):
            return plan.modulo_inventario or request.method in permissions.SAFE_METHODS
            
        if 'TransaccionViewSet' in view_name:
            # Ventas y Cotizaciones
            if request.data.get('tipo_documento') in ['VENTA', 'COTIZACION'] or request.method in permissions.SAFE_METHODS:
                return plan.modulo_ventas
            # Compras
            if request.data.get('tipo_documento') == 'COMPRA':
                return plan.modulo_compras
            return True # Otros tipos o métodos seguros
            
        if 'ProveedorViewSet' in view_name:
            return plan.modulo_compras
            
        if 'UsuarioViewSet' in view_name:
            # Si quiere ver/gestionar clientes finales
            if request.query_params.get('rol') == 'CLIENTE_FINAL' or request.data.get('rol') == 'CLIENTE_FINAL':
                return plan.modulo_clientes
            # Si quiere gestionar personal
            return plan.modulo_usuarios
            
        if any(v in view_name for v in ['TurnoCajaViewSet', 'MovimientoCajaViewSet', 'PagoViewSet']):
            return plan.modulo_caja
            
        if 'rentabilidad' in getattr(view, 'action', '') or 'exportar' in getattr(view, 'action', ''):
            return plan.modulo_reportes
            
        if 'AuditLogViewSet' in view_name:
            return plan.modulo_auditoria
            
        return True

class IsAdminUser(permissions.BasePermission):
    """Solo permite acceso a administradores de empresa o superusuarios"""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return request.user.rol == 'ADMIN'

class IsVendedorUser(permissions.BasePermission):
    """Permite el acceso exclusivo a vendedores de mostrador"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == 'VENDEDOR')

class IsClienteUser(permissions.BasePermission):
    """Permite acceso exclusivo a clientes que consumen la tienda"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == 'CLIENTE_FINAL')

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Cualquiera que esté autenticado puede ver el catálogo (GET).
    Pero solo el ADMIN puede crear, editar o borrar (POST/PUT/DELETE).
    """
    def has_permission(self, request, view):
        # Obligatorio estar logueado
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Si solo quiere "ver", lo dejamos pasar
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Si quiere modificar, exigimos rol ADMIN
        return request.user.rol == 'ADMIN'

class IsVendedorOrAdmin(permissions.BasePermission):
    """
    Vendedores y Administradores tienen poder de gestión sobre ventas.
    Los clientes regulares NO pueden usar los métodos protegidos aquí.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.rol in ['ADMIN', 'VENDEDOR']
