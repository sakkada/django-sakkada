# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.db.models import Count
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.utils import quote
from django.contrib.admin.templatetags.admin_static import static


def fkey_list_link(name, model_set=None, fkey_name=None,
                   with_count=True, with_add_link=False):
    def link(self, item, url_only=None):
        """
        Arguments:
        - name: name of child model and link (also name of model set by default)
        - model_set: name of foreign key reverse field (usually {name}_set);
                     required, if related_name value in child model is not default
        - fkey_name: foreign key field name (model_name by default); required,
                     if foreign key field name is not equal to parent model name
        - with_count: show count of related objects, default True (try to get
                      value from "{model_set}__count" attribute first (see
                      fkey_list_annotate_counts), else call "count" method
                      on model_set queryset)
        - with_add_link: add link to add new item (+ icon), default False
        """
        msetname = model_set if model_set else '%s_set' % name
        if not hasattr(item, msetname):
            raise Exception(u'FkeyList link generater:'
                            u' "%s" does not exist' % msetname)
        modelset = getattr(item, msetname)
        fkeyname = fkey_name if fkey_name else item._meta.model_name

        view = AdminViewName(modelset.model._meta)
        link_add = (view.add_fkeylist, None, (fkeyname, item.pk), {},)
        link_list = (view.changelist_fkeylist, None, (fkeyname, item.pk), {},)

        if url_only in ('list', 'add',):
            result = link_add if url_only == 'add' else link_list
            result = reverse(*result)
        else:
            vernames = (modelset.model._meta.verbose_name.capitalize(),
                        modelset.model._meta.verbose_name_plural.capitalize(),)
            count = ''
            if with_count:
                count = getattr(item, '%s__count' % msetname, None)
                count = ' (%s)' % (modelset.count() if count is None else count)

            addicon = static(u'admin/img/icon_addlink.gif')
            result = (u'<a href="%s" title="Show related «%s»">%s</a>%s'
                      % (reverse(*link_list), vernames[1], vernames[1], count))
            result = (u'<nobr>%s&nbsp;'
                      u'<a href="%s" title="Create related «%s»"><img src="%s"></a>'
                      u'</nobr>' % (result, reverse(*link_add), vernames[0], addicon)
                      if with_add_link else result)
        return result
    link.short_description = '%s list' % name
    link.allow_tags = True

    return link


class AdminViewName(object):
    """Object return full revers urlname by postfix only"""
    def __init__(self, opts):
        self.opts = opts

    def __getattr__(self, name):
        return 'admin:%s_%s_%s' % (self.opts.app_label, self.opts.model_name, name)


class FkeyListChangeList(ChangeList):
    fkey_list_data = None

    def __init__(self, request, *args):
        super(FkeyListChangeList, self).__init__(request, *args)
        if hasattr(request, 'FKEY_LIST'):
            self.fkey_list_data = request.FKEY_LIST

    def get_queryset(self, request):
        # add annotate counts if fkey_list_annotate_counts defined
        qs = super(FkeyListChangeList, self).get_queryset(request)
        annotations = self.model_admin.fkey_list_annotate_counts
        if annotations and isinstance(annotations, (list, tuple,)):
            qs = qs.annotate(*[Count(i, distinct=True) for i in annotations])
        return qs

    def url_for_result(self, result):
        if self.fkey_list_data:
            view = getattr(self.fkey_list_data['link_name'], 'change_fkeylist')
            args = (self.fkey_list_data['fkey_name'],
                    quote(self.fkey_list_data['id']),
                    quote(getattr(result, self.pk_attname)),)
            return reverse(view, args=args,
                           current_app=self.model_admin.admin_site.name)

        return super(FkeyListChangeList, self).url_for_result(result)


