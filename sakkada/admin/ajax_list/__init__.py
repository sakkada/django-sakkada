from django.contrib import admin
from django.conf import settings
from django.forms.widgets import Media
from django.http import JsonResponse
from django.utils.safestring import mark_safe


def ajax_field_cell(item, attr, text=''):
    return '<div class="ajax_field" id="wrap_%s_%d">%s</div>' % (
        attr, item.id, item._meta.get_field(attr).formfield().widget.render(
            attr, getattr(item, attr),
            attrs={'data-item': item.pk, 'data-attr': attr,}),
    )


def ajax_field_value(item, attr, value):
    return item._meta.get_field(attr).formfield().to_python(value)


def ajax_list_field(attr, short_description=u''):
    """
    Convenience function: Assign the return value of this method to a variable
    of your ModelAdmin class and put the variable name into list_display.
    Example:
        class SomeAjaxListAdmin(AjaxListAdmin):
            toggle_active = ajax_list_field('active', _('is active'))
            list_display = ('pk', 'toggle_active',)
    """
    def wrapper(self, item):
        return mark_safe(ajax_field_cell(item, attr))
    wrapper.short_description = short_description or attr
    wrapper.ajax_editable_field = attr
    return wrapper


class AjaxListAdmin(admin.ModelAdmin):
    ajax_list_parent_template = None

    @property
    def media(self):
        js = '' if settings.DEBUG else '.min'
        js = (
            'admin/js/vendor/jquery/jquery%s.js' % js,
            'admin/js/jquery.init.js',
            'admin/js/cookies.js',
            'admin/ajax_list/scripts.js',
        )

        base = getattr(super(), 'media', Media())
        return base + Media(js=js)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.change_list_template = [
            'admin/ajax_list/%s/%s/change_list.html' % (
                self.model._meta.app_label, self.model._meta.model_name),
            'admin/ajax_list/%s/change_list.html' % self.model._meta.app_label,
            'admin/ajax_list/change_list.html',
        ]

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """Handle the changelist view, add ajax_list_field support."""
        if request.is_ajax():
            if request.POST.get('ajax_list', None) == 'ajax_field_change':
                return self.ajax_field_change(request)

        extra_context = extra_context or {}
        extra_context.update({
            'ajax_list_parent_template': self.ajax_list_parent_template,
        })
        return super().changelist_view(request, extra_context, *args, **kwargs)

    def collect_ajax_fields(self):
        """
        Collect all fields marked as ajax editable. We do not
        want the user to be able to edit arbitrary fields by crafting
        an AJAX request by hand.
        """
        if hasattr(self, '_ajax_editable_fields'):
            return
        self._ajax_editable_fields = {}

        for field in self.list_display:
            attr = getattr(self.__class__, field, None)
            attr = getattr(attr, 'ajax_editable_field', None)
            attr and self._ajax_editable_fields.update({attr: True})

    def ajax_field_change(self, request):
        """Handle an AJAX ajax_field request."""
        try:
            item = int(request.POST.get('item', None))
            attr = str(request.POST.get('attr', None))
            value = str(request.POST.get('value', None))
        except Exception:
            return JsonResponse({'error': 'Invalid request.'})

        if not self.has_change_permission(request, None):
            return JsonResponse(
                {'error': 'You do not have permission to update "%s".' % attr})

        self.collect_ajax_fields()
        if attr not in self._ajax_editable_fields:
            return JsonResponse({'error': 'Invalid attribute "%s".' % attr})

        obj = self.model._default_manager.filter(pk=item).first()
        if obj is None:
            return JsonResponse({'error': 'Object #%s does not exist.' % item})

        try:
            value = ajax_field_value(obj, attr, value)
            setattr(obj, attr, value)
            obj.save()
            data = {'value': value}
        except Exception:
            return JsonResponse(
                {'error': 'Unable to change "%s" on "%s"' % (attr, obj)})

        return JsonResponse(data)
