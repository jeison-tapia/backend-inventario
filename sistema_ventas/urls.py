from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from inventario.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', RedirectView.as_view(url='api/docs/', permanent=False)), # Redirige raíz a la documentación
    path('admin/', admin.site.urls),
    path('api/', include('inventario.urls')), # <-- Agrega 'api/' aquí
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Documentación interactiva Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]