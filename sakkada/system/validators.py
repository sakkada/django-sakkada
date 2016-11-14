import os
from django.utils.translation import ugettext_lazy as _
from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile
from django.core.files.uploadedfile import UploadedFile
from django.template.defaultfilters import filesizeformat


def isuploaded(value):
    # note: value may be FieldFile or UploadedFile (model field or form field
    #       validation respectively), if FieldFile - get _file attr as value
    if isinstance(value, FieldFile):
        value = getattr(value, '_file', None)
    return isinstance(value, UploadedFile)


class BaseValidator(object):
    code = None

    def __call__(self, value):
        raise NotImplementedError

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.code == other.code


@deconstructible
class FilesizeValidator(BaseValidator):
    code = 'filesize_validator'

    def __init__(self, min=None, max=None):
        if not min and not max:
            raise ValueError(u'There is not any size value specified'
                             u' for check (min and/or max).')
        self.min, self.max = min, max

    def __call__(self, value):
        if not isuploaded(value):
            return
        if self.max is not None and value.file._size > self.max:
            raise ValidationError(
                _('Please keep filesize under %(max)s. Current filesize is %(real)s')
                % {'max': filesizeformat(self.max),
                   'real': filesizeformat(value.file._size),},
                code=self.code
            )
        if self.min is not None and value.file._size < self.min:
            raise ValidationError(
                _('Please keep filesize above %(min)s. Current filesize is %(real)s')
                % {'min': filesizeformat(self.min),
                   'real': filesizeformat(value.file._size),},
                code=self.code
            )


@deconstructible
class MimetypeValidator(BaseValidator):
    code = 'mimetype_validator'

    def __init__(self, mimetypes=None):
        if not mimetypes:
            raise ValueError(u'There is not any allowed mimetypes for check.')
        self.mimetypes = mimetypes

    def __call__(self, value):
        if not isuploaded(value):
            return
        mimetype = getattr(value.file, 'content_type', None)
        if mimetype and mimetype not in self.mimetypes:
            raise ValidationError(
                _('Filetype "%(curr)s" is not allowed. Available types - [%(list)s].')
                % {'curr': mimetype, 'list': str(', '.join(self.mimetypes))},
                code=self.code
            )


@deconstructible
class ExtensionValidator(BaseValidator):
    code = 'extension_validator'

    def __init__(self, extensions=None):
        if not extensions:
            raise ValueError(u'There is not any allowed extensions for check.')
        self.extensions = extensions

    def __call__(self, value):
        if not isuploaded(value):
            return
        extension = os.path.splitext(value.name)[1].lower()
        if extension not in self.extensions:
            raise ValidationError(
                _('Files with extension "%(curr)s" is not allowed.'
                  ' Available extensions - [%(list)s].')
                % {'curr': extension, 'list': str(', '.join(self.extensions))},
                code=self.code
            )
