from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Categoria, Producto, Transaccion, DetalleTransaccion, Plan, EmpresaCliente

# Registramos nuestros modelos para que aparezcan en el panel web
admin.site.register(Plan)
admin.site.register(EmpresaCliente)
admin.site.register(Usuario, UserAdmin)
admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(Transaccion)
admin.site.register(DetalleTransaccion)