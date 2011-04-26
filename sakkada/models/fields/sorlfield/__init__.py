from django import get_version
from fields import AdvancedImageWithThumbnailsField
if get_version() < '1.2.5':
    raise Exception('Extended Sorl ImageField require Django 1.2.5 or greater.')