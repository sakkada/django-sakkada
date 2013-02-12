from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.template.defaultfilters import filesizeformat
import os

# validators decorators
def filesize(min=None, max=None):
    if not min and not max:
        raise ValueError(u'There is not any size value specified for check (min and/or max).')

    return lambda value: filesize_validator(value, min=min, max=max)

def mimetype(mimetypes):
    if not mimetypes:
        raise ValueError(u'There is not any allowed mimetypes for check.')

    return lambda value: mimetype_validator(value, mimetypes)

def extension(extensions):
    if not extensions:
        raise ValueError(u'There is not any allowed extensions for check.')

    return lambda value: extension_validator(value, extensions)

# parameterized validators
def mimetype_validator(value, mimetypes):
    # content_type attr exist only in just uploaded file
    if not isuploaded(value): return

    mimetype = getattr(value.file, 'content_type', None)
    if mimetype and mimetype not in mimetypes:
        raise ValidationError(_('Filetype "%(curr)s" is not allowed. Available types - [%(list)s].') \
                              % {'curr': mimetype, 'list': str(', '.join(mimetypes))})

def extension_validator(value, extensions):
    if not isuploaded(value): return

    extension = os.path.splitext(value.name)[1].lower()
    if extension not in extensions:
        raise ValidationError(_('Files with extension "%(curr)s" is not allowed. Available extensions - [%(list)s].') \
                              % {'curr': extension, 'list': str(', '.join(extensions))})

def filesize_validator(value, min=None, max=None):
    if not isuploaded(value): return

    if max is not None and value.file._size > max:
        raise ValidationError(_('Please keep filesize under %(max)s. Current filesize is %(real)s') \
                              % {'max': filesizeformat(max), 'real': filesizeformat(value.file._size)})
    if min is not None and value.file._size < min:
        raise ValidationError(_('Please keep filesize above %(min)s. Current filesize is %(real)s') \
                              % {'min': filesizeformat(min), 'real': filesizeformat(value.file._size)})

# utils
def isuploaded(value):
    # note: check for _file first, because UploadedFile must be already cached
    # just uploaded file should be UploadedFile instance with _size and
    # content_type attributes
    return getattr(value, '_file', False) and isinstance(value._file, UploadedFile)