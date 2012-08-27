from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect
from django.core.cache import cache

class CacheClearAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(CacheClearAdmin, self).__init__(*args, **kwargs)
        self.change_list_template = [
            'admin/cache/%s/%s/change_list.html' % (self.opts.app_label, self.opts.object_name.lower()),
            'admin/cache/%s/change_list.html' % self.opts.app_label,
            'admin/cache/change_list.html',
        ]

    def cache_clear(self, request):
        return cache_clear(request, self)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        info = self.opts.app_label, self.opts.module_name
        urls = patterns('', url(
            r'^cache_clear/$', self.admin_site.admin_view(self.cache_clear),
            name="%s_%s_cache_clear" % info
        ))
        return urls + super(CacheClearAdmin, self).get_urls()

@staff_member_required
def cache_clear(request, model_admin):
    if request.POST.get('post', None):
        cache.clear()
        message = _('Cache data has been successfully cleared')
        messages.success(request, message)
        return redirect('.')

    opts = model_admin.model._meta
    has_perm = request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())
    context = {
        'title':                    _("Cache clear page"),
        'opts':                     opts,
        'app_label':                opts.app_label,
        'has_change_permission':    has_perm,
    }
    template = [
        'admin/cache/%s/%s/cache_clear.html' % (opts.app_label, opts.object_name.lower()),
        'admin/cache/%s/cache_clear.html' % opts.app_label,
        'admin/cache/cache_clear.html',
    ]
    return render(request, template, context)