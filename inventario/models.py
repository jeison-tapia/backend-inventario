from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework.exceptions import ValidationError
from django.utils import timezone

class ModeloAuditoriaBase(models.Model):
    """Clase abstracta para heredar campos de rastreo a todas las tablas"""
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Plan(models.Model):
    """Define los límites y accesos de la cuenta según la suscripción del cliente del sistema"""
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    # Módulos/Funcionalidades que el superusuario habilita para este plan
    modulo_inventario = models.BooleanField(default=True, help_text="Habilita Categorías, Productos, Bodegas")
    modulo_ventas = models.BooleanField(default=True, help_text="Habilita Transacciones de Venta y Cotización")
    modulo_compras = models.BooleanField(default=True, help_text="Habilita Compras a Proveedores y Proveedores")
    modulo_caja = models.BooleanField(default=True, help_text="Habilita Turnos y Movimientos de Caja")
    modulo_reportes = models.BooleanField(default=False, help_text="Habilita Reportes de Rentabilidad y Exportación")
    modulo_auditoria = models.BooleanField(default=False, help_text="Habilita Logs de Auditoría")
    
    # Nuevos módulos para sincronizar con el sidebar
    modulo_clientes = models.BooleanField(default=True, help_text="Habilita el módulo de Clientes")
    modulo_catalogo = models.BooleanField(default=True, help_text="Habilita el Catálogo de productos")
    modulo_etiquetas = models.BooleanField(default=True, help_text="Habilita la generación de etiquetas")
    modulo_usuarios = models.BooleanField(default=True, help_text="Habilita la gestión de Personal (Usuarios)")
    
    # Límites de capacidad por plan
    max_usuarios = models.IntegerField(default=5, help_text="Máximo de usuarios que el cliente puede crear")
    max_productos = models.IntegerField(default=100, help_text="Máximo de productos permitidos")
    
    def __str__(self):
        return self.nombre

class EmpresaCliente(ModeloAuditoriaBase):
    """Representa a un cliente del sistema (un negocio) que contrata el servicio"""
    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, unique=True, blank=True, null=True)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='empresas')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    """Tabla de usuarios. Puede ser Superusuario (Dueño Sistema) o Personal de una EmpresaCliente"""
    ROLES = (
        ('ADMIN', 'Administrador de Empresa'),
        ('VENDEDOR', 'Vendedor de Empresa'),
        ('CLIENTE_FINAL', 'Cliente Final (B2C)'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='CLIENTE_FINAL')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    # Vínculo con la empresa que contrata el servicio
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, null=True, blank=True, related_name='empleados')
    
    # [Hito 6] Crédito comercial para clientes finales
    credito_limite = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                         help_text='Monto máximo de crédito autorizado para este cliente')

    @property
    def deuda_actual(self):
        """Calcula la suma de todas las ventas EMITIDAS no ligadas a pagos completos"""
        return self.compras_cliente.filter(
            tipo_documento='VENTA', estado='EMITIDA'
        ).aggregate(total=models.Sum('total_final'))['total'] or 0

    @property
    def credito_disponible(self):
        return self.credito_limite - self.deuda_actual

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"

class Categoria(ModeloAuditoriaBase):
    """Familias de productos para organizar el catálogo"""
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, related_name='categorias', null=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return self.nombre

class Bodega(models.Model):
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, related_name='bodegas', null=True)
    nombre = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return f"{self.nombre} {'(Activa)' if self.activa else '(Inactiva)'}"

class Producto(ModeloAuditoriaBase):
    """Catálogo flexible: soporta ferreterías (unidades) o carnicerías (fracciones)"""
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, related_name='productos', null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT, related_name='productos')
    codigo_sku = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    # [Hito 6] Precios diferenciados por tipo de cliente
    precio_venta_distribuidor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                                     help_text='Precio especial para clientes distribuidores/VIP')
    
    permite_fracciones = models.BooleanField(default=False)
    unidad_medida = models.CharField(max_length=20, default='Unidad')
    destacado_en_web = models.BooleanField(default=False)
    
    stock_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    
    # [Hito 6] Fecha de vencimiento (opcional - para alimentos, medicamentos, etc.)
    fecha_vencimiento = models.DateField(null=True, blank=True,
                                          help_text='Dejar vacío si el producto no tiene vencimiento')

    class Meta:
        unique_together = ('empresa', 'codigo_sku')

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        delta = self.fecha_vencimiento - timezone.now().date()
        return delta.days

    @property
    def estado_vencimiento(self):
        dias = self.dias_para_vencer
        if dias is None:
            return 'N/A'
        if dias < 0:
            return 'VENCIDO'
        if dias <= 30:
            return 'POR_VENCER'
        return 'VIGENTE'

    def __str__(self):
        return f"[{self.codigo_sku}] {self.nombre}"

