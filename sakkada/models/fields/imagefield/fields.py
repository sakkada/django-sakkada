from django.db.models.fields.files import ImageField, ImageFieldFile
from forms import ClearableFormImageField

class AdvancedImageFieldFile(ImageFieldFile):
    @property
    def extension(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(file.name)[1][1:]

class AdvancedImageField(ImageField):
    attr_class = AdvancedImageFieldFile

    def __init__(self, verbose_name=None, min_size=None, max_size=None, mimetypes=None, clearable=False, **kwargs):
        super(AdvancedImageField, self).__init__(verbose_name=verbose_name, **kwargs)
        self.min_size, self.max_size, self.mimetypes, self.clearable = min_size, max_size, mimetypes, clearable

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
            super(AdvancedImageField, self).save_form_data(instance, data)

    def formfield(self, **kwargs):
        kwargs['form_class'] = ClearableFormImageField
        for i in ['min_size', 'max_size', 'mimetypes']:
            kwargs[i] = getattr(self, i, None)
        return super(AdvancedImageField, self).formfield(**kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.ImageField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)