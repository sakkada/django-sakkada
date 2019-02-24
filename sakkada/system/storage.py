from threading import local


class Storage(object):
    """proxy to _thread_locals.storage object"""
    def __getattribute__(self, name):
        return _thread_locals.storage.get(name, None)

    def __setattr__(self, name, value):
        _thread_locals.storage[name] = value

    def __delattr__(self, name):
        if name in _thread_locals.storage:
            _thread_locals.storage.__delitem__(name)


class StorageMiddleware(object):
    """insert request, user, ect. variables into local storage"""
    def process_request(self, request):
        _thread_locals.storage = {}
        storage.request = request
        storage.user = getattr(request, 'user', None)


_thread_locals = local()
_thread_locals.storage = {}
storage = Storage()
