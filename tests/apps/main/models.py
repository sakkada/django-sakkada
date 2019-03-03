from django.db import models
from sakkada.models.prev_next import PrevNextModel
from sakkada.models.fields.filefield import (AdvancedFileField,
                                             AdvancedImageField)
from sakkada.system import validators


FILES_UPLOAD_TO = {
    'filefieldmodel_file': 'main/filefieldmodel/file/',
    'filefieldmodel_image': 'main/filefieldmodel/image/',
}


class PrevNextTestModel(PrevNextModel):
    title = models.CharField('title', max_length=128)
    slug = models.SlugField('slug', max_length=128)
    weight = models.IntegerField('weight', default=500)
    nweight = models.IntegerField(
        'weight nullable', default=500, null=True, blank=True)

    class Meta:
        ordering = ('-weight',)

    def __str__(self):
        return '%s (%d: %s)' % (self.title, self.id, self.slug,)


class FileFieldModel(models.Model):
    file = AdvancedFileField(
        'file', blank=True, clearable=True, erasable=False,
        upload_to=FILES_UPLOAD_TO['filefieldmodel_file'],
        validators=[
            validators.ExtensionValidator(['.txt',]),
            validators.MimetypeValidator(['text/plain',]),
            validators.FilesizeValidator(max=1024),
        ]
    )

    image = AdvancedImageField(
        'image', blank=False, clearable=False, erasable=True,
        upload_to=FILES_UPLOAD_TO['filefieldmodel_image'],
        validators=[
            validators.MimetypeValidator(['image/png',]),
            validators.FilesizeValidator(max=1024*4),
        ]
    )

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return str(self.id)
