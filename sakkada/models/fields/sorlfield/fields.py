# -*- encoding: utf-8 -*-
from django.db.models import signals
from sorl.thumbnail.fields import ImageWithThumbnailsField, ImageWithThumbnailsFieldFile
from sorl.thumbnail.utils import delete_thumbnails
from forms import DeleteImageFormField
from PIL import Image
import os

class AdvancedImageWithThumbnailsFieldFile(ImageWithThumbnailsFieldFile):
    def save(self, name, content, save=True):
        super(AdvancedImageWithThumbnailsFieldFile, self).save(name, content, save)
        resize(getattr(self.instance, self.field.name).path, self.field.max_width, self.field.max_height, self.field.max_quality)

    @property
    def extension(self):
        file = getattr(self.instance, self.field.name)
        return file and os.path.splitext(file.name)[1][1:]

class AdvancedImageWithThumbnailsField(ImageWithThumbnailsField):
    attr_class = AdvancedImageWithThumbnailsFieldFile

    def __init__(self, verbose_name=None, max_width=None, max_height=None, max_quality=None, clearable=False, **kwargs):
        super(AdvancedImageWithThumbnailsField, self).__init__(verbose_name=verbose_name, **kwargs)
        self.max_width, self.max_height, self.max_quality, self.clearable = max_width, max_height, max_quality, clearable

    def save_form_data(self, instance, data):
        """Overwrite save_form_data to delete images if "delete" checkbox is selected"""
        if data == '__deleted__' and self.blank:
            # delete file while "checkbox" delete if clearable
            file = getattr(instance, self.name)
            file.delete() if self.clearable else delete_thumbnails(file.path)
            setattr(instance, self.name, None)
        else:
            # delete old file while update if clearable, else delete only thumbnails
            if instance.pk and data:
                original = instance.__class__.objects.get(pk=instance.pk)
                original = getattr(original, self.name)
                if original and original != data:
                    original.delete() if self.clearable else delete_thumbnails(original.path)
            super(AdvancedImageWithThumbnailsField, self).save_form_data(instance, data)

    def formfield(self, **kwargs):
        kwargs['form_class'] = DeleteImageFormField
        kwargs['thumbnail'] = self.thumbnail
        kwargs['thumbnail_tag'] = self.thumbnail_tag
        return super(AdvancedImageWithThumbnailsField, self).formfield(**kwargs)

    def contribute_to_class(self, cls, name):
        super(AdvancedImageWithThumbnailsField, self).contribute_to_class(cls, name)
        signals.post_delete.connect(self.delete_file, sender=cls)

    def delete_file(self, instance, sender, **kwargs):
        file = getattr(instance, self.attname)
        if file and file.name != self.default:
            if self.clearable:
                sender._default_manager.filter(**{self.name: file.name}) or file.delete(save=False)
            else:
                delete_thumbnails(file.path)
        elif file:
            file.close()

def resize(file_path, max_width, max_height, max_quality=None):
    """
    Resize file (located on file path) to maximum dimensions proportionally.
    At least one of max_width and max_height must be not None.
    If source image in rect of max_width and max_height, no resize required.
    Value of max_quality (or 75 by default) is a quality of resized image (if jpeg).
    """
    if not (max_width or max_height):
        return
    img = Image.open(file_path)
    w, h = img.size
    if (not max_width or max_width >= w) and (not max_height or max_height >= h):
        return
    w = int(max_width or w)
    h = int(max_height or h)
    q = int(max_quality or 75)
    img.thumbnail((w, h), Image.ANTIALIAS)
    img.save(file_path, quality=q)