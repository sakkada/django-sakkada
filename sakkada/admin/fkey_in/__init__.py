"""
0.0.1 - first release
0.0.2 - added different applications support
0.0.3 - reverse fixed ((args[1]) -> (args[1],))
0.0.4 - added FkeyInMpttAdmin for MpttTree models
0.0.5 - refactor fkey_in_link (change add link to image and show verbose names)

install:
    * no media
    * install templates to your app:
        copy data from _install dir to your app templates,
        change app_name with current application name, or
        change app_name with appname/modelname (create subdir)
    * extends admin model with FkeyInAdmin between admin.ModelAdmin, for example
        class SomeAdmin(FkeyInAdmin, admin.ModelAdmin): pass
    * set links to related changelist_view with fkey_in_link (see below)
        item_link = fkey_in_link('item')

def fkey_in_link(name, model_set=None, fkey_name=None)
    - name:      name of child model
    - model_set: required if related_name value in child model is not default
    - fkey_name: required if foreign key field name is not equal parent model name

!   init FkeyInAdmin instance update admin urls with _fkeyin postfix, that's why
    for use fkey_in_link('model_name') you have to register admin, extended with FkeyInAdmin
    for model with name 'model_name', else catch:
        Caught NoReverseMatch while rendering: Reverse for '[app_name]_[model_name]_changelist_fkeyin'
"""
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.conf import settings

def fkey_in_link(name, model_set=None, fkey_name=None, with_add_link=False):
    def link(self, item, url_only=None):
        modelset    = model_set if model_set else '%s_set' % name
        if not hasattr(item, modelset):
            raise Exception, u'FkeyIn link generater: "%s" does not exist' % modelset
        modelset    = getattr(item, modelset)
        fkeyname    = fkey_name if fkey_name else item._meta.module_name
        link        = u'admin:%s_%s_changelist_fkeyin' % (modelset.model._meta.app_label, modelset.model._meta.module_name)
        link        = reverse(link, None, (fkeyname, item.pk), {})
        if url_only in ['list', 'add']:
            result  = '%s%s' % (link, 'add/' if url_only == 'add' else '')
        else:
            vernames    = modelset.model._meta.verbose_name, modelset.model._meta.verbose_name_plural
            addicon     = u'%simg/admin/icon_addlink.gif' % settings.ADMIN_MEDIA_PREFIX
            result      = u'<a href="%s" title="show related &laquo;%s&raquo;">%s</a> (%d)' % (link, vernames[1], vernames[1], modelset.count())
            result      = u'<nobr>%s&nbsp;<a href="%sadd/" title="create related &laquo;%s&raquo;"><img src="%s"></a></nobr>' % (result, link, vernames[0], addicon) if with_add_link else result
        return result
    link.short_description  = '%s list' % name
    link.allow_tags         = True
    return link

class FkeyInAdmin(admin.ModelAdmin):
    # foreign key in functionality
    def queryset(self, request):
        """Add fkey id filter from request if exists"""
        qs = super(FkeyInAdmin, self).queryset(request)
        if hasattr(request, 'FKEY_IN'):
            qs = qs.filter(**{request.FKEY_IN['module_name'].__str__():request.FKEY_IN['id']})
        return qs

    def fkey_view(self, request, *args, **kwargs):
        """Common method for all nodein views"""
        view_name = kwargs['view_name']
        if not hasattr(self, view_name):
            raise Exception, 'FkeyIn view "%s" does not exist' % view_name

        # check fkey instance
        if not hasattr(self.model, args[0]):
            raise Exception, 'FkeyIn: field "%s" does not exist in model "%s"' % (args[0], self.model._meta.module_name)
        parent = getattr(self.model, args[0]).field.rel.to.objects.filter(pk=args[1])
        if parent.count() != 1:
            raise Exception, 'FkeyIn: fkey "%s" #%s for "%s" model does not exist' % (args[0], args[1], self.model._meta.module_name)
        parent = parent[0]

        request.FKEY_IN = {
            'module_name':  args[0],
            'id':           args[1],
            'item':         parent,
            'item_link':    reverse('admin:%s_%s_change' % (parent.__class__._meta.app_label, parent.__class__._meta.module_name), None, (args[1],), {}),
            'list_link':    self.fkeys_link(args[0]),
        }

        # clean ex data
        args = tuple(args[2:])
        del kwargs['view_name']

        return getattr(self, view_name)(request, *args, **kwargs)

    def get_urls(self):
        """Extends urls by nodein routes to nodein_view with view_name param"""
        from django.conf.urls.defaults import patterns, url
        from django.utils.functional import update_wrapper

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = patterns('',
            url(r'^([\w\d\_]+)-(\d+)/$',                wrap(self.fkey_view), {'view_name': 'changelist_view'}, name='%s_%s_changelist_fkeyin' % info),
            url(r'^([\w\d\_]+)-(\d+)/add/$',            wrap(self.fkey_view), {'view_name': 'add_view'},        name='%s_%s_add_fkeyin' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/history/$',   wrap(self.fkey_view), {'view_name': 'history_view'},    name='%s_%s_history_fkeyin' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/delete/$',    wrap(self.fkey_view), {'view_name': 'delete_view'},     name='%s_%s_delete_fkeyin' % info),
            url(r'^([\w\d\_]+)-(\d+)/(.+)/$',           wrap(self.fkey_view), {'view_name': 'change_view'},     name='%s_%s_change_fkeyin' % info),
        )

        urls = super(FkeyInAdmin, self).get_urls()
        return urlpatterns + urls

    def fkeys_link(self, fkey_name):
        """Admin link to fkeys list"""
        return reverse('admin:%s_%s_changelist' % (getattr(self.model, fkey_name).field.rel.to._meta.app_label, getattr(self.model, fkey_name).field.rel.to._meta.module_name), None, (), {})

    def get_form(self, request, obj=None, **kwargs):
        """preset foreign key value if FKEY_IN"""
        form = super(FkeyInAdmin, self).get_form(request, obj, **kwargs)
        if obj is None and hasattr(request, 'FKEY_IN') and form.base_fields.has_key(request.FKEY_IN['module_name']):
            form.base_fields[request.FKEY_IN['module_name']].initial = request.FKEY_IN['id']
        return form

class FkeyInMpttAdmin(FkeyInAdmin):
    def queryset(self, request):
        """Add fkey left and right filter from request if exists"""

        qs = super(FkeyInAdmin, self).queryset(request)
        if hasattr(request, 'FKEY_IN'):
            item = request.FKEY_IN['item']
            opts = item._meta
            filters = {opts.tree_id_attr: getattr(item, opts.tree_id_attr)}
            filters['%s__gt' % opts.left_attr] = getattr(item, opts.left_attr)
            filters['%s__lt' % opts.left_attr] = getattr(item, opts.right_attr)
            qs = qs.filter(**filters)

        return qs