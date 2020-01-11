from django.db import models
from sakkada.models.prev_next import PrevNextModel
from sakkada.models.fields.filefield import (
    AdvancedFileField, AdvancedImageField)
from sakkada.models.fields.multivalue import (
    CharMultipleValuesField, TextMultipleValuesField, MultipleValuesModelMixin)
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
        ordering = ['-weight',]

    def __str__(self):
        return '%s (%d: %s)' % (self.title, self.id, self.slug,)


class PrevNextNoOrderingTestModel(PrevNextTestModel):
    class Meta:
        proxy = True
        ordering = []


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


class MultiValueFieldModel(MultipleValuesModelMixin, models.Model):
    char_default = CharMultipleValuesField(max_length=1024)
    text_default = TextMultipleValuesField(max_length=1024)

    comma_separated = CharMultipleValuesField(
        max_length=1024, default=['a', 'b', 'c',])
    slash_separated = CharMultipleValuesField(
        max_length=1024, delimiter='/', default=['a', 'b', 'c',])
    newline_separated = TextMultipleValuesField(default=['a', 'b', 'c',])

    cfield_blank = CharMultipleValuesField(max_length=1024, blank=True)
    cfield_non_editable = CharMultipleValuesField(
        max_length=1024, blank=True, editable=False)
    cfield_with_extended_form_field = CharMultipleValuesField(max_length=1024)

    cfield_integer = CharMultipleValuesField(max_length=1024, coerce=int)
    cfield_integer_with_default = CharMultipleValuesField(
        max_length=1024, coerce=int, default=[1, 2, 3,])

    # fields with choices
    cfield_float_with_choices_and_default = CharMultipleValuesField(
        max_length=1024, coerce=float, delimiter='|', default=[1.0, 2.0,],
        choices=((1.0, 'One',), (1.5, 'One and half',), (2.0, 'Two',),))
    cfield_integer_with_choices_checkboxes = CharMultipleValuesField(
        max_length=1024, coerce=int, delimiter=':', default=[1, 2,],
        choices=((1, 'One',), (2, 'Two',), (3, 'Three',),))
    cfield_integer_with_grouped_choices = CharMultipleValuesField(
        max_length=1024, coerce=int, default=[1, 22,],
        choices=(('one', ((1, 'One',), (11, 'Eleven',),),),
                 ('two', ((2, 'Two',), (22, 'Twenty two',),),),))
    tfield_integer_with_choices = TextMultipleValuesField(
        max_length=1024, coerce=int, default=[1, 2,],
        choices=((1, 'One',), (2, 'Two',), (3, 'Three',),))

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return str(self.id)
