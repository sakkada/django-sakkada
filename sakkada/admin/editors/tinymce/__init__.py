# -*- coding: utf-8 -*-
from django.forms.widgets import Media
from django.contrib.admin.templatetags.admin_static import static
from django.contrib import admin
from django.conf import settings


class EditorAdmin(admin.ModelAdmin):
    tinymce_fields = {}
    tinymce_setup = None
    tinymce_static_url = 'tiny_mce'

    @property
    def media(self):
        # media as a propery, because if this module used as an app,
        # call of function "static" in __init__.py (class Media definition)
        # cause an "django.core.AppRegistryNotReady: Apps aren't loaded yet".

        setup = '.%s' % self.tinymce_setup if self.tinymce_setup else ''
        setup = 'admin/tinymce/setup/activater%s.js' % setup

        js = '' if settings.DEBUG else '.min'
        js = (
            static('admin/js/jquery%s.js' % js),
            static('admin/js/jquery.init.js'),
            static('admin/js/cookies.js'),
            static('%s/tiny_mce.js' % self.tinymce_static_url.rstrip('/')),
            static(setup),
        )
        css = {'all': (static('admin/tinymce/setup/activater.css'),),}

        base = getattr(super(EditorAdmin, self), 'media', Media())
        return base + Media(js=js, css=css)

    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        if hasattr(self, 'tinymce_fields') and self.tinymce_fields:
            for name in self.tinymce_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] += (' ' if f.widget.attrs['class']
                                            else '') + 'editor_tinymce'
        return form
