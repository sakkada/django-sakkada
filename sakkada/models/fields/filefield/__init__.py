from django import VERSION
from .fields import AdvancedFileField, AdvancedImageField

if VERSION < (1, 2, 5,):
    raise Exception('Extended FileField require Django 1.2.5 or greater.')
