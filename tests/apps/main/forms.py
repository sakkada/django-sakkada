from django import forms
from sakkada.models.fields.multivalue import CharMultipleValuesFormField
from . import models


# File Fields
class FileFieldModelForm(forms.ModelForm):
    class Meta:
        model = models.FileFieldModel
        fields = '__all__'


# Multiple Values Fields
class ExtendedCharMultipleValuesFormField(CharMultipleValuesFormField):
    delimiter = ';'


class MultiValueFieldModelForm(forms.ModelForm):
    class Meta:
        model = models.MultiValueFieldModel
        fields = '__all__'
        field_classes = {
            'cfield_with_extended_form_field': ExtendedCharMultipleValuesFormField,
        }
        widgets = {
            'cfield_integer_with_choices_checkboxes': forms.CheckboxSelectMultiple,
        }
