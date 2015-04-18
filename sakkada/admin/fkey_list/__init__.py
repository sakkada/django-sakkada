# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.util import quote

def fkey_list_link(name, model_set=None, fkey_name=None, with_add_link=False):
    def link(self, item, url_only=None):
        modelset = model_set if model_set else '%s_set' % name
        if not hasattr(item, modelset):
            raise Exception, (u'FkeyList link generater:'
                              u' "%s" does not exist' % modelset)
        modelset = getattr(item, modelset)
        fkeyname = fkey_name if fkey_name else item._meta.model_name

        link = AdminViewName(modelset.model._meta).changelist_fkeylist
        link = reverse(link, None, (fkeyname, item.pk), {})
        if url_only in ['list', 'add']:
            result = '%s%s' % (link, 'add/' if url_only == 'add' else '')
        else:
            vernames = (modelset.model._meta.verbose_name,
                        modelset.model._meta.verbose_name_plural)
            addicon = u'%sadmin/img/icon_addlink.gif' % settings.STATIC_URL
            result = (u'<a href="%s" title="Show related «%s»">%s</a> (%d)'
                      % (link, vernames[1], vernames[1], modelset.count()))
            result = (u'<nobr>%s&nbsp;'
                      u'<a href="%sadd/" title="create related «%s»"><img src="%s"></a>'
                      u'</nobr>' % (result, link, vernames[0], addicon)
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
    Note: get_urls extended and ChangeList extended and all views.
    """
    def get_queryset(self, request):
        """Add fkey id filter from request if exists"""
        qs = super(FkeyListAdmin, self).get_queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            qs = qs.filter(**{request.FKEY_LIST['fkey_name']: request.FKEY_LIST['id']})
        return qs

    def fkey_view(self, request, *args, **kwargs):
        """Common method for all fkey_list views"""
        view_name = kwargs.pop('view_name')

        # try to rescue custom views except change_view
        if view_name == 'change_view':
            value = args[2]
            if not value.isdigit():
                try:
                    item = self.model._default_manager.get(pk=value)
                except ValueError, self.model.DoesNotExist:
                    return HttpResponseRedirect('../../%s' % value)

        if not hasattr(self, view_name):
            raise Exception, 'FkeyList view "%s" does not exist' % view_name

        # check fkey instance
        if not hasattr(self.model, args[0]):
            raise Exception, ('FkeyList: field "%s" does not exist in model "%s"'
                              % (args[0], self.model._meta.model_name))
        parent = getattr(self.model, args[0]).field.rel.to.objects.filter(pk=args[1])
        if parent.count() != 1:
            raise Exception, ('FkeyList: fkey "%s" #%s for "%s" model does not exist'
                              % (args[0], args[1], self.model._meta.model_name))
        parent = parent[0]

        # default and fkey links dependencies
        link_name_parent = AdminViewName(parent.__class__._meta)
        link_name, link_args = AdminViewName(self.model._meta), args[:2]
        link_deps = {
            reverse(link_name.add): reverse(link_name.add_fkeylist, None, args[:2]),
            reverse(link_name.changelist): reverse(link_name.changelist_fkeylist,
                                                   None, args[:2]),
        }

        request.FKEY_LIST = {
            'fkey_name': args[0],
            'id': args[1],
            'item': parent,
            'item_link': reverse(link_name_parent.change, None, (args[1],), {}),
            'list_link': reverse(link_name_parent.changelist, None, (), {}),
            'link_name': link_name,
        }

        # get response
        args = tuple(args[2:])
        response = getattr(self, view_name)(request, *args, **kwargs)

        # try to return fkey location in HttpResponseRedirect instead original
        location = (isinstance(response, HttpResponseRedirect)
                    and response['Location'].split('?', 1))
        if location and location[0] in link_deps:
            response['Location'] = link_deps[location[0]] + ('?%s' % location[1]
                                                             if location.__len__() > 1
                                                             else '')
        return response

    def get_urls(self):
        """Extends urls by nodein routes to nodein_view with view_name param"""
        from django.conf.urls import patterns, url
        try:
            from functools import update_wrapper
        except ImportError:
            # deprecated: django <=1.6
            from django.utils.functional import update_wrapper

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
        """Extent ChangeList class."""
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
