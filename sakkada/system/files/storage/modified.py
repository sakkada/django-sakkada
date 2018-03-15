import os
from django.core.exceptions import ImproperlyConfigured
from .unique import UniqueNameFileSystemStorage


class ModifierProcessedNameFileSystemStorage(UniqueNameFileSystemStorage):
    """
    Processed by defined modifiers or custom modify methods filename and
    extension. Requires unidecode for transliteration modifier.
    """
    modifiers = None
    modifiers_extension = None
    overwrite_existing = False

    def __init__(self, modifiers=None, modifiers_extension=None,
                 *args, **kwargs):
        super(ModifierProcessedNameFileSystemStorage,
              self).__init__(*args, **kwargs)
        self.modifiers = modifiers
        self.modifiers_extension = modifiers_extension
        self.check()

    def check(self):
        error = None
        if self.modifiers and 'transliteration' in self.modifiers:
            try:
                import unidecode
                self._unidecode_transliteration = unidecode.unidecode
            except ImportError:
                error = 'storage requires "unidecode" module to be installed'
        if self.modifiers or self.modifiers_extension and not error:
            mods = (self.modifiers or []) + (self.modifiers_extension or [])
            for i in mods:
                if not (hasattr(self, '%s_modifier' % i) or hasattr(str, i)):
                    error = 'modifier "%s" does not exists or unsupported' % i
                    break
        if error:
            raise ImproperlyConfigured('Modifier Storage: %s.' % error)

    def get_unique_available_name(self, name, max_length=None,
                                  content=None, chunk_size=None):
        dirname, basename = os.path.split(name)
        rootname, extension = os.path.splitext(basename)
        basename = u''.join((
            self.handle_rootname(dirname, rootname, extension),
            self.handle_extension(dirname, rootname, extension),))
        name = os.path.join(dirname, basename)
        return super(ModifierProcessedNameFileSystemStorage,
                     self).get_unique_available_name(
            name, max_length=max_length,
            content=content, chunk_size=chunk_size)

    def handle_rootname(self, dirname, rootname, extension):
        if self.modifiers:
            rootname = self.run_modifiers(self.modifiers, rootname)
        return self.modify_rootname(dirname, rootname, extension)

    def handle_extension(self, dirname, rootname, extension):
        if self.modifiers_extension:
            extension = self.run_modifiers(self.modifiers_extension, extension)
        return self.modify_extension(dirname, rootname, extension)

    def run_modifiers(self, modifiers, value):
        for i in modifiers:
            i, args, kwargs = ((tuple(i) + (None, None,))[:3]
                               if isinstance(i, (list, tuple)) else
                               (i, None, None,))
            args, kwargs = args or tuple(), kwargs or {}
            value = (getattr(self, '%s_modifier' % i)(value, *args, **kwargs)
                     if hasattr(self, '%s_modifier' % i) else
                     getattr(value, i)(*args, **kwargs))
        return value

    # custom modify methods section
    def modify_rootname(self, dirname, rootname, extension):
        return rootname

    def modify_extension(self, dirname, rootname, extension):
        return extension

    # modifiers section
    def transliteration_modifier(self, value):
        return self._unidecode_transliteration(value)