class InventarioBodega(models.Model):
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='inventarios')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='inventario_bodegas')
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('bodega', 'producto')

    def __str__(self):
        return f"{self.producto.nombre} en {self.bodega.nombre}: {self.cantidad}"

class Proveedor(ModeloAuditoriaBase):
    """Proveedores de inventario"""
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, related_name='proveedores', null=True)
    razon_social = models.CharField(max_length=200)
    identificacion_fiscal = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empresa', 'identificacion_fiscal')

    def __str__(self):
        return f"{self.identificacion_fiscal} - {self.razon_social}"

class Transaccion(ModeloAuditoriaBase):
    """Cabecera para Ventas, Cotizaciones, Compras y Devoluciones"""
    empresa = models.ForeignKey(EmpresaCliente, on_delete=models.CASCADE, related_name='transacciones', null=True)
    TIPO_CHOICES = [
        ('COMPRA', 'Compra a Proveedor'),
        ('VENTA', 'Venta a Cliente'),
        ('COTIZACION', 'Cotización'),
        ('DEVOLUCION', 'Devolución'),
        ('TRANSFERENCIA', 'Transferencia entre Bodegas'),
    ]
    ESTADOS = (('BORRADOR', 'Borrador'), ('EMITIDA', 'Emitida'), ('ANULADA', 'Anulada'))

    tipo_documento = models.CharField(max_length=20, choices=TIPO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')
    cliente = models.ForeignKey(Usuario, on_delete=models.SET_NULL, related_name='compras_cliente', null=True, blank=True, limit_choices_to={'rol': 'CLIENTE_FINAL'})
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, related_name='ventas_proveedor', null=True, blank=True)
    total_final = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # [Hito 7] Bodega origen/destino (null temporalmente por migración)
    bodega = models.ForeignKey(Bodega, on_delete=models.RESTRICT, null=True, blank=True, related_name='transacciones_origen')
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.RESTRICT, null=True, blank=True, related_name='transacciones_destino')

    # [Hito 6] Numeración automática de documentos legibles
    numero_documento = models.CharField(max_length=50, null=True, blank=True,
                                         help_text='Auto-generado: FAC-2026-0001')
    
    # [Hito 6] Para devoluciones parciales: referencia a la venta original
    transaccion_origen = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='devoluciones',
                                            help_text='Venta original que origina esta devolución')
    
    # [Hito 6] Notas u observaciones adicionales
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('empresa', 'numero_documento')

    def __str__(self):
        doc = self.numero_documento or f"#{self.id}"
        return f"{self.tipo_documento} {doc} - {self.estado}"

    def _generar_numero_documento(self):
        """Genera un código único y legible por tipo de documento, empresa y año"""
        prefijos = {
            'VENTA': 'FAC',
            'COTIZACION': 'COT',
            'COMPRA': 'COM',
            'DEVOLUCION': 'DEV',
            'TRANSFERENCIA': 'TRF',
        }
        prefijo = prefijos.get(self.tipo_documento, 'DOC')
        year = timezone.now().year
        # Buscar el último numero del mismo tipo, empresa y año
        ultimo = Transaccion.objects.filter(
            empresa=self.empresa,
            numero_documento__startswith=f"{prefijo}-{year}-"
        ).order_by('-numero_documento').first()
        if ultimo and ultimo.numero_documento:
            try:
                last_num = int(ultimo.numero_documento.split('-')[-1])
            except (ValueError, IndexError):
                last_num = 0
        else:
            last_num = 0
        return f"{prefijo}-{year}-{str(last_num + 1).zfill(4)}"

    def save(self, *args, **kwargs):
        # Auto-asignar numero_documento solo si es la primera vez
        if not self.numero_documento:
            self.numero_documento = self._generar_numero_documento()

        # Determinar el estado anterior antes de guardar
        estado_anterior = None
        if self.pk:
            try:
                estado_anterior = Transaccion.objects.get(pk=self.pk).estado
            except Transaccion.DoesNotExist:
                pass
            
        # 1. Validar Stock ANTES de guardar (Solo VENTA al emitir)
        # Esta validación se moverá a la lógica de negocio en los Views/Serializers
        # para manejar el inventario por bodega.
        if estado_anterior != 'EMITIDA' and self.estado == 'EMITIDA' and self.tipo_documento == 'VENTA':
            # if self.pk:
            #     for detalle in self.detalles.all():
            #         if detalle.producto.stock_actual < detalle.cantidad:
            #             raise ValidationError({
            #                 "error": f"Stock insuficiente para '{detalle.producto.nombre}'. "
            #                                  f"Disponible: {detalle.producto.stock_actual}, "
            #                                  f"Se intentó vender: {detalle.cantidad}"
            #             })
            pass # La validación de stock se hará a nivel de InventarioBodega en la lógica de negocio

        # Validaciones de actores requeridos
        if self.tipo_documento in ['VENTA', 'COTIZACION'] and not self.cliente:
            raise ValidationError({"cliente": "Se requiere un cliente para ventas o cotizaciones."})
        if self.tipo_documento == 'COMPRA' and not self.proveedor:
            raise ValidationError({"proveedor": "Se requiere un proveedor para registrar compras."})
        
        super().save(*args, **kwargs)
        
        # 2. Lógica de Stock Bidireccional al emitir
        if estado_anterior != 'EMITIDA' and self.estado == 'EMITIDA':
            if self.tipo_documento != 'COTIZACION' and not self.bodega:
                raise ValidationError({"bodega": "Debe especificar una bodega para emitir este documento."})
            
            if self.tipo_documento == 'VENTA':
                for detalle in self.detalles.all():
                    inv, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    if inv.cantidad < detalle.cantidad:
                        raise ValidationError({"error": f"Stock insuficiente en la bodega para '{detalle.producto.nombre}'."})
                    inv.cantidad -= detalle.cantidad
                    inv.save(update_fields=['cantidad'])
            elif self.tipo_documento == 'COMPRA' or self.tipo_documento == 'DEVOLUCION':
                for detalle in self.detalles.all():
                    inv, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    inv.cantidad += detalle.cantidad
                    inv.save(update_fields=['cantidad'])
            elif self.tipo_documento == 'TRANSFERENCIA':
                for detalle in self.detalles.all():
                    inv_origen, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    if inv_origen.cantidad < detalle.cantidad:
                        raise ValidationError({"error": f"Stock insuficiente en bodega origen para '{detalle.producto.nombre}'."})
                    inv_origen.cantidad -= detalle.cantidad
                    inv_origen.save(update_fields=['cantidad'])
                    inv_dest, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega_destino, producto=detalle.producto)
                    inv_dest.cantidad += detalle.cantidad
                    inv_dest.save(update_fields=['cantidad'])

        # 3. Lógica Inversa al ANULAR
        if estado_anterior == 'EMITIDA' and self.estado == 'ANULADA':
            if self.tipo_documento == 'VENTA':
                for detalle in self.detalles.all():
                    inv, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    inv.cantidad += detalle.cantidad
                    inv.save(update_fields=['cantidad'])
            elif self.tipo_documento == 'COMPRA' or self.tipo_documento == 'DEVOLUCION':
                for detalle in self.detalles.all():
                    inv, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    inv.cantidad -= detalle.cantidad
                    inv.save(update_fields=['cantidad'])
            elif self.tipo_documento == 'TRANSFERENCIA':
                for detalle in self.detalles.all():
                    inv_origen, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega, producto=detalle.producto)
                    inv_origen.cantidad += detalle.cantidad
                    inv_origen.save(update_fields=['cantidad'])
                    inv_dest, _ = InventarioBodega.objects.get_or_create(bodega=self.bodega_destino, producto=detalle.producto)
                    inv_dest.cantidad -= detalle.cantidad
                    inv_dest.save(update_fields=['cantidad'])

