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
        return super().__init__(*args, **kwargs)

    def register_view(self, regex, view=None, urlname=None, kwargs=None,
                      wrap_view=True, name=None, help_text=None, visible=True,
                      provide_admin_site=True, dashboard_extra_context=None):
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
        * `provide_admin_site` is an optional, that allow providing AdminSite
            instance to the view throw "admin_site" argument, True by default.
        * `dashboard_extra_context` is an optional parameter, that will be
            stored in corresponding custom_views item in dashboard template,
            if "link_icon" key specified, it will be used as css class
                name of <li> container in index template (default is empty,
                provided by django: "addlink", "changelink" and "deletelink").
        """
        urlname = urlname or uuid.uuid4().hex

        if view is not None:
            if inspect.isclass(view) and issubclass(view, View):
                view = view.as_view()
            self.custom_views.append((
                (regex, view, urlname, kwargs, wrap_view, provide_admin_site,),
                (name, help_text, visible, urlname, dashboard_extra_context,),
            ))
            return

        def decorator(fn):
            if inspect.isclass(fn) and issubclass(fn, View):
                fn = fn.as_view()
            self.custom_views.append((
                (regex, fn, urlname, kwargs, wrap_view, provide_admin_site),
                (name, help_text, visible, urlname, dashboard_extra_context,),
            ))
            return fn
        return decorator

    def get_urls(self):
        """Add our custom views to the admin urlconf."""
        from django.conf.urls import url

        customs_views_urls = []
        for (regex, fn, urlname, kwargs, wrap_view,
             provide_admin_site), _ in self.custom_views:
            aview = self.admin_view(fn) if wrap_view else fn
            if provide_admin_site:
                kwargs = kwargs or {}
                kwargs.update(admin_site=self)
            customs_views_urls.append(url(regex, aview,
                                          name=urlname, kwargs=kwargs))

        return customs_views_urls + super().get_urls()

    def index(self, request, extra_context=None):
        """Insert a custom views list into index page's context."""
        if not extra_context:
            extra_context = {}

        custom_views = []
        if self.custom_views_show_dashboard:
            for i, (name, help_text, visible, urlname,
                    dashboard_extra_context) in self.custom_views:
                if visible is True:
                    custom_views.append((urlname, name or capfirst(i[1].__name__),
                                         help_text, dashboard_extra_context))

        # Sort views alphabetically.
        custom_views.sort(key=lambda x: x[1])
        extra_context.update({
            'custom_views': custom_views,
            'custom_views_parent_template': self.custom_views_parent_template,
        })
        return super().index(request, extra_context)


class AdminViewsSite(AdminViewsMixin, AdminSite):
    """
    A Django AdminSite with the AdminViewsMixin
    to allow registering custom views not connected to models.
    """
