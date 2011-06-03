from django.forms import ValidationError
from django.forms.fields import FileField
from django.utils.translation import ugettext as _
from django.template.defaultfilters import filesizeformat
from widgets import ClearableFileWidget
import os

class ClearableFormFileField(FileField):
    def __init__(self, *args, **kwargs):
        self.min_size = kwargs.pop('min_size', None)
        self.max_size = kwargs.pop('max_size', None)
        self.extensions = kwargs.pop('extensions', None)
        self.mimetypes = kwargs.pop('mimetypes', None)
        widget = kwargs.get('widget', None)
        widget = widget if isinstance(widget, type) and issubclass(widget, ClearableFileWidget) else ClearableFileWidget
        widget = widget(show_delete_checkbox=not kwargs.get("required", True),)
        kwargs["widget"] = widget
        super(ClearableFormFileField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        data = super(ClearableFormFileField, self).to_python(data)
        extension = os.path.splitext(data.name)[1].lower()

        if self.mimetypes and data.content_type not in self.mimetypes:
            raise ValidationError(_('Filetype %(curr)s not allowed. Available types - %(list)s.') % {'curr': data.content_type, 'list': str(', '.join(self.mimetypes))})
        if self.extensions and extension not in self.extensions:
            raise ValidationError(_('Files with extension %(curr)s not allowed. Available extensions - %(list)s.') % {'curr': extension, 'list': str(', '.join(self.extensions))})
        if self.max_size and data._size > self.max_size:
            raise ValidationError(_('Please keep filesize under %(max)s. Current filesize %(real)s') % {'max': filesizeformat(self.max_size), 'real': filesizeformat(data._size)})
        if self.min_size and data._size < self.min_size:
            raise ValidationError(_('Please keep filesize above %(min)s. Current filesize %(real)s') % {'min': filesizeformat(self.min_size), 'real': filesizeformat(data._size)})

        return data

    def clean(self, data, initial=None):
        return '__deleted__' if data == '__deleted__' else super(ClearableFormFileField, self).clean(data, initial)