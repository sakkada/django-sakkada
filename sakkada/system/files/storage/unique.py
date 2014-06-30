"""
Forked from https://github.com/ecometrica/django-hashedfilenamestorage
Changes:
    - Storage defined as a usual class directly
    - Added uniquify_names argument to control filename generation behaviour
    - Added overwrite_existing argument to control file overwriting behaviour
"""
from errno import EEXIST

from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import force_text


class NoAvailableName(Exception):
    pass


class UniqueNameFileSystemStorage(FileSystemStorage):
    """
    UniqueNameFileSystemStorage allows to control filename
    generating behaviour: allow filenames uniqueness (generate
    new random name if previous exists) or generate static
    filename related to uploaded file name or/and content.
    There is also overwrite_existing option, that allows to
    prevent overwriting already existing file.
    """
    uniquify_names = True
    overwrite_existing = True

    def __init__(self, uniquify_names=None,
                       overwrite_existing=None, *args, **kwargs):
        if uniquify_names is not None:
            self.uniquify_names = uniquify_names
        if overwrite_existing is not None:
            self.overwrite_existing = overwrite_existing

        super(UniqueNameFileSystemStorage, self).__init__(*args, **kwargs)

    def get_available_name(self, name):
        # Execute only in _save method for regenerate filename
        # so raise NoAvailableName if not uniquify_names
        if not self.uniquify_names:
            raise NoAvailableName(name)

        return self.get_unique_available_name(name)

    def get_unique_available_name(self, name, content=None):
        # Real method to generate new filename, it may be overwritten
        if self.uniquify_names:
            name = super(UniqueNameFileSystemStorage,
                         self).get_available_name(name)
        return name

    def check_not_overwrite_existing(self, name, content):
        # Checking to disallow writing file in _save
        return (not self.uniquify_names and not self.overwrite_existing
                and self.exists(name))

    def save(self, name, content):
        # Default behaviour except calling get_unique_available_name
        # instead get_available_name and pass content argument
        if name is None:
            name = content.name

        if not hasattr(content, 'chunks'):
            content = File(content)

        name = self.get_unique_available_name(name, content=content)
        name = self._save(name, content)

        # Store filenames with forward slashes, even on Windows
        return force_text(name.replace('\\', '/'))

    def _save(self, name, content):
        # Save original file without changes if required
        if self.check_not_overwrite_existing(name, content):
            return name

        try:
            return super(UniqueNameFileSystemStorage,
                         self)._save(name, content)
        except NoAvailableName:
            # File already exists, so we can safely do nothing
            # because their contents match. Raises if uniquify_names is False.
            pass

        return name
