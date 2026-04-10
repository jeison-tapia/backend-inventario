from rest_framework import serializers
from .models import Categoria, Producto, Usuario, Transaccion, DetalleTransaccion, Proveedor, AuditLog, Pago, Bodega, InventarioBodega, TurnoCaja, MovimientoCaja, Plan, EmpresaCliente
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class EmpresaClienteSerializer(serializers.ModelSerializer):
    plan_nombre = serializers.ReadOnlyField(source='plan.nombre')
    admin_username = serializers.SerializerMethodField()
    
    def get_admin_username(self, obj):
        admin = obj.empleados.filter(rol='ADMIN').first()
        return admin.username if admin else 'Sin asignar'
    
    class Meta:
        model = EmpresaCliente
        fields = '__all__'

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Asegurarnos de que Javier sea admin al instante de iniciar sesión
        if self.user.username.lower() == 'javier':
            self.user.rol = 'ADMIN'
            self.user.is_superuser = True
            self.user.is_staff = True
            self.user.save()

        # Bloqueo total al intentar loguearse si la empresa está inactiva
        if self.user.empresa and not self.user.empresa.activo and not self.user.is_superuser:
            raise serializers.ValidationError(
                {"detail": "Su empresa se encuentra inactiva. Contacte al administrador."}
            )
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['rol'] = user.rol
        token['is_superuser'] = user.is_superuser
        if user.empresa:
            token['empresa'] = user.empresa.nombre
            plan = user.empresa.plan
            token['plan'] = {
                'nombre': plan.nombre,
                'modulo_inventario': plan.modulo_inventario,
                'modulo_ventas': plan.modulo_ventas,
                'modulo_compras': plan.modulo_compras,
                'modulo_caja': plan.modulo_caja,
                'modulo_reportes': plan.modulo_reportes,
                'modulo_auditoria': plan.modulo_auditoria,
                'modulo_clientes': plan.modulo_clientes,
                'modulo_catalogo': plan.modulo_catalogo,
                'modulo_etiquetas': plan.modulo_etiquetas,
                'modulo_usuarios': plan.modulo_usuarios,
            }
        return token

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = '__all__'

class InventarioBodegaSerializer(serializers.ModelSerializer):
    bodega_nombre = serializers.ReadOnlyField(source='bodega.nombre')
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.codigo_sku')
    
    class Meta:
        model = InventarioBodega
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')
    # [Hito 6] Campos calculados de vencimiento
    dias_para_vencer = serializers.ReadOnlyField()
    estado_vencimiento = serializers.ReadOnlyField()
    # [Hito 7] Inventario segregado
    inventarios = InventarioBodegaSerializer(source='inventario_bodegas', many=True, read_only=True)

    class Meta:
        model = Producto
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    # [Hito 6] Campos de crédito calculados
    deuda_actual = serializers.ReadOnlyField()
    credito_disponible = serializers.ReadOnlyField()
    empresa_detalle = EmpresaClienteSerializer(source='empresa', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'rol', 'telefono', 'first_name', 'last_name',
                  'password', 'credito_limite', 'deuda_actual', 'credito_disponible', 'empresa', 'empresa_detalle']
        extra_kwargs = {
            'password': {'write_only': True},
            'empresa': {'required': False}
        }
    
    def create(self, validated_data):
        user = Usuario(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)

class DetalleTransaccionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_sku = serializers.ReadOnlyField(source='producto.codigo_sku')

    class Meta:
        model = DetalleTransaccion
        fields = '__all__'
        read_only_fields = ['precio_historico_costo', 'precio_historico_venta', 
                            'subtotal_linea', 'margen_linea']

class PagoSerializer(serializers.ModelSerializer):
    """[Hito 6] Serializer para registrar pagos con método y referencia"""
    class Meta:
        model = Pago
        fields = '__all__'
        read_only_fields = ['fecha_pago']

class TransaccionSerializer(serializers.ModelSerializer):
    detalles = DetalleTransaccionSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)
    cliente_nombre = serializers.ReadOnlyField(source='cliente.username')
    proveedor_nombre = serializers.ReadOnlyField(source='proveedor.razon_social')
    # [Hito 6] Mostrar número de documento legible
    transaccion_origen_numero = serializers.ReadOnlyField(source='transaccion_origen.numero_documento')
    # [Hito 7] Detalles de Bodega
    bodega_nombre = serializers.ReadOnlyField(source='bodega.nombre')
    bodega_destino_nombre = serializers.ReadOnlyField(source='bodega_destino.nombre')

    class Meta:
        model = Transaccion
        fields = '__all__'
        read_only_fields = ['total_final', 'numero_documento']

class AuditLogSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.username')

    class Meta:
        model = AuditLog
        fields = '__all__'


class MovimientoCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCaja
        fields = '__all__'
        read_only_fields = ['fecha']


class TurnoCajaSerializer(serializers.ModelSerializer):
    apertura_por_nombre = serializers.ReadOnlyField(source='apertura_por.username')
    movimientos = MovimientoCajaSerializer(many=True, read_only=True)
    # Totales calculados en tiempo real (solo lectura)
    total_ventas_efectivo = serializers.SerializerMethodField()
    total_ventas_tarjeta = serializers.SerializerMethodField()
    total_ventas_transferencia = serializers.SerializerMethodField()
    total_ingresos_manuales = serializers.SerializerMethodField()
    total_egresos_manuales = serializers.SerializerMethodField()

    def get_total_ventas_efectivo(self, obj):
        from django.db.models import Sum
        return float(obj.pagos_del_turno.filter(metodo='EFECTIVO').aggregate(t=Sum('monto'))['t'] or 0)

    def get_total_ventas_tarjeta(self, obj):
        from django.db.models import Sum
        return float(obj.pagos_del_turno.filter(metodo='TARJETA').aggregate(t=Sum('monto'))['t'] or 0)

    def get_total_ventas_transferencia(self, obj):
        from django.db.models import Sum
        return float(obj.pagos_del_turno.filter(metodo='TRANSFERENCIA').aggregate(t=Sum('monto'))['t'] or 0)

    def get_total_ingresos_manuales(self, obj):
        from django.db.models import Sum
        return float(obj.movimientos.filter(tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0)

    def get_total_egresos_manuales(self, obj):
        from django.db.models import Sum
        return float(obj.movimientos.filter(tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0)

    class Meta:
        model = TurnoCaja
        fields = '__all__'
        read_only_fields = ['fecha_apertura', 'fecha_cierre', 'total_efectivo_esperado',
                            'diferencia', 'apertura_por']