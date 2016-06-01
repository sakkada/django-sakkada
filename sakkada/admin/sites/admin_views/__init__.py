# Idea and source code taken from http://github.com/jsocol/django-adminplus
# Thanks for James Socol (me@jamessocol.com)
import inspect
import uuid
from django.contrib.admin.sites import AdminSite
from django.utils.text import capfirst
from django.views.generic import View

__all__ = ("AdminViewsMixin", "AdminViewsSite",)


class AdminViewsMixin(object):
    """Mixin for AdminSite to allow registering custom admin views."""

    index_template = 'admin/views/index.html'
    custom_views = None
    custom_views_parent_template = None
    custom_views_show_dashboard = True

    def __init__(self, *args, **kwargs):
        self.custom_views = []
        return super(AdminViewsMixin, self).__init__(*args, **kwargs)

    def register_view(self, regex, view=None, urlname=None, kwargs=None,
                      wrap_view=True, name=None, help_text=None, visible=True):
        """
        Add a custom admin view. Can be used as a function or a decorator.

        * `regex` is the regex pattern in the url().
        * `view` is any view function you can imagine.
        * `urlname` is an optional parameter to be able to call the view with a
            redirect() or reverse().
        * `kwargs` is an optional parameter for url().
        * `wrap_view` is a boolean to allow wrap view with admin_view.
        * `name` is an optional pretty name for the list of custom views. If
            empty, we'll guess based on view.__name__.
        * `help_text` is an optional short description of what view do.
        * `visible` is a boolean to set if the custom view should be visible in
            the admin dashboard or not.
        """
        urlname = urlname or uuid.uuid4().hex

        if view is not None:
            if inspect.isclass(view) and issubclass(view, View):
                view = view.as_view()
            self.custom_views.append(((regex, view, urlname, kwargs, wrap_view),
                                      (name, help_text, visible, urlname,),))
            return

        def decorator(fn):
            if inspect.isclass(fn) and issubclass(fn, View):
                fn = fn.as_view()
            self.custom_views.append(((regex, fn, urlname, kwargs, wrap_view),
                                      (name, help_text, visible, urlname,),))
            return fn
        return decorator

    def get_urls(self):
        """Add our custom views to the admin urlconf."""
        from django.conf.urls import url

        customs_views_urls = []
        for regex, _ in self.custom_views:
            aview = self.admin_view(regex[1]) if regex[4] else regex[1]
            customs_views_urls.append(url(regex[0], aview,
                                          name=regex[2], kwargs=regex[3]))

        return customs_views_urls + super(AdminViewsMixin, self).get_urls()

    def index(self, request, extra_context=None):
        """Insert a custom views list into index page's context."""
        if not extra_context:
            extra_context = {}

        custom_views = []
        if self.custom_views_show_dashboard:
            for i, (name, help_text, visible, urlname,) in self.custom_views:
                if visible is True:
                    custom_views.append((urlname, name or capfirst(i[1].__name__),
                                         help_text))

        # Sort views alphabetically.
        custom_views.sort(key=lambda x: x[1])
        extra_context.update({
            'custom_views': custom_views,
            'custom_views_parent_template': self.custom_views_parent_template,
        })
        return super(AdminViewsMixin, self).index(request, extra_context)


class AdminViewsSite(AdminViewsMixin, AdminSite):
    """
    A Django AdminSite with the AdminViewsMixin
    to allow registering custom views not connected to models.
    """
