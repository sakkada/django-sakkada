# -*- coding: utf-8 -*-
from django.conf import settings
from django.forms.widgets import Media, Widget, TextInput, Textarea


__all__ = ('SimpleFBWidget', 'SimpleFBInput', 'SimpleFBTextarea',)


class SimpleFBWidget(Widget):
    @property
    def media(self):
        js = '' if settings.DEBUG else '.min'
        js = (
            'admin/js/vendor/jquery/jquery%s.js' % js,
            'admin/js/jquery.init.js',
            'admin/js/vendor/jquery/jquery.resizable-field.js',
            'admin/simplefb/simple_fb_editor.js',
        )
        css = {'all': ('admin/simplefb/simple_fb_editor.css',),}
        base = getattr(super(SimpleFBWidget, self), 'media', Media())
        return base + Media(js=js, css=css)

    def __init__(self, attrs=None):
        if not attrs:
            attrs = {}
        cls = ' '.join([attrs.get('class', ''), 'editor_simple_fb']).strip()
        attrs.update({'class': cls,})
        return super(SimpleFBWidget, self).__init__(attrs=attrs)


class SimpleFBInput(TextInput, SimpleFBWidget):
    pass


class SimpleFBTextarea(Textarea, SimpleFBWidget):
    pass
