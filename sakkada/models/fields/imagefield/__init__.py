from django import get_version
from fields import AdvancedImageField
if get_version() < '1.2.5':
    raise Exception('Extended ImageField require Django 1.2.5 or greater.')