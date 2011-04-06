from django.contrib import admin

class AttrsProxyAdmin(admin.ModelAdmin):
    """Set attrs to widgets from self.attrs_proxy['fieldname']['attrname'] to fieldname.widget['attrname']"""
    attrs_proxy = {}
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(AttrsProxyAdmin, self).get_form(request, obj=None, **kwargs)
        # set some css classes
        self.attrs_proxy_set(form)
        return form
        
    # css proxy classes set
    def attrs_proxy_set(self, form):
        if hasattr(self, 'attrs_proxy') and self.attrs_proxy:
            for name in self.attrs_proxy:
                field = form.base_fields.get(name, None)
                if field is None: continue
                for key, value in self.attrs_proxy[name].items():
                    key, is_add = key.strip('+'), key[0] is '+'
                    value = [value] if not isinstance(value, (list, tuple)) else value
                    if is_add:
                        value = ([field.widget.attrs[key].strip()] if field.widget.attrs.has_key(key) else []) + value
                    field.widget.attrs[key] = u' '.join(value)