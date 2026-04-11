from django.db.models import F, Sum
import csv
from django.http import HttpResponse
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import (Categoria, Producto, Usuario, Transaccion, DetalleTransaccion, 
                       Proveedor, AuditLog, Pago, Bodega, InventarioBodega, TurnoCaja, 
                       MovimientoCaja, Plan, EmpresaCliente)
from .serializers import (CategoriaSerializer, ProductoSerializer, UsuarioSerializer,
                           TransaccionSerializer, DetalleTransaccionSerializer,
                           ProveedorSerializer, CustomTokenObtainPairSerializer,
                           AuditLogSerializer, PagoSerializer, BodegaSerializer, 
                           InventarioBodegaSerializer, TurnoCajaSerializer, 
                           MovimientoCajaSerializer, PlanSerializer, EmpresaClienteSerializer)
from .permissions import (IsAdminOrReadOnly, IsVendedorOrAdmin, IsAdminUser, 
                           HasPlanPermission)
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone
from .utils_mail import despachar_factura_correo

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class PaginacionEstandar(PageNumberPagination):
    """Paginador por defecto para listas grandes"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAdminUser] # Solo superusuarios del sistema

class EmpresaClienteViewSet(viewsets.ModelViewSet):
    queryset = EmpresaCliente.objects.all()
    serializer_class = EmpresaClienteSerializer
    permission_classes = [permissions.IsAdminUser] # Solo superusuarios del sistema

    def perform_create(self, serializer):
        # 1. Crear la empresa
        empresa = serializer.save()
        
        # 2. Crear automáticamente el usuario administrador para esta empresa
        # Si vienen datos de admin en el request
        admin_data = self.request.data.get('admin_user')
        if admin_data:
            Usuario.objects.create_user(
                username=admin_data.get('username'),
                email=admin_data.get('email'),
                password=admin_data.get('password'),
                first_name=admin_data.get('first_name', ''),
                last_name=admin_data.get('last_name', ''),
                rol='ADMIN',
                empresa=empresa
            )

class BodegaViewSet(viewsets.ModelViewSet):
    queryset = Bodega.objects.all()
    serializer_class = BodegaSerializer
    permission_classes = [IsAdminOrReadOnly, HasPlanPermission]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Bodega.objects.all()
        return Bodega.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class InventarioBodegaViewSet(viewsets.ModelViewSet):
    queryset = InventarioBodega.objects.all()
    serializer_class = InventarioBodegaSerializer
    permission_classes = [permissions.IsAuthenticated, HasPlanPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['bodega__nombre', 'producto__nombre']
    ordering_fields = ['cantidad', 'fecha_actualizacion']

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = super().get_queryset()
        else:
            queryset = InventarioBodega.objects.filter(bodega__empresa=self.request.user.empresa)
            
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            queryset = queryset.filter(producto__categoria_id=categoria_id)
        return queryset

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAdminOrReadOnly, HasPlanPermission]
    pagination_class = PaginacionEstandar
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['razon_social', 'identificacion_fiscal', 'email']
    ordering_fields = ['razon_social', 'fecha_creacion']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Proveedor.objects.all()
        return Proveedor.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminOrReadOnly, HasPlanPermission]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Categoria.objects.all()
        return Categoria.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAdminOrReadOnly, HasPlanPermission]
    pagination_class = PaginacionEstandar
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'codigo_sku', 'categoria__nombre']
    ordering_fields = ['precio_venta', 'precio_costo', 'nombre', 'stock_actual']

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = super().get_queryset()
        else:
            queryset = Producto.objects.filter(empresa=self.request.user.empresa)
            
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """Endpoint para alertas: productos en estado crítico"""
        queryset = self.get_queryset().filter(stock_actual__lte=F('stock_minimo'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def proximos_a_vencer(self, request):
        """[Hito 6] Productos que vencen en los próximos 30 días"""
        hoy = timezone.now().date()
        limite = hoy + timezone.timedelta(days=30)
        queryset = self.get_queryset().filter(
            fecha_vencimiento__isnull=False,
            fecha_vencimiento__lte=limite
        ).order_by('fecha_vencimiento')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    def get_permissions(self):
        return [IsVendedorOrAdmin(), HasPlanPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Usuario.objects.all()
        if user.rol == 'VENDEDOR':
            return Usuario.objects.filter(empresa=user.empresa, rol='CLIENTE_FINAL')
        return Usuario.objects.filter(empresa=user.empresa)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        # Solo superusuario del sistema puede crear empresas y asignar personal a ellas libremente
        if not self.request.user.is_superuser:
            # Los administradores de empresa solo crean personal para su propia empresa
            serializer.save(empresa=self.request.user.empresa)
        else:
            serializer.save()

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        # Solo superusuario puede cambiar de empresa a un usuario
        if 'empresa' in serializer.validated_data and not self.request.user.is_superuser:
            raise PermissionDenied("No puedes cambiar la empresa de un usuario.")

        if not self.request.user.is_superuser:
            if self.request.user.rol == 'VENDEDOR' and serializer.instance.rol != 'CLIENTE_FINAL':
                raise PermissionDenied("Los vendedores solo pueden editar datos de clientes finales.")
        serializer.save()

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def mi_perfil(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['get'])
    def estado_credito(self, request, pk=None):
        """[Hito 6] Resumen de crédito de un cliente"""
        usuario = self.get_object()
        return Response({
            'credito_limite': usuario.credito_limite,
            'deuda_actual': usuario.deuda_actual,
            'credito_disponible': usuario.credito_disponible,
        })

class TransaccionViewSet(viewsets.ModelViewSet):
    serializer_class = TransaccionSerializer
    pagination_class = PaginacionEstandar
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['cliente__username', 'proveedor__razon_social', 'tipo_documento', 'estado', 'numero_documento']
    ordering_fields = ['fecha_creacion', 'total_final']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsVendedorOrAdmin(), HasPlanPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Transaccion.objects.all()
        if user.rol == 'CLIENTE_FINAL':
            return Transaccion.objects.filter(cliente=user)
        return Transaccion.objects.filter(empresa=user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

    @action(detail=True, methods=['post'])
    def convertir_a_venta(self, request, pk=None):
        """[Hito 6] Convierte una COTIZACION en VENTA manteniendo los mismos detalles"""
        cotizacion = self.get_object()
        if cotizacion.tipo_documento != 'COTIZACION':
            return Response({'error': 'Solo se pueden convertir cotizaciones.'}, status=400)
        if cotizacion.estado == 'ANULADA':
            return Response({'error': 'No se puede convertir una cotización anulada.'}, status=400)

        # Crear nueva VENTA a partir de la cotización
        venta = Transaccion.objects.create(
            tipo_documento='VENTA',
            estado='BORRADOR',
            cliente=cotizacion.cliente,
            bodega=cotizacion.bodega,
            observaciones=f'Convertida desde cotización {cotizacion.numero_documento}',
            transaccion_origen=cotizacion,
        )
        # Copiar todos los detalles
        for detalle in cotizacion.detalles.all():
            DetalleTransaccion.objects.create(
                transaccion=venta,
                producto=detalle.producto,
                cantidad=detalle.cantidad,
                descuento_porcentaje=detalle.descuento_porcentaje,
            )
        serializer = self.get_serializer(venta)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'])
    def devolucion_parcial(self, request, pk=None):
        """[Hito 6] Crea una devolución parcial de ítems de una venta"""
        from rest_framework import status as drf_status
        venta_original = self.get_object()
        if venta_original.tipo_documento != 'VENTA' or venta_original.estado != 'EMITIDA':
            return Response({'error': 'Solo se puede devolver de una venta emitida.'}, status=400)

        items = request.data.get('items', [])  # [{producto_id, cantidad}]
        if not items:
            return Response({'error': 'Debes especificar al menos un ítem a devolver.'}, status=400)

        devolucion = Transaccion.objects.create(
            tipo_documento='DEVOLUCION',
            estado='BORRADOR',
            cliente=venta_original.cliente,
            bodega=venta_original.bodega,
            transaccion_origen=venta_original,
            empresa=venta_original.empresa,
            observaciones=f'Devolución parcial de {venta_original.numero_documento}',
        )

        # Insertar los ítems que el usuario quiere devolver
        for item in items:
            producto_id = item.get('producto_id')
            cantidad = float(item.get('cantidad', 0))
            if not producto_id or cantidad <= 0:
                continue
            # Verificar que el producto existe en la venta original
            detalle_orig = venta_original.detalles.filter(producto_id=producto_id).first()
            if not detalle_orig:
                continue
            # No puede devolver más de lo comprado
            cantidad = min(cantidad, float(detalle_orig.cantidad))
            DetalleTransaccion.objects.create(
                transaccion=devolucion,
                producto_id=producto_id,
                cantidad=cantidad,
                descuento_porcentaje=detalle_orig.descuento_porcentaje
            )

        devolucion.estado = 'EMITIDA'
        devolucion.save()

        return Response(TransaccionSerializer(devolucion).data, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enviar_correo(self, request, pk=None):
        """Genera el PDF en memoria y lo despacha al cliente"""
        transaccion = self.get_object()
        if transaccion.estado != 'EMITIDA':
            return Response({'error': 'Solo se pueden enviar documentos EMITIDOS.'}, status=status.HTTP_400_BAD_REQUEST)
        
        exito, msg = despachar_factura_correo(transaccion)
        if exito:
            return Response({'mensaje': msg}, status=status.HTTP_200_OK)
        else:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def rentabilidad(self, request):
        """[Hito 6] Reporte de margen bruto por período"""
        if not request.user.is_superuser:
            empresa = getattr(request.user, 'empresa', None)
            if not empresa or not empresa.plan.modulo_reportes:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Su plan no permite ver reportes de rentabilidad.")

        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        qs = DetalleTransaccion.objects.filter(
            transaccion__tipo_documento='VENTA',
            transaccion__estado='EMITIDA',
        )
        if fecha_inicio and fecha_fin:
            qs = qs.filter(transaccion__fecha_creacion__range=[fecha_inicio, fecha_fin])

        total_ventas = qs.aggregate(total=Sum('subtotal_linea'))['total'] or 0
        total_costo = sum(
            (d.precio_historico_costo or 0) * d.cantidad for d in qs
        )
        total_margen = sum(d.margen_linea for d in qs if d.margen_linea)

        return Response({
            'total_ingresos': float(total_ventas),
            'total_costo': float(total_costo),
            'margen_bruto': float(total_margen),
            'margen_porcentaje': round((float(total_margen) / float(total_ventas) * 100), 2) if total_ventas else 0,
        })

    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        if not request.user.is_superuser:
            empresa = getattr(request.user, 'empresa', None)
            if not empresa or not empresa.plan.modulo_reportes:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Su plan no permite exportar reportes.")

        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        queryset = self.get_queryset()
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha_creacion__range=[fecha_inicio, fecha_fin])

        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transacciones"
        ws.append(['Número', 'Tipo', 'Estado', 'Cliente/Proveedor', 'Total', 'Fecha'])

        for tr in queryset:
            actor = tr.cliente.username if tr.cliente else (tr.proveedor.razon_social if tr.proveedor else 'N/A')
            ws.append([
                tr.numero_documento or f'#{tr.id}',
                tr.tipo_documento, tr.estado, actor,
                float(tr.total_final), tr.fecha_creacion.strftime('%Y-%m-%d %H:%M')
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="reporte_transacciones.xlsx"'
        wb.save(response)
        return response

    @action(detail=False, methods=['get'])
    def exportar_pdf(self, request):
        if not request.user.is_superuser:
            empresa = getattr(request.user, 'empresa', None)
            if not empresa or not empresa.plan.modulo_reportes:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Su plan no permite exportar reportes.")

        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        queryset = self.get_queryset()
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha_creacion__range=[fecha_inicio, fecha_fin])

        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_transacciones.pdf"'
        doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Reporte de Transacciones y Movimientos", styles['Title']))
        elements.append(Spacer(1, 20))

        data = [['Número', 'Tipo', 'Estado', 'Actor', 'Total ($)', 'Fecha']]
        for tr in queryset:
            actor = tr.cliente.username if tr.cliente else (tr.proveedor.razon_social if tr.proveedor else 'N/A')
            data.append([
                tr.numero_documento or f'#{tr.id}',
                tr.tipo_documento, tr.estado, actor,
                f"{tr.total_final:.2f}", tr.fecha_creacion.strftime('%Y-%m-%d %H:%M')
            ])

        table = Table(data, colWidths=[80, 80, 70, 130, 70, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(table)
        doc.build(elements)
        return response

class DetalleTransaccionViewSet(viewsets.ModelViewSet):
    serializer_class = DetalleTransaccionSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsVendedorOrAdmin(), HasPlanPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return DetalleTransaccion.objects.all()
        if user.rol == 'CLIENTE_FINAL':
            return DetalleTransaccion.objects.filter(transaccion__cliente=user)
        return DetalleTransaccion.objects.filter(transaccion__empresa=user.empresa)

class PagoViewSet(viewsets.ModelViewSet):
    """[Hito 6] CRUD de Pagos asociados a transacciones"""
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [IsVendedorOrAdmin, HasPlanPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['transaccion__numero_documento', 'metodo', 'referencia']
    ordering_fields = ['fecha_pago', 'monto']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Pago.objects.all()
        return Pago.objects.filter(transaccion__empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        # [Hito 7A] Vincular automáticamente el pago al turno de caja ABIERTO si existe
        turno = TurnoCaja.objects.filter(
            apertura_por__empresa=self.request.user.empresa,
            estado='ABIERTO'
        ).order_by('-fecha_apertura').first()
        serializer.save(turno_caja=turno)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by('-fecha_creacion')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser, HasPlanPermission]
    pagination_class = PaginacionEstandar
    filter_backends = [filters.SearchFilter]
    search_fields = ['accion', 'tabla_afectada', 'descripcion', 'usuario__username']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return AuditLog.objects.all()
        return AuditLog.objects.filter(usuario__empresa=self.request.user.empresa)
    ordering_fields = ['fecha_creacion']


# ─────────────────────────────────────────────
# HITO 7-A: ViewSets de Cierre de Caja
# ─────────────────────────────────────────────

class TurnoCajaViewSet(viewsets.ModelViewSet):
    """Gestión de turnos de trabajo y arqueo de caja"""
    queryset = TurnoCaja.objects.all()
    serializer_class = TurnoCajaSerializer
    permission_classes = [IsVendedorOrAdmin, HasPlanPermission]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return TurnoCaja.objects.all()
        return TurnoCaja.objects.filter(apertura_por__empresa=self.request.user.empresa)

    @action(detail=False, methods=['get'])
    def turno_activo(self, request):
        """Devuelve el turno ABIERTO actual de la empresa del usuario, si existe"""
        turno = TurnoCaja.objects.filter(
            apertura_por__empresa=request.user.empresa,
            estado='ABIERTO'
        ).order_by('-fecha_apertura').first()
        if not turno:
            return Response({'turno_activo': None})
        return Response(TurnoCajaSerializer(turno).data)

    @action(detail=False, methods=['post'])
    def abrir(self, request):
        """Abre un nuevo turno de caja para la empresa. Solo se permite uno abierto a la vez."""
        if TurnoCaja.objects.filter(apertura_por__empresa=request.user.empresa, estado='ABIERTO').exists():
            return Response({'error': 'Ya existe un turno abierto para su empresa.'}, status=400)
        monto_inicial = request.data.get('monto_inicial', 0)
        turno = TurnoCaja.objects.create(
            apertura_por=request.user,
            monto_inicial=monto_inicial
        )
        return Response(TurnoCajaSerializer(turno).data, status=201)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra el turno y calcula el arqueo comparando esperado vs declarado."""
        turno = self.get_object()
        if turno.estado == 'CERRADO':
            return Response({'error': 'Este turno ya está cerrado.'}, status=400)

        from django.db.models import Sum
        # Calcular efectivo esperado
        ventas_efectivo = float(
            turno.pagos_del_turno.filter(metodo='EFECTIVO').aggregate(t=Sum('monto'))['t'] or 0
        )
        ingresos = float(
            turno.movimientos.filter(tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
        )
        egresos = float(
            turno.movimientos.filter(tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
        )
        esperado = float(turno.monto_inicial) + ventas_efectivo + ingresos - egresos

        declarado = float(request.data.get('efectivo_declarado', 0))
        diferencia = declarado - esperado

        turno.estado = 'CERRADO'
        turno.fecha_cierre = timezone.now()
        turno.total_efectivo_esperado = esperado
        turno.total_efectivo_declarado = declarado
        turno.diferencia = diferencia
        turno.observaciones_cierre = request.data.get('observaciones', '')
        turno.save()

        return Response(TurnoCajaSerializer(turno).data)


class MovimientoCajaViewSet(viewsets.ModelViewSet):
    """Registra ingresos y egresos manuales dentro de un turno activo"""
    queryset = MovimientoCaja.objects.all().order_by('-fecha')
    serializer_class = MovimientoCajaSerializer
    permission_classes = [IsVendedorOrAdmin, HasPlanPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['motivo', 'tipo', 'turno__id']
    ordering_fields = ['fecha', 'monto']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return MovimientoCaja.objects.all()
        return MovimientoCaja.objects.filter(turno__apertura_por__empresa=self.request.user.empresa)