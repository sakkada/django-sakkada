from urllib.parse import urlparse, urlunparse
from functools import update_wrapper
from django.urls import reverse, resolve, Resolver404
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.utils import quote
from django.templatetags.static import static


# Common Classes
# --------------
class AdminViewName(object):
    """Object returns full admin urlname by postfix only."""
    def __init__(self, opts):
        self.opts = opts

    def __getattr__(self, name):
        return 'admin:%s_%s_%s' % (self.opts.app_label,
                                   self.opts.model_name, name)


class FkeyListChangeList(ChangeList):
    fkey_list_data = None

    def __init__(self, request, *args):
        super().__init__(request, *args)
        if hasattr(request, 'FKEY_LIST'):
            self.fkey_list_data = request.FKEY_LIST

    def url_for_result(self, result):  # (child fkey_list)
        if self.fkey_list_data:
            view = getattr(self.fkey_list_data['link_name'], 'change_fkeylist')
            args = (self.fkey_list_data['fkey_name'],
                    quote(self.fkey_list_data['id']),
                    quote(getattr(result, self.pk_attname)),)
            return reverse(view, args=args,
                           current_app=self.model_admin.admin_site.name)

        return super().url_for_result(result)

    def get_queryset(self, request):  # (parent fkey_list)
        # add count annotations if fkey_list_annotate_counts defined
        qs = super().get_queryset(request)
        annotations = self.model_admin.fkey_list_annotate_counts
        if annotations and isinstance(annotations, (list, tuple,)):
            qs = qs.annotate(*[Count(i, distinct=True) for i in annotations])
        return qs


# Parent FkeyList Admin section
# ------------------------------
def fkey_list_link(name, model_set=None, fkey_name=None,
                   with_count=True, with_add_link=False):
    """
    Arguments:
    - name: name of child model and name of the link (this value used to
        generate field's related_name by appending suffix "_set"
        if model_set value is empty)
    - model_set: name of foreign key reverse field (usually {model}_set);
        required, if related_name value of foreign key field in child model
        is not default
    - fkey_name: foreign key field name (foreign model name by default);
        required, if foreign key field name is not equal to foreign model
        name
    - with_count: show count of related objects, default True;
        try to get value from "{model_set.field.related_query_name}__count"
        attribute first (see fkey_list_annotate_counts), if attribute not
        exists - call "count" method on model_set queryset;
        if value of with_count is non-empty string, it will be used as
        count attribute name instead related_query_name with suffix
    - with_add_link: add link to add new item (+ icon), default False
    """
    def link(self, item, url_only=None):
        """
        Arguments:
        - item: model instance fkey field is related to
        - url_only: if "add" or "list" - return just requested URL
        """
        # modelset and fkeyname names used because model_set and fkey_name
        # are closured variables in "link" function
        modelset = model_set if model_set else '%s_set' % name
        fkeyname = fkey_name if fkey_name else item._meta.model_name
        if not hasattr(item, modelset):
            raise Exception('FkeyList link generater:'
                            ' "%s" does not exist' % modelset)
        modelset = getattr(item, modelset)
        viewname = AdminViewName(modelset.model._meta)

        link_add = reverse(
            viewname.add_fkeylist, None, (fkeyname, item.pk),)
        link_list = reverse(
            viewname.changelist_fkeylist, None, (fkeyname, item.pk),)

        if url_only in ('list', 'add',):
            result = link_add if url_only == 'add' else link_list
        else:
            names = (modelset.model._meta.verbose_name.capitalize(),
                     modelset.model._meta.verbose_name_plural.capitalize(),)
            count = ''
            if with_count:
                count = (with_count if isinstance(with_count, str) else
                         '%s__count' % modelset.field.related_query_name())
                count = (getattr(item, count) if hasattr(item, count) else
                         modelset.count())
                count = ' (%s)' % (count)
            result = ('<a href="%s" title="Show related «%s»">%s</a>%s'
                      % (link_list, names[1], names[1], count))
            result = ('<span class="nowrap">'
                      '%s <a href="%s" title="Create related «%s»">'
                      '<img src="%s"></a></span>' % (
                          result, link_add, names[0],
                          static('admin/img/icon-addlink.svg')
                      ) if with_add_link else result)

        return mark_safe(result)
    link.short_description = '%s list' % name

    return link


