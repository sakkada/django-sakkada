from django.db.models import signals
from django.db.models.fields.files import FieldFile, ImageFieldFile, \
                                          FileField, ImageField
from forms import ClearableFormFileField, ClearableFormImageField
import os

# field files
class AdvancedFieldFile(FieldFile):
    @property
    def extension(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(file.name)[1]

class AdvancedImageFieldFile(AdvancedFieldFile, ImageFieldFile):
    pass

# file fields
class AdvancedFileField(FileField):
    attr_class = AdvancedFieldFile

    def __init__(self, verbose_name=None, clearable=False, erasable=False, **kwargs):
        super(AdvancedFileField, self).__init__(verbose_name=verbose_name, **kwargs)
        self.clearable, self.erasable = clearable, erasable

        if not self.blank and self.clearable:
            raise ValueError('Non blank FileField can not be clearable.')

    def formfield(self, **kwargs):
        kwargs['form_class'] = ClearableFormFileField
        kwargs['clearable'] = self.clearable
        return super(AdvancedFileField, self).formfield(**kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.FileField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)

    def save_form_data(self, instance, data):
        """overwrite to delete file if "delete" checkbox is checked"""
        if data == '__delete__' and self.blank and self.clearable:
            # delete file while delete checkbox checked
            file = getattr(instance, self.name)
            self._safe_erase(file, instance)
            setattr(instance, self.name, None)
        else:
            # erase old file before update if field is erasable
            if instance.pk and data:
                file = instance.__class__.objects.get(pk=instance.pk)
                file = getattr(file, self.name)
                file and file != data and self._safe_erase(file, instance)
            super(AdvancedFileField, self).save_form_data(instance, data)

    # erasable deletion
    def contribute_to_class(self, cls, name):
        super(AdvancedFileField, self).contribute_to_class(cls, name)
        signals.post_delete.connect(self.post_delete, sender=cls)

    def post_delete(self, instance, sender, **kwargs):
        file = getattr(instance, self.attname)
        self._safe_erase(file, instance, save=False)

    def _safe_erase(self, file, instance, save=True):
        # safe file storage real erase
        if not file: return
        count = instance.__class__._default_manager
        count = count.filter(**{self.name: file.name,}) \
                     .exclude(pk=instance.pk).count()

        # if no other object of this type references the file
        # and it's not the default value for future objects,
        # delete it from the backend
        not count and file.name != self.default and self.erasable \
                  and file.delete(save=save)

        # try to close the file, so it doesn't tie up resources.
        file.closed or file.close()

class AdvancedImageField(AdvancedFileField, ImageField):
    attr_class = AdvancedImageFieldFile

    def formfield(self, **kwargs):
        kwargs['form_class'] = ClearableFormImageField
        kwargs['clearable'] = self.clearable
        return super(AdvancedFileField, self).formfield(**kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.ImageField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)