# -*- coding: utf-8 -*-
from django.contrib import admin
from django.conf import settings

class EditorAdmin(admin.ModelAdmin):
    @property
    def media(self):
        setup = '.%s' % self.wymeditor_setup if self.wymeditor_setup else ''
        setup = 'admin/wymeditor/setup/activater%s.js' % setup

        js = [
            settings.STATIC_URL + 'admin/js/jquery.min.js',
            settings.STATIC_URL + 'admin/js/jquery.init.js',
            settings.STATIC_URL + 'admin/jquery/init.js',
            settings.STATIC_URL + 'admin/jquery/jquery.cookie.js',
            settings.STATIC_URL + 'admin/wymeditor/jquery.wymeditor.pack.js',
            settings.STATIC_URL + setup,
        ]
        css = {'all': [settings.STATIC_URL + 'admin/wymeditor/setup/activater.css',]}

        media = getattr(super(EditorAdmin, self), 'media', None) or Media()
        media.add_js(js)
        media.add_css(css)
        return media

    wymeditor_fields = {}
    wymeditor_setup = None

    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        # set some css classes
        self.wymeditor_set(form)
        return form

    # css proxy classes set
    def wymeditor_set(self, form):
        if hasattr(self, 'wymeditor_fields') and self.wymeditor_fields:
            for name in self.wymeditor_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] = ' '.join(([f.widget.attrs['class'].strip()] if f.widget.attrs.has_key('class') else []) + ['editor_wymeditor'])