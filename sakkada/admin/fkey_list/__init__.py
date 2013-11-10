from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import admin
from django.conf import settings

def fkey_list_link(name, model_set=None, fkey_name=None, with_add_link=False):
    def link(self, item, url_only=None):
        modelset    = model_set if model_set else '%s_set' % name
        if not hasattr(item, modelset):
            raise Exception, u'FkeyList link generater: "%s" does not exist' % modelset
        modelset    = getattr(item, modelset)
        fkeyname    = fkey_name if fkey_name else item._meta.module_name
        link        = u'admin:%s_%s_changelist_fkeylist' % (modelset.model._meta.app_label, 
                                                            modelset.model._meta.module_name)
        link        = reverse(link, None, (fkeyname, item.pk), {})
        if url_only in ['list', 'add']:
            result  = '%s%s' % (link, 'add/' if url_only == 'add' else '')
        else:
            vernames    = modelset.model._meta.verbose_name, modelset.model._meta.verbose_name_plural
            addicon     = u'%sadmin/img/icon_addlink.gif' % settings.STATIC_URL
            result      = u'<a href="%s" title="show related &laquo;%s&raquo;">%s</a> (%d)' \
                          % (link, vernames[1], vernames[1], modelset.count())
            result      = u'<nobr>%s&nbsp;<a href="%sadd/" title="create related &laquo;%s&raquo;">'\
                          u'<img src="%s"></a></nobr>' % (result, link, vernames[0], addicon) \
                          if with_add_link else result

        return result
    link.short_description  = '%s list' % name
    link.allow_tags         = True
    return link

class FkeyLinkName(object):
    """Object return full revers urlname by postfix only"""

    def __init__(self, opts):
        self.opts = opts

    def __getattr__(self, name):
        return 'admin:%s_%s_%s' % (self.opts.app_label, self.opts.module_name, name)

class FkeyListAdmin(admin.ModelAdmin):
    # fkey_list functionality
    def queryset(self, request):
        """Add fkey id filter from request if exists"""
        qs = super(FkeyListAdmin, self).queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            qs = qs.filter(**{request.FKEY_LIST['fkey_name'].__str__():request.FKEY_LIST['id']})
        return qs

    def fkey_view(self, request, *args, **kwargs):
        """Common method for all fkey_list views"""
        view_name = kwargs['view_name']

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
            raise Exception, 'FkeyList: field "%s" does not exist in model "%s"' \
                             % (args[0], self.model._meta.module_name)
        parent = getattr(self.model, args[0]).field.rel.to.objects.filter(pk=args[1])
        if parent.count() != 1:
            raise Exception, 'FkeyList: fkey "%s" #%s for "%s" model does not exist' \
                             % (args[0], args[1], self.model._meta.module_name)
        parent = parent[0]

        request.FKEY_LIST = {
            'fkey_name':    args[0],
            'id':           args[1],
            'item':         parent,
            'item_link':    reverse('admin:%s_%s_change' % (parent.__class__._meta.app_label, 
                                                            parent.__class__._meta.module_name), 
                                    None, (args[1],), {}),
            'list_link':    self.fkeys_link(args[0]),
            'link_name':    FkeyLinkName(self.model._meta),
        }

        # default and fkey links dependencies
        link_name, link_args = request.FKEY_LIST['link_name'], args[:2]
        link_deps = {
            reverse(link_name.changelist): reverse(link_name.changelist_fkeylist, None, args[:2]),
            reverse(link_name.add): reverse(link_name.add_fkeylist, None, args[:2]),
        }

        # clean ex data and get response
        args = tuple(args[2:])
        del kwargs['view_name']
        response = getattr(self, view_name)(request, *args, **kwargs)

        # try to return fkey location in HttpResponseRedirect instead original
        location = isinstance(response, HttpResponseRedirect) and response['Location'].split('?', 1)
        if location and location[0] in link_deps:
            response['Location'] = link_deps[location[0]] + ('?%s' % location[1] if location.__len__() > 1 else '')

        return response

    def get_urls(self):
        """Extends urls by nodein routes to nodein_view with view_name param"""
        from django.conf.urls import patterns, url
        from django.utils.functional import update_wrapper

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = patterns('',
            url(r'^([\w\d\_]+)-(\d+)/$', wrap(self.fkey_view), 
                {'view_name': 'changelist_view'}, name='%s_%s_changelist_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/add/$', wrap(self.fkey_view), 
                {'view_name': 'add_view'}, name='%s_%s_add_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/history/$', wrap(self.fkey_view), 
                {'view_name': 'history_view'}, name='%s_%s_history_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/delete/$', wrap(self.fkey_view), 
                {'view_name': 'delete_view'}, name='%s_%s_delete_fkeylist' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/$', wrap(self.fkey_view), 
                {'view_name': 'change_view'}, name='%s_%s_change_fkeylist' % info),
        )

        urls = super(FkeyListAdmin, self).get_urls()
        return urlpatterns + urls

    def fkeys_link(self, fkey_name):
        """Admin link to fkeys list"""
        return reverse('admin:%s_%s_changelist' \
                       % (getattr(self.model, fkey_name).field.rel.to._meta.app_label, 
                          getattr(self.model, fkey_name).field.rel.to._meta.module_name,), 
                       None, (), {})

    def get_form(self, request, obj=None, **kwargs):
        """preset foreign key value if FKEY_LIST"""
        form = super(FkeyListAdmin, self).get_form(request, obj, **kwargs)
        if obj is None and hasattr(request, 'FKEY_LIST') \
                       and form.base_fields.has_key(request.FKEY_LIST['fkey_name']):
            form.base_fields[request.FKEY_LIST['fkey_name']].initial = request.FKEY_LIST['id']
        return form

class FkeyMpttAdmin(FkeyListAdmin):
    def queryset(self, request):
        """Add fkey left and right filter from request if exists"""

        qs = super(FkeyListAdmin, self).queryset(request)
        if hasattr(request, 'FKEY_LIST'):
            item = request.FKEY_LIST['item']
            opts = item._mptt_meta
            filters = {opts.tree_id_attr: getattr(item, opts.tree_id_attr),}
            filters['%s__gt' % opts.left_attr] = getattr(item, opts.left_attr)
            filters['%s__lt' % opts.left_attr] = getattr(item, opts.right_attr)
            qs = qs.filter(**filters)

        return qs