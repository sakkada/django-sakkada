from django.db.models.fields.files import FileField, FieldFile
from forms import ClearableFormFileField
import os

class AdvancedFieldFile(FieldFile):
    @property
    def extension(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(file.name)[1][1:]

class AdvancedFileField(FileField):
    attr_class = AdvancedFieldFile

    def __init__(self, verbose_name=None, max_size=None, min_size=None, extensions=None, mimetypes=None, clearable=False, **kwargs):
        super(AdvancedFileField, self).__init__(verbose_name=verbose_name, **kwargs)
        self.max_size, self.min_size, self.extensions, self.mimetypes, self.clearable = max_size, min_size, extensions, mimetypes, clearable

    def save_form_data(self, instance, data):
        """Overwrite save_form_data to delete file if "delete" checkbox is selected"""
        if data == '__deleted__' and self.blank:
            # delete file while "checkbox" delete if clearable
            self.clearable and getattr(instance, self.name).delete()
            setattr(instance, self.name, None)
        else:
            # delete old file while update if clearable
            if instance.pk and data:
                original = instance.__class__.objects.get(pk=instance.pk)
                original = getattr(original, self.name)
                original and original != data and self.clearable and original.delete()
            super(AdvancedFileField, self).save_form_data(instance, data)

    def formfield(self, **kwargs):
        kwargs['form_class'] = ClearableFormFileField
        for i in ['max_size', 'min_size', 'extensions', 'mimetypes']:
            kwargs[i] = getattr(self, i, None)
        return super(AdvancedFileField, self).formfield(**kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.FileField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)