class FkeyListParentAdmin(admin.ModelAdmin):
    """Added fkey_list parent only functionality."""

    # if defined list of names - annotate counts by names
    fkey_list_annotate_counts = None
    fkey_list_root_link = None

    def get_changelist(self, request, **kwargs):
        """Extend ChangeList class"""
        if not hasattr(self, '_changelist_class'):
            cls = super().get_changelist(request, **kwargs)
            if cls is not ChangeList:
                class FkeyListChangeListMixed(FkeyListChangeList, cls):
                    pass
                self._changelist_class = FkeyListChangeListMixed
            else:
                self._changelist_class = FkeyListChangeList

        return self._changelist_class


# Child and parent FkeyList Admin section
# ---------------------------------------
class FkeyListAdmin(FkeyListParentAdmin, admin.ModelAdmin):
    """
    Added fkey_list parent and child functionality.
    Note: get_urls extended, ChangeList extended,
          all views and template also extended.
    """
    # alternative parent template names
    fkey_list_parent_change_list_template = None
    fkey_list_parent_change_form_template = None
    fkey_list_parent_delete_confirmation_template = None
    fkey_list_parent_delete_selected_confirmation_template = None
    fkey_list_parent_object_history_template = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opts = self.model._meta
        app, model = opts.app_label, (opts.app_label, opts.model_name,)

        self.change_list_template = [
            'admin/fkey_list/%s/%s/change_list.html' % model,
            'admin/fkey_list/%s/change_list.html' % app,
            'admin/fkey_list/change_list.html',
        ]
        self.change_form_template = [
            'admin/fkey_list/%s/%s/change_form.html' % model,
            'admin/fkey_list/%s/change_form.html' % app,
            'admin/fkey_list/change_form.html'
        ]
        self.delete_confirmation_template = [
            'admin/fkey_list/%s/%s/delete_confirmation.html' % model,
            'admin/fkey_list/%s/delete_confirmation.html' % app,
            'admin/fkey_list/delete_confirmation.html'
        ]
        self.delete_selected_confirmation_template = [
            'admin/fkey_list/%s/%s/delete_selected_confirmation.html' % model,
            'admin/fkey_list/%s/delete_selected_confirmation.html' % app,
            'admin/fkey_list/delete_selected_confirmation.html'
        ]
        self.object_history_template = [
            'admin/fkey_list/%s/%s/object_history.html' % model,
            'admin/fkey_list/%s/object_history.html' % app,
            'admin/fkey_list/object_history.html'
        ]

    def get_admin_view_name_for_model(self, model):
        return AdminViewName(model._meta)

    def fkey_view(self, request, *args, **kwargs):
        """Common method for all fkey_list views"""
        view_name = kwargs.pop('view_name')
        fkey_name, fkey_id = args[0], args[1]

        # try to rescue custom views except change_view
        if view_name == 'change_view':
            value = args[2]
            if not value.isdigit():
                try:
                    self.model._default_manager.get(pk=value)
                except (ValueError, self.model.DoesNotExist):
                    return HttpResponseRedirect('../../%s' % value)

        if not hasattr(self, view_name):
            raise Exception('FkeyList: view "%s" does not exist' % view_name)

        # check fkey instance
        if not hasattr(self.model, fkey_name):
            raise Exception('FkeyList: field "%s" does not exist in model "%s"'
                            % (fkey_name, self.model._meta.model_name,))

        related_model = getattr(self.model, fkey_name).field.remote_field.model
        parent = related_model.objects.filter(pk=fkey_id).first()
        if not parent:
            raise Exception('FkeyList: fkey "%s" #%s for "%s" does not exist'
                            % (fkey_name, fkey_id, self.model._meta.model_name,))

        # default and fkey links dependencies
        link_args = args[:2]
        link_name = self.get_admin_view_name_for_model(self.model)
        link_name_parent = self.get_admin_view_name_for_model(type(parent))
        link_deps = {
            link_name.add: reverse(
                link_name.add_fkeylist, None, link_args),
            link_name.changelist: reverse(
                link_name.changelist_fkeylist, None, link_args),
            link_name.change: True,
        }

        # get root_link (string or link of strings)
        root_link = None
        if self.fkey_list_root_link:
            root_link = (self.fkey_list_root_link(request, *args, **kwargs)
                         if callable(self.fkey_list_root_link) else
                         self.fkey_list_root_link)
        if root_link and not isinstance(root_link, (list, tuple,)):
            root_link = (root_link,)

        request.FKEY_LIST = {
            'fkey_name': fkey_name,
            'fkey_opts': related_model._meta,
            'id': fkey_id,
            'item': parent,
            'item_link': reverse(link_name_parent.change, None, (args[1],)),
            'list_link': reverse(link_name_parent.changelist, None, ()),
            'root_link': root_link,
            'link_name': link_name,
        }

        # update context of any view
        extra_context = kwargs.get('extra_context', {})
        extra_context.update(dict([(i, getattr(self, i),) for i in (
            'fkey_list_parent_change_list_template',
            'fkey_list_parent_change_form_template',
            'fkey_list_parent_delete_confirmation_template',
            'fkey_list_parent_delete_selected_confirmation_template',
            'fkey_list_parent_object_history_template',
        )]))
        kwargs['extra_context'] = extra_context

        # get response
        fkeyargs, clearargs = tuple(args[:2]), tuple(args[2:])
        response = getattr(self, view_name)(request, *clearargs, **kwargs)

        # try to return fkey location in HttpResponseRedirect instead original
        location, newlocation = (isinstance(response, HttpResponseRedirect)
                                 and response['Location']), None
        while location:
            # parse redirect url to save GET querystring, etc
            parsed = urlparse(location)

            # resolve redirect location
            try:
                match = resolve(parsed.path)
            except Resolver404:
                break

            newlocation = link_deps.get(match.view_name, None)
            if not newlocation:
                break

            # 1 - if link_deps value contains non-empty string (url), redirect
            # rescue "add new after saving" and "return to changelist" redirects
            if isinstance(newlocation, str):
                break

            # 2 - if link_deps value is True, process each case directly
            # rescue "continue editing" redirects after new object adding
            if match.view_name == link_name.change:
                newlocation = reverse(link_name.change_fkeylist,
                                      None, fkeyargs + (match.args[0],))
                break
            break

        if newlocation:
            response['Location'] = urlunparse(
                parsed[:2] + (newlocation,) + parsed[3:]
            )
        return response

    def get_urls(self):
        """Extends urls by fkey routes to fkey_view with view_name param"""
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        info = '%s_%s' % (self.model._meta.app_label,
                          self.model._meta.model_name,)
        urlpatterns = [
            url(r'^(\w+)-(\d+)/$', wrap(self.fkey_view),
                {'view_name': 'changelist_view'},
                name='%s_changelist_fkeylist' % info),
            url(r'^(\w+)-(\d+)/add/$', wrap(self.fkey_view),
                {'view_name': 'add_view'},
                name='%s_add_fkeylist' % info),
            url(r'^(\w+)-(\d+)/(.+)/history/$', wrap(self.fkey_view),
                {'view_name': 'history_view'},
                name='%s_history_fkeylist' % info),
            url(r'^(\w+)-(\d+)/(.+)/delete/$', wrap(self.fkey_view),
                {'view_name': 'delete_view'},
                name='%s_delete_fkeylist' % info),
            url(r'^(\w+)-(\d+)/(.+)/change/$', wrap(self.fkey_view),
                {'view_name': 'change_view'},
                name='%s_change_fkeylist' % info),
        ]

        return urlpatterns + super().get_urls()

    def get_preserved_filters(self, request):
        """Returns the preserved filters querystring."""
        match = request.resolver_match
        if self.preserve_filters and match:
            # same as default if changelist_fkeylist
            current_url = '%s:%s' % (match.app_name, match.url_name)
            view_name = AdminViewName(self.model._meta)
            if current_url == view_name.changelist_fkeylist:
                preserved_filters = request.GET.urlencode()
            else:
                preserved_filters = None

            if preserved_filters:
                return urlencode({'_changelist_filters': preserved_filters,})
        return super().get_preserved_filters(request)

    def get_form(self, request, obj=None, **kwargs):
        """Set initial foreign key value if FKEY_LIST"""
        form = super().get_form(request, obj, **kwargs)
        fkey_name = getattr(request, 'FKEY_LIST', {}).get('fkey_name', None)
        if obj is None and fkey_name:
            form.base_fields[fkey_name].initial = request.FKEY_LIST['id']

        return form

    def get_queryset(self, request):
        """Add fkey id filter from request if exists"""
        qs = super().get_queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            qs = qs.filter(**{
                request.FKEY_LIST['fkey_name']: request.FKEY_LIST['id'],
            })
        return qs


class FkeyMpttAdmin(FkeyListAdmin):
    def get_queryset(self, request):
        """Add fkey left and right filter from request if exists"""
        qs = super().get_queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            item = request.FKEY_LIST['item']
            opts = item._mptt_meta
            qs = qs.filter(**{
                opts.tree_id_attr: getattr(item, opts.tree_id_attr),
                '%s__gt' % opts.left_attr: getattr(item, opts.left_attr),
                '%s__lt' % opts.left_attr: getattr(item, opts.right_attr),
            })

        return qs
