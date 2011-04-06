from django.conf import settings as django_settings
from django.http import HttpResponseBadRequest
from meta_editor import MetaEditor, FEIN_ADMIN_MEDIA

class ListEditor(MetaEditor):
    def __init__(self, *args, **kwargs):
        super(ListEditor, self).__init__(*args, **kwargs)

        self.list_display = list(self.list_display)

        opts = self.model._meta
        self.change_list_template = [
            'admin/fein/%s/%s/list_editor.html' % (opts.app_label, opts.object_name.lower()),
            'admin/fein/%s/list_editor.html' % opts.app_label,
            'admin/fein/list_editor.html',
            'admin/%s/%s/change_list.html' % (opts.app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % opts.app_label,
            'admin/change_list.html'
        ]

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances
        change list/actions page.
        """

        # handle common AJAX requests
        if request.is_ajax():
            cmd = request.POST.get('__cmd')
            if cmd == 'toggle_boolean':
                return self._toggle_boolean(request)
            else:
                return HttpResponseBadRequest('Oops. AJAX request not understood.')

        self._refresh_changelist_caches()
        extra_context = extra_context or {}
        extra_context['FEIN_ADMIN_MEDIA'] = FEIN_ADMIN_MEDIA
        
        return super(ListEditor, self).changelist_view(request, extra_context, *args, **kwargs)