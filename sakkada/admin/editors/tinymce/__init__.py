# -*- coding: utf-8 -*-
from django.forms.widgets import Media
from django.contrib.admin.templatetags.admin_static import static
from django.contrib import admin
from django.conf import settings


class EditorAdmin(admin.ModelAdmin):
    @property
    def media(self):
        setup = '.%s' % self.tinymce_setup if self.tinymce_setup else ''
        setup = 'admin/tinymce/setup/activater%s.js' % setup

        js = '' if settings.DEBUG else '.min'
        js = (
            static('admin/js/jquery%s.js' % js),
            static('admin/js/jquery.init.js'),
            static('admin/jquery/init.js'),
            static('admin/jquery/jquery.cookie.js'),
            static('admin/tinymce/jscripts/tiny_mce/tiny_mce.js'),
            static(setup),
        )
        css = {'all': (static('admin/tinymce/setup/activater.css'),),}

        media = getattr(super(EditorAdmin, self), 'media', None) or Media()
        media.add_js(js)
        media.add_css(css)
        return media

    tinymce_fields = {}
    tinymce_setup = None

    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        # set some css classes
        self.tinymce_set(form)
        return form

    # css proxy classes set
    def tinymce_set(self, form):
        if hasattr(self, 'tinymce_fields') and self.tinymce_fields:
            for name in self.tinymce_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] = ' '.join(([f.widget.attrs['class'].strip()]
                                                    if f.widget.attrs.has_key('class')
                                                    else []) + ['editor_tinymce'])
