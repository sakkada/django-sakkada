from django.forms import ValidationError
from django.forms.fields import ImageField
from django.utils.translation import ugettext as _
from django.template.defaultfilters import filesizeformat
from widgets import ClearableImageWidget
import os

class ClearableFormImageField(ImageField):
    def __init__(self, *args, **kwargs):
        self.min_size = kwargs.pop('min_size', None)
        self.max_size = kwargs.pop('max_size', None)
        self.mimetypes = kwargs.pop('mimetypes', None)
        widget = kwargs.get('widget', None)
        widget = widget if isinstance(widget, type) and issubclass(widget, ClearableImageWidget) else ClearableImageWidget
        widget = widget(show_delete_checkbox=not kwargs.get("required", True),)
        kwargs["widget"] = widget
        super(ClearableFormImageField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        data = super(ClearableFormImageField, self).to_python(data)
        extension = os.path.splitext(data.name)[1].lower()

        if self.mimetypes and data.content_type not in self.mimetypes:
            raise ValidationError(_('Filetype %(curr)s not allowed. Available types - %(list)s.') % {'curr': data.content_type, 'list': str(', '.join(self.mimetypes))})
        if self.min_size and data._size < self.min_size:
            raise ValidationError(_('Please keep filesize above %(min)s. Current filesize %(real)s') % {'min': filesizeformat(self.min_size), 'real': filesizeformat(data._size)})
        if self.max_size and data._size > self.max_size:
            raise ValidationError(_('Please keep filesize under %(max)s. Current filesize %(real)s') % {'max': filesizeformat(self.max_size), 'real': filesizeformat(data._size)})

        return data

    def clean(self, data, initial=None):
        return '__deleted__' if data == '__deleted__' else super(ClearableFormImageField, self).clean(data, initial)