class DetalleTransaccion(ModeloAuditoriaBase):
    """El carrito de compras con registro histórico de precios y descuentos"""
    transaccion = models.ForeignKey(Transaccion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    precio_historico_costo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_historico_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # [Hito 6] Descuento aplicado a esta línea
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                                help_text='Porcentaje de descuento (0-100)')
    subtotal_linea = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # [Hito 6] Margen de ganancia de esta línea
    margen_linea = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def save(self, *args, **kwargs):
        # 1. Congelar precios actuales si es un detalle recién creado
        if not self.pk:
            self.precio_historico_costo = self.producto.precio_costo
            self.precio_historico_venta = self.producto.precio_venta
        
        # 2. Calcular subtotal con descuento aplicado
        if getattr(self, 'precio_historico_venta', None) and getattr(self, 'cantidad', None):
            from decimal import Decimal
            desc_pct = Decimal(str(self.descuento_porcentaje or 0))
            descuento_factor = Decimal('1') - (desc_pct / Decimal('100'))
            self.subtotal_linea = Decimal(str(self.cantidad)) * Decimal(str(self.precio_historico_venta)) * descuento_factor
        
        # 3. Calcular margen de ganancia de esta línea
        if getattr(self, 'precio_historico_venta', None) and getattr(self, 'precio_historico_costo', None) and getattr(self, 'cantidad', None):
            from decimal import Decimal
            desc_pct = Decimal(str(self.descuento_porcentaje or 0))
            margen_unitario = Decimal(str(self.precio_historico_venta)) - Decimal(str(self.precio_historico_costo))
            descuento_factor = Decimal('1') - (desc_pct / Decimal('100'))
            self.margen_linea = (margen_unitario * descuento_factor) * Decimal(str(self.cantidad))
            
        super().save(*args, **kwargs)
        
        # 4. Actualizar el total de la transacción padre
        if self.transaccion:
            detalles = self.transaccion.detalles.all()
            total = sum(d.subtotal_linea for d in detalles if d.subtotal_linea)
            self.transaccion.total_final = total
            self.transaccion.save(update_fields=['total_final'])

