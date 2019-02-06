import json
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseServerError, HttpResponseForbidden,
                         HttpResponseNotFound)
from django.core.exceptions import PermissionDenied
from django.contrib import admin
from django.conf import settings
from django.forms.widgets import Media
from django.utils.safestring import mark_safe


def ajax_field_cell(item, attr, text=''):
    attrs = {'data-item': item.pk, 'data-attr': attr,}
    text = item._meta.get_field(attr).formfield() \
               .widget.render(attr, getattr(item, attr), attrs=attrs)
    text = (u'<div class="ajax_field" id="wrap_%s_%d">%s</div>'
            % (attr, item.id, text,))

    return text

def ajax_field_value(item, attr, value):
    attrs = {'data-item': item.pk, 'data-attr': attr,}
    return item._meta.get_field(attr).formfield().to_python(value)

def ajax_list_field(attr, short_description=u''):
    """
    Convenience function: Assign the return value of this method to a variable
    of your ModelAdmin class and put the variable name into list_display.
    Example:
        class SomeAjaxListAdmin(AjaxListAdmin):
            toggle_active = ajax_field('active', _('is active'))
            list_display = ('pk', 'toggle_active',)
    """
    def _fn(self, item):
        return mark_safe(ajax_field_cell(item, attr))
    _fn.short_description = short_description or attr
    _fn.ajax_editable_field = attr
    return _fn


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
        css = {'all': ('admin/ajax_list/styles.css',),}

        base = getattr(super(AjaxListAdmin, self), 'media', Media())
        return base + Media(js=js, css=css)

    def __init__(self, *args, **kwargs):
        """AjaxBool Admin initialisation"""
        super(AjaxListAdmin, self).__init__(*args, **kwargs)
        opts = self.model._meta
        self.change_list_template = [
            'admin/ajax_list/%s/%s/change_list.html' % (opts.app_label,
                                                             opts.model_name),
            'admin/ajax_list/%s/change_list.html' % opts.app_label,
            'admin/ajax_list/change_list.html',
        ]

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """Handle the changelist view, add ajax_list_field support."""

        # handle common AJAX requests
        if request.is_ajax():
            cmd = request.POST.get('__cmd__')
            if cmd == 'ajax_field_change':
                return self._ajax_field_change(request)

        extra_context = extra_context or {}
        extra_context.update({
            'ajax_list_parent_template': self.ajax_list_parent_template,
        })
        return super(AjaxListAdmin, self).changelist_view(request, extra_context,
                                                          *args, **kwargs)

    def _collect_ajax_fields(self):
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

    def _ajax_field_change(self, request):
        """Handle an AJAX ajax_field request"""
        try:
            item = int(request.POST.get('item', None))
            attr = str(request.POST.get('attr', None))
            value = str(request.POST.get('value', None))
        except:
            return HttpResponseBadRequest('Invalid request')

        if not self.has_change_permission(request, None):
            return HttpResponseForbidden('You do not have permission'
                                         ' to update "%s";' % attr)

        self._collect_ajax_fields()

        if not attr in self._ajax_editable_fields:
            return HttpResponseBadRequest('Not a valid attribute "%s"' % attr)

        try:
            obj = self.model._default_manager.get(pk=item)
        except self.model.DoesNotExist:
            return HttpResponseNotFound('Object does not exist')

        try:
            value = ajax_field_value(obj, attr, value)
            setattr(obj, attr, value)
            obj.save()
            data = {'status': 'OK', 'value': value,}
        except Exception, e:
            return HttpResponseServerError('Unable to change "%s" on "%s"'
                                           % (attr, obj))

        return HttpResponse(json.dumps(data), content_type='application/json')