class FkeyListAdmin(admin.ModelAdmin):
    """
    Added fkey_list functionality.
    Note: get_urls extended, ChangeList extended,
          all views and template also extended.
    """
    # alternative parent template names
    fkey_list_parent_change_list_template = None
    fkey_list_parent_change_form_template = None
    fkey_list_parent_delete_confirmation_template = None
    fkey_list_parent_delete_selected_confirmation_template = None
    fkey_list_parent_object_history_template = None

    # if defined list of names - annotate counts by names
    fkey_list_annotate_counts = None

    def __init__(self, *args, **kwargs):
        super(FkeyListAdmin, self).__init__(*args, **kwargs)
        opts = self.model._meta
        appl, applmodn = opts.app_label, (opts.app_label, opts.model_name,)

        self.change_list_template = [
            'admin/fkey_list/%s/%s/change_list.html' % applmodn,
            'admin/fkey_list/%s/change_list.html' % appl,
            'admin/fkey_list/change_list.html',
        ]
        self.change_form_template = [
            'admin/fkey_list/%s/%s/change_form.html' % applmodn,
            'admin/fkey_list/%s/change_form.html' % appl,
            'admin/fkey_list/change_form.html'
        ]
        self.delete_confirmation_template = [
            'admin/fkey_list/%s/%s/delete_confirmation.html' % applmodn,
            'admin/fkey_list/%s/delete_confirmation.html' % appl,
            'admin/fkey_list/delete_confirmation.html'
        ]
        self.delete_selected_confirmation_template = [
            'admin/fkey_list/%s/%s/delete_selected_confirmation.html' % applmodn,
            'admin/fkey_list/%s/delete_selected_confirmation.html' % appl,
            'admin/fkey_list/delete_selected_confirmation.html'
        ]
        self.object_history_template = [
            'admin/fkey_list/%s/%s/object_history.html' % applmodn,
            'admin/fkey_list/%s/object_history.html' % appl,
            'admin/fkey_list/object_history.html'
        ]

    def get_queryset(self, request):
        """Add fkey id filter from request if exists"""
        qs = super(FkeyListAdmin, self).get_queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            qs = qs.filter(**{request.FKEY_LIST['fkey_name']: request.FKEY_LIST['id'],})
        return qs

    def fkey_view(self, request, *args, **kwargs):
        """Common method for all fkey_list views"""
        view_name = kwargs.pop('view_name')
        fkey_name, fkey_id = args[0], args[1]

        # try to rescue custom views except change_view
        if view_name == 'change_view':
            value = args[2]
            if not value.isdigit():
                try:
                    item = self.model._default_manager.get(pk=value)
                except ValueError, self.model.DoesNotExist:
                    return HttpResponseRedirect('../../%s' % value)

        if not hasattr(self, view_name):
            raise Exception('FkeyList: view "%s" does not exist' % view_name)

        # check fkey instance
        if not hasattr(self.model, fkey_name):
            raise Exception('FkeyList: field "%s" does not exist in model "%s"'
                            % (fkey_name, self.model._meta.model_name))
        parent = getattr(self.model, fkey_name).field.rel.to.objects.filter(pk=fkey_id)
        if not parent.exists():
            raise Exception('FkeyList: fkey "%s" #%s for "%s" does not exist'
                            % (fkey_name, fkey_id, self.model._meta.model_name))
        parent = parent[0]

        # default and fkey links dependencies
        link_name_parent = AdminViewName(parent.__class__._meta)
        link_name, link_args = AdminViewName(self.model._meta), args[:2]
        link_deps = {
            reverse(link_name.add): reverse(link_name.add_fkeylist, None, link_args),
            reverse(link_name.changelist): reverse(link_name.changelist_fkeylist,
                                                   None, link_args),
        }

        request.FKEY_LIST = {
            'fkey_name': fkey_name,
            'id': fkey_id,
            'item': parent,
            'item_link': reverse(link_name_parent.change, None, (args[1],), {}),
            'list_link': reverse(link_name_parent.changelist, None, (), {}),
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
        args = tuple(args[2:])
        response = getattr(self, view_name)(request, *args, **kwargs)

        # try to return fkey location in HttpResponseRedirect instead original
        # todo: parse url for clean processing
        location = (isinstance(response, HttpResponseRedirect)
                    and response['Location'].split('?', 1))
        if location and location[0] in link_deps:
            response['Location'] = '?'.join([link_deps[location[0]]]+location[1:])
        return response

    def get_urls(self):
        """Extends urls by fkey routes to fkey_view with view_name param"""
        from django.conf.urls import patterns, url
        from functools import update_wrapper

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = '%s_%s' % (self.model._meta.app_label, self.model._meta.model_name,)
        urlpatterns = patterns('',
            url(r'^([\w\d\_]+)-(\d+)/$', wrap(self.fkey_view),
                {'view_name': 'changelist_view'}, name='%s_changelist_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/add/$', wrap(self.fkey_view),
                {'view_name': 'add_view'}, name='%s_add_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/history/$', wrap(self.fkey_view),
                {'view_name': 'history_view'}, name='%s_history_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/delete/$', wrap(self.fkey_view),
                {'view_name': 'delete_view'}, name='%s_delete_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/$', wrap(self.fkey_view),
                {'view_name': 'change_view'}, name='%s_change_fkeylist' % info),
        )

        return urlpatterns + super(FkeyListAdmin, self).get_urls()

    def get_preserved_filters(self, request):
        """Returns the preserved filters querystring."""
        match = request.resolver_match
        if self.preserve_filters and match:
            # same as default if changelist_fkeylist
            view_name = AdminViewName(self.model._meta)
            current_url = '%s:%s' % (match.app_name, match.url_name)
            if current_url == view_name.changelist_fkeylist:
                preserved_filters = request.GET.urlencode()
            else:
                preserved_filters = None
            if preserved_filters:
                return urlencode({'_changelist_filters': preserved_filters,})
        return super(FkeyListAdmin, self).get_preserved_filters(request)

    def get_form(self, request, obj=None, **kwargs):
        """Set initial foreign key value if FKEY_LIST"""
        form = super(FkeyListAdmin, self).get_form(request, obj, **kwargs)
        fkey_name = getattr(request, 'FKEY_LIST', {}).get('fkey_name', None)
        if obj is None and fkey_name:
            form.base_fields[fkey_name].initial = request.FKEY_LIST['id']

        return form

    def get_changelist(self, request, **kwargs):
        """Extend ChangeList class"""
        if not getattr(self, '_changelist_class', None):
            cls = super(FkeyListAdmin, self).get_changelist(request, **kwargs)
            if cls is not ChangeList:
                class FkeyListChangeListMixed(FkeyListChangeList, cls):
                    pass
                self._changelist_class = FkeyListChangeListMixed
            else:
                self._changelist_class = FkeyListChangeList

        return self._changelist_class


class FkeyMpttAdmin(FkeyListAdmin):
    def get_queryset(self, request):
        """Add fkey left and right filter from request if exists"""
        qs = super(FkeyListAdmin, self).get_queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            item = request.FKEY_LIST['item']
            opts = item._mptt_meta
            filters = {opts.tree_id_attr: getattr(item, opts.tree_id_attr),}
            filters['%s__gt' % opts.left_attr] = getattr(item, opts.left_attr)
            filters['%s__lt' % opts.left_attr] = getattr(item, opts.right_attr)
            qs = qs.filter(**filters)

        return qs
