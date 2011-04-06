# -*- coding: utf-8 -*-
from django.contrib import admin
from django.conf import settings

class EditorAdmin(admin.ModelAdmin):
    class Media:
        js = [
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.min.js',
            settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
            settings.MEDIA_URL + 'admin/jquery/init.js',
            settings.MEDIA_URL + 'admin/simple_fb/activater.js',
        ]
        
        css = {'all': [settings.MEDIA_URL + 'admin/simple_fb/activater.css',]}

    simple_fb_fields = {}
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(EditorAdmin, self).get_form(request, obj=None, **kwargs)
        # set some css classes
        self.simple_fb_set(form)
        return form
        
    # css proxy classes set
    def simple_fb_set(self, form):
        if hasattr(self, 'simple_fb_fields') and self.simple_fb_fields:
            for name in self.simple_fb_fields:
                f = form.base_fields[name]
                f.widget.attrs['class'] = ' '.join(([f.widget.attrs['class'].strip()] if f.widget.attrs.has_key('class') else []) + ['editor_simple_fb'])