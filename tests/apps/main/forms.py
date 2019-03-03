from django import forms
from . import models


class FileFieldModelForm(forms.ModelForm):
    class Meta:
        model = models.FileFieldModel
        fields = '__all__'
