from django import get_version
from fields import AdvancedFileField
if get_version() < '1.2.5':
    raise Exception('Extended FileField require Django 1.2.5 or greater.')