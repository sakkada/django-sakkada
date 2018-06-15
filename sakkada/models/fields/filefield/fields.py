import os
from django.utils.safestring import mark_safe
from django.db.models import signals
from django.db.models.fields.files import (FieldFile, ImageFieldFile,
                                           FileField, ImageField)
from .forms import ClearableFormFileField, ClearableFormImageField


# field files
class AdvancedFieldFile(FieldFile):
    @property
    def extension(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(file.name)[1]

    @property
    def basename(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.basename(self.file.name)

    @property
    def basename_splitext(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(os.path.basename(self.file.name))


class AdvancedImageFieldFile(AdvancedFieldFile, ImageFieldFile):
    @property
    def image_tag(self):
        return mark_safe(u'<img src="%s" alt="%s" width="%s" height="%s">'
                         % (self.url, self.name, self.width, self.height))


# file fields
class AdvancedFileField(FileField):
    attr_class = AdvancedFieldFile

    def __init__(self, verbose_name=None, clearable=False, erasable=False,
                 **kwargs):
        super(AdvancedFileField, self).__init__(verbose_name=verbose_name,
                                                **kwargs)
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
        if data == '__delete__' and self.blank and self.clearable:
            self.__pre_save_action__ = '__delete__'
        else:
            self.__pre_save_action__ = '__erase_previous__'
            super(AdvancedFileField, self).save_form_data(instance, data)

    def pre_save(self, instance, add):
        file = getattr(instance, self.name)
        action = getattr(self, '__pre_save_action__', '__erase_previous__')
        if action == '__delete__':
            # delete file if delete checkbox is checked
            self._safe_erase(file, instance, save=False)
            setattr(instance, self.name, None)
        elif action == '__erase_previous__' and not add and file:
            # erase old file before update if field is erasable
            orig = instance.__class__.objects.filter(pk=instance.pk).first()
            orig = getattr(orig, self.name, None)
            orig and orig != file and self._safe_erase(orig, instance,
                                                       save=False)

        return super(AdvancedFileField, self).pre_save(instance, add)

    # erasable deletion
    def contribute_to_class(self, cls, name):
        super(AdvancedFileField, self).contribute_to_class(cls, name)
        signals.post_delete.connect(self.post_delete, sender=cls)

    def post_delete(self, instance, sender, **kwargs):
        file = getattr(instance, self.attname)
        self._safe_erase(file, instance, save=False)

    def _safe_erase(self, file, instance, save=True):
        # safe file storage real erase
        if not file:
            return
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

    def __init__(self, verbose_name=None, show_image=True, **kwargs):
        super(AdvancedImageField, self).__init__(verbose_name=verbose_name,
                                                 **kwargs)
        self.show_image = show_image

    def formfield(self, **kwargs):
        kwargs['form_class'] = ClearableFormImageField
        kwargs['clearable'] = self.clearable
        kwargs['show_image'] = self.show_image
        return super(AdvancedFileField, self).formfield(**kwargs)

    def south_field_triple(self):
        """Return a suitable description of this field for South."""
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.ImageField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