class Pago(ModeloAuditoriaBase):
    """[Hito 6] Registro de pagos asociados a una transaccion (soporte multi-método)"""
    METODOS = (
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de Crédito/Débito'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('MIXTO', 'Pago Mixto'),
    )
    transaccion = models.ForeignKey(Transaccion, on_delete=models.CASCADE, related_name='pagos')
    metodo = models.CharField(max_length=20, choices=METODOS, default='EFECTIVO')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    referencia = models.CharField(max_length=100, blank=True, null=True,
                                   help_text='Número de voucher, comprobante de transferencia, etc.')
    fecha_pago = models.DateTimeField(default=timezone.now)
    # [Hito 7A] Turno de caja activo al momento del pago
    turno_caja = models.ForeignKey('TurnoCaja', on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_del_turno')

    def __str__(self):
        return f"Pago #{self.id}: {self.metodo} ${self.monto} → {self.transaccion}"

class AuditLog(ModeloAuditoriaBase):
    """Registro inmutable de actividades de usuarios para auditoría y trazabilidad"""
    ACCIONES = (
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    accion = models.CharField(max_length=50, choices=ACCIONES)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.CharField(max_length=50)
    descripcion = models.TextField()

    def __str__(self):
        return f"[{self.fecha_creacion}] {self.usuario} - {self.accion} en {self.tabla_afectada}"
    
    class Meta:
        ordering = ['-fecha_creacion']


# ─────────────────────────────────────────────
# HITO 7-A: Módulo de Cierre de Caja
# ─────────────────────────────────────────────

class TurnoCaja(models.Model):
    """Representa un turno de trabajo de un cajero/vendedor.
    Se abre al inicio de la jornada declarando el efectivo base,
    y se cierra haciendo el arqueo final."""
    ESTADOS = (('ABIERTO', 'Abierto'), ('CERRADO', 'Cerrado'))

    apertura_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='turnos_caja'
    )
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text='Efectivo en caja al inicio del turno')
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='ABIERTO')

    # Calculados al momento del cierre
    total_efectivo_esperado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_efectivo_declarado = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                                    help_text='Monto contado físicamente al cierre')
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text='Positivo=sobrante, Negativo=faltante')
    observaciones_cierre = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Turno #{self.pk} - {self.apertura_por} - {self.estado}"

    class Meta:
        ordering = ['-fecha_apertura']


class MovimientoCaja(models.Model):
    """Registro de ingresos o egresos manuales dentro de un turno
    (p.ej. pago de servicios, retiro de efectivo, etc.)"""
    TIPOS = (('INGRESO', 'Ingreso manual'), ('EGRESO', 'Egreso manual'))

    turno = models.ForeignKey(
        TurnoCaja, on_delete=models.CASCADE, related_name='movimientos'
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} ${self.monto} - {self.motivo}"