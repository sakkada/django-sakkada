# -*- coding: utf-8 -*-
from django.forms.widgets import Media
from django.contrib import admin
from django.conf import settings


class EditorAdmin(admin.ModelAdmin):
    tinymce_fields = {}
    tinymce_setup = None
    tinymce_static_url = 'tiny_mce'

    @property
    def media(self):
        setup = '.%s' % self.tinymce_setup if self.tinymce_setup else ''
        setup = 'admin/tinymce/setup/activater%s.js' % setup

        js = '' if settings.DEBUG else '.min'
        js = (
            'admin/js/vendor/jquery/jquery%s.js' % js,
            'admin/js/jquery.init.js',
            'admin/js/cookies.js',
            '%s/tiny_mce.js' % self.tinymce_static_url.rstrip('/'),
            setup,
        )
        css = {'all': ('admin/tinymce/setup/activater.css',),}

        base = getattr(super(EditorAdmin, self), 'media', Media())
        return base + Media(js=js, css=css)

    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        if hasattr(self, 'tinymce_fields') and self.tinymce_fields:
            for name in self.tinymce_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] = ('%s %s' % (
                    f.widget.attrs.get('class', ''), 'editor_tinymce'
                )).strip()
        return form
