# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.templatetags.admin_static import static
from django.forms.widgets import Media

__all__ = ('EditorAdmin',)


class EditorAdmin(admin.ModelAdmin):
    @property
    def media(self):
        # media as a propery, because if this module used as an app,
        # call of function "static" in __init__.py (class Media definition)
        # cause an "django.core.AppRegistryNotReady: Apps aren't loaded yet".

        js = '' if settings.DEBUG else '.min'
        js = (
            static('admin/js/jquery%s.js' % js),
            static('admin/js/jquery.init.js'),
            static('admin/simple_fb/activater.js'),
        )
        css = {'all': (static('admin/simple_fb/activater.css'),),}

        base = getattr(super(EditorAdmin, self), 'media', Media())
        return base + Media(js=js, css=css)

    simple_fb_fields = {}

    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        if hasattr(self, 'simple_fb_fields') and self.simple_fb_fields:
            for name in self.simple_fb_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] += (' ' if f.widget.attrs['class']
                                            else '') + 'editor_simple_fb'
        return form
