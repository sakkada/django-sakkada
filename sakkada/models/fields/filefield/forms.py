from django.forms.fields import FileField, ImageField
from .widgets import ClearableFileInput, ClearableImageFileInput


class ClearableFormFileField(FileField):
    default_widget = ClearableFileInput

    def __init__(self, *args, **kwargs):
        self.clearable = kwargs.pop('clearable', None)

        widget = kwargs.get('widget', None)
        widget = (isinstance(widget, type) and
                  issubclass(widget, ClearableFileInput) and
                  widget or self.default_widget)
        kwargs["widget"] = widget(
            show_delete_checkbox=self.clearable and not kwargs.get(
                "required", True)
        )

        super(ClearableFormFileField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        return (data if data == '__delete__' else
                super(ClearableFormFileField, self).clean(data, initial))


class ClearableFormImageField(ClearableFormFileField, ImageField):
    default_widget = ClearableImageFileInput

    def __init__(self, *args, **kwargs):
        self.clearable = kwargs.pop('clearable', None)
        self.show_image = kwargs.pop('show_image', None)

        widget = kwargs.get('widget', None)
        widget = (isinstance(widget, type) and
                  issubclass(widget, ClearableFileInput) and
                  widget or self.default_widget)

        kwargs["widget"] = widget(
            show_image=self.show_image,
            show_delete_checkbox=self.clearable and not kwargs.get(
                "required", True)
        )

        super(ImageField, self).__init__(*args, **kwargs)
