import json
from django.conf import settings
from django.contrib import admin
from django.core import checks
from django.forms.widgets import Media
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class BaseTreeAdmin(admin.ModelAdmin):
    list_per_page = 999
    tree_list_parent_template = None
    sortable_by = ()

    @property
    def media(self):
        js = '' if settings.DEBUG else '.min'
        js = (
            'admin/js/vendor/jquery/jquery%s.js' % js,
            'admin/js/jquery.init.js',
            'admin/js/cookies.js',
            'admin/tree_list/scripts.js',
        )
        css = {'all': ('admin/tree_list/styles.css',),}
        return getattr(super(), 'media', Media()) + Media(js=js, css=css)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.list_display = list(self.list_display)
        if 'indented_short_title' not in self.list_display:
            if self.list_display[0] == 'action_checkbox':
                self.list_display[1] = 'indented_short_title'
            else:
                self.list_display[0] = 'indented_short_title'

        self.change_list_template = [
            'admin/tree_list/%s/%s/change_list.html' % (
                self.model._meta.app_label, self.model._meta.model_name,),
            'admin/tree_list/%s/change_list.html' % self.model._meta.app_label,
            'admin/tree_list/change_list.html',
        ]

    def get_level(self, obj):
        raise NotImplementedError

    def move_node(self, request):
        raise NotImplementedError

    def build_tree_structure(self, request):
        raise NotImplementedError

    def save_moved_node(self, node):
        return node.save()

    def add_as_descendant(self, data, parent_pk, pk):
        data['nodes'][parent_pk]['descendants'].append(pk)
        parent_of_parent_pk = data['nodes'][parent_pk]['parent']
        if parent_of_parent_pk:
            self.add_as_descendant(data, parent_of_parent_pk, pk)

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances
        change list/actions page.
        """
        if 'move_node_column' not in self.list_display:
            self.list_display.append('move_node_column')

        # handle AJAX requests
        if request.is_ajax():
            if request.POST.get('tree_list', None) == 'move_node':
                return self.move_node(request)

        extra_context = extra_context or {}
        extra_context.update({
            'tree_list_structure': mark_safe(json.dumps(
                self.build_tree_structure(self.get_queryset(request)))),
            'tree_list_parent_template': self.tree_list_parent_template,
        })

        return super().changelist_view(request, extra_context, *args, **kwargs)

    def indented_short_title(self, item):
        """
        Generate a short title for a node, indent it depending
        on the node's depth in the hierarchy.
        """
        r = ('<span class="tree_list_node_indent">%s</span>'
             '<span data-item="%d" id="tree_list_node_marker-%d" level="%d"'
             ' class="tree_list_node_marker tree_list_node_leaf">&nbsp;</span>'
             % ('.&nbsp;&nbsp;&nbsp;' * self.get_level(item), item.id, item.id,
                self.get_level(item),))
        if hasattr(self, 'indented_short_title_text'):
            r = ('%s<span class="indented_short_title">%s</span>'
                 % (r, self.indented_short_title_text(item),))
        else:
            r = ('%s<span class="indented_short_title">%s</span>'
                 % (r, getattr(item, 'short_title', item.__str__)(),))
        return mark_safe(r)
    indented_short_title.short_description = _('title')

    def move_node_column(self, node):
        action = ('<a class="tree_list_paste_target" href="#"'
                  ' data-item="%s" data-position="%s" title="%s">%s</a>')
        actions = (
            '<nobr>',
            ('<a href="#" data-item="%s" class="tree_list_cut_item" title="%s">'
             '&#9668;&#9658;</a>' % (node.pk, _('Cut'),)),
            '&nbsp;&nbsp;&nbsp;',
            action % (node.pk, 'left', _('Insert before (left)'), '&#9650;',),
            '&nbsp;',
            action % (node.pk, 'right', _('Insert after (right)'), '&#9660;',),
            '&nbsp;',
            action % (node.pk, 'first-child', _('Insert as first child'),
                      '&#x2198;',),
            '</nobr>',
        )
        return mark_safe(''.join(actions))
    move_node_column.short_description = _('move')


class TreeBeardTreeAdmin(BaseTreeAdmin):
    def get_level(self, obj):
        return obj.get_depth() - 1

    def get_queryset(self, request):
        from treebeard.al_tree import AL_Node
        from treebeard.mp_tree import MP_Node
        from treebeard.ns_tree import NS_Node

        # always order by class respective sorting
        qs = super().get_queryset(request)
        if isinstance(qs.model, MP_Node):
            qs = qs.order_by('path')
        elif isinstance(qs.model, NS_Node):
            qs = qs.order_by('tree_id', 'lft')
        elif isinstance(qs.model, AL_Node):
            qs = qs.order_by(*(['parent'] + list(self.model.node_order_by)
                               if qs.model.node_order_by else
                               ['parent', 'sib_order']))
        return qs

    def check(self, **kwargs):
        return super().check(**kwargs) + self._check_dependencies_installed()

    def _check_dependencies_installed(self):
        errors = []
        try:
            import treebeard
        except ImportError:
            errors.append(
                checks.Error(
                    "'django-treebeard' must be installed in order to use"
                    ' the TreeBeardTreeAdmin in admin application.',
                    hint="Install 'django-treebeard' application to use {}"
                         ' class based on TreeBeardTreeAdmin.'.format(
                             type(self).__name__),
                    id='sakkada.E011', obj=self,
                )
            )
        return errors

    def build_tree_structure(self, queryset):
        """
        Build an in-memory representation of the whole item tree,
        trying to keep database accesses down to a minimum.
        The returned dictionary looks like this (as json dump):
            {"6": {"id": 6, "children": [7, 8, 10], "parent": null, "descendants": [7, 12, 13, 8, 10]},
             "7": {"id": 7, "children": [12], "parent": 6, "descendants": [12, 13]},
             "8": {"id": 8, "children": [], "parent": 6, "descendants": []},
            ...
        """
        data = {'order': [], 'nodes': {},}
        items, trail = [(i.pk, i.get_depth() - 1,)
                        for i in queryset.model.objects.all()], []
        for pk, level in items:
            parent_pk = [i for i in trail if i[1] < level][-2:]
            parent_pk = parent_pk[-1][0] if parent_pk else 0

            data['order'].append(pk)
            data['nodes'][pk] = {
                'id': pk,
                'parent': parent_pk,
                'level': level,
                'children': [],
                'descendants': [],
            }
            if parent_pk:
                data['nodes'][parent_pk]['children'].append(pk)
                self.add_as_descendant(data, parent_pk, pk)

            if trail:
                if trail[-1][1] > level:
                    trail = [i for i in trail if i[1] < level]
                elif trail[-1][1] == level:
                    trail.pop(-1)
            trail.append((pk, level,))

        return data

    def move_node(self, request):
        if not self.has_change_permission(request, None):
            return JsonResponse(
                {'error': 'You have not permissions for this operation.'})

        position = request.POST.get('position')
        if position in ('last-child', 'first-child', 'left', 'right',):
            manager = self.model.objects
            try:
                cut_item = manager.get(pk=request.POST.get('cut_item'))
                pasted_on = manager.get(pk=request.POST.get('pasted_on'))
                cut_item.move(pasted_on, position)
            except self.model.DoesNotExist as e:
                return JsonResponse({'error': e.__str__()})
            # Ensure that model save has been run
            source = manager.get(pk=cut_item.pk)
            self.save_moved_node(source)
            return JsonResponse(
                self.build_tree_structure(self.get_queryset(request)))

        return JsonResponse(
            {'error': 'Invalid position value "%s".' % position})


class MpttTreeAdmin(BaseTreeAdmin):
    def get_level(self, obj):
        return getattr(obj, obj._mptt_meta.level_attr)

    def get_queryset(self, request):
        # always order by (tree_id, lft)
        qs = super().get_queryset(request)
        return qs.order_by(qs.model._mptt_meta.tree_id_attr,
                           qs.model._mptt_meta.left_attr)

    def check(self, **kwargs):
        return super().check(**kwargs) + self._check_dependencies_installed()

    def _check_dependencies_installed(self):
        errors = []
        try:
            import mptt
        except ImportError:
            errors.append(
                checks.Error(
                    "'django-mptt' must be installed in order to use"
                    ' the MpttTreeAdmin in admin application.',
                    hint="Install 'django-mptt' application to use {}"
                         ' class based on MpttTreeAdmin.'.format(
                             type(self).__name__),
                    id='sakkada.E012',
                    obj=self,
                )
            )
        return errors

    def build_tree_structure(self, queryset):
        """
        Build an in-memory representation of the whole item tree,
        trying to keep database accesses down to a minimum.
        The returned dictionary looks like this (as json dump):
            {"6": {"id": 6, "children": [7, 8, 10], "parent": null, "descendants": [7, 12, 13, 8, 10]},
            "7": {"id": 7, "children": [12], "parent": 6, "descendants": [12, 13]},
            "8": {"id": 8, "children": [], "parent": 6, "descendants": []},
            ...
        """
        data = {'order':[], 'nodes': {},}
        items = queryset.model.objects.values_list(
            "pk", "%s_id" % queryset.model._mptt_meta.parent_attr,
            queryset.model._mptt_meta.level_attr)

        for pk, parent_id, level in items:
            data['order'].append(pk)
            data['nodes'][pk] = {
                'id': pk,
                'parent': parent_id,
                'level': level,
                'children': [],
                'descendants': [],
            }
            if parent_id:
                data['nodes'][parent_id]['children'].append(pk)
                self.add_as_descendant(data, parent_id, pk)

        return data

    def move_node(self, request):
        from mptt.exceptions import InvalidMove
        if not self.has_change_permission(request, None):
            return JsonResponse(
                {'error': 'You have not permissions for this operation.'})

        position = request.POST.get('position')
        if position in ('last-child', 'first-child', 'left', 'right',):
            manager = self.model._tree_manager
            try:
                cut_item = manager.get(pk=request.POST.get('cut_item'))
                pasted_on = manager.get(pk=request.POST.get('pasted_on'))
                manager.move_node(cut_item, pasted_on, position)
            except (self.model.DoesNotExist, InvalidMove,) as e:
                return JsonResponse({'error': e.__str__()})
            # Ensure that model save has been run
            source = manager.get(pk=cut_item.pk)
            self.save_moved_node(source)
            return JsonResponse(
                self.build_tree_structure(self.get_queryset(request)))

        return JsonResponse(
            {'error': 'Invalid position value "%s".' % position})
