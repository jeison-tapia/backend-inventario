import threading

_thread_locals = threading.local()

def get_current_user():
    """Retorna el usuario de la petición actual, o None."""
    request = getattr(_thread_locals, 'request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None

class AuditMiddleware:
    """Extrae el request y lo almacena en el hilo local para uso por los signals de Auditoría."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response
