from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect
from django.core.cache import caches


def cache_clear_view(request, template_name=None, extra_context=None,
                     admin_site=None):
    """Clear system cache data."""
    cache = caches['default']
    if request.POST.get('post', None):
        cache.clear()
        messages.success(request, _('Cache data has been successfully cleared.'))
        return redirect('.')

    context = {'title': _("Cache clear"),}
    context.update(admin_site.each_context(request))
    context.update(**(extra_context or {}))
    template_name = template_name or ('admin/cache/cache_clear.html',
                                      'admin/cache_clear.html',)
    return render(request, template_name, context)
