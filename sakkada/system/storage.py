try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

class Storage(object):
    """proxy to _thread_locals.storage object"""
    def __getattribute__(self, name):
        return _thread_locals.storage[name] if _thread_locals.storage.has_key(name) else None
    def __setattr__(self, name, value):
        _thread_locals.storage[name] = value
    def __delattr__(self, name):
        if _thread_locals.storage.has_key(name): del(_thread_locals.storage[name])

class StorageMiddleware(object):
    """insert request, user, ect. variables into local storage"""
    def process_request(self, request):
        _thread_locals.storage = {}
        storage.request     = request
        storage.user        = getattr(request, 'user', None)

_thread_locals = local()
_thread_locals.storage = {}
storage = Storage()