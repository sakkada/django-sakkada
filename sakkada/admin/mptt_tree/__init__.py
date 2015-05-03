import json
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.admin.views.main import ChangeList
from django.contrib import admin
from django.conf import settings
from django.forms.widgets import Media
from mptt.exceptions import InvalidMove


def _build_tree_structure(queryset):
    """
    Build an in-memory representation of the whole item tree, trying to keep
    database accesses down to a minimum. The returned dictionary looks like
    this (as json dump):
        {"6": {"id": 6, "children": [7, 8, 10], "parent": null, "descendants": [7, 12, 13, 8, 10]},
         "7": {"id": 7, "children": [12], "parent": 6, "descendants": [12, 13]},
         "8": {"id": 8, "children": [], "parent": 6, "descendants": []},
         ...
    """
    all_nodes = {'order':[], 'nodes': {},}
    def add_as_descendant(n, p):
        all_nodes['nodes'][n]['descendants'].append(p)
        n_parent_id = all_nodes['nodes'][n]['parent']
        if n_parent_id:
            add_as_descendant(n_parent_id, p)

    opts, qall = queryset.model._mptt_meta, queryset.model.objects.all()
    for pk, parent_id, lvl in qall.values_list("pk", "%s_id" % opts.parent_attr,
                                               opts.level_attr):
        all_nodes['order'].append(pk)
        all_nodes['nodes'][pk] = {'id': pk, 'parent': parent_id, 'level': lvl,
                                    'children': [], 'descendants': [],}
        if parent_id:
            all_nodes['nodes'][parent_id]['children'].append(pk)
            add_as_descendant(parent_id, pk)

    return all_nodes


class TreeChangeList(ChangeList):
    """TreeEditor ChangeList always need to order by 'tree_id' and 'lft'."""
    def get_queryset(self, request):
        qs = super(TreeChangeList, self).get_queryset(request)
        if isinstance(self.model_admin, MpttTreeAdmin):
            return qs.order_by(qs.model._mptt_meta.tree_id_attr,
                               qs.model._mptt_meta.left_attr)
        return qs


class MpttTreeAdmin(admin.ModelAdmin):
    list_per_page = 999
    mptt_tree_parent_template = None

    @property
    def media(self):
        # media as a propery, because if this module used as an app,
        # call of function "static" in __init__.py (class Media definition)
        # cause an "django.core.AppRegistryNotReady: Apps aren't loaded yet".
        js = '' if settings.DEBUG else '.min'
        js = (
            static('admin/js/jquery%s.js' % js),
            static('admin/js/jquery.init.js'),
            static('admin/js/cookies.js'),
            static('admin/mptt_tree/scripts.js',),
        )
        css = {'all': (static('admin/mptt_tree/styles.css'),)}

        base = getattr(super(MpttTreeAdmin, self), 'media', Media())
        return base + Media(js=js, css=css)

    def __init__(self, *args, **kwargs):
        super(MpttTreeAdmin, self).__init__(*args, **kwargs)

        self.list_display = list(self.list_display)
        if 'indented_short_title' not in self.list_display:
            if self.list_display[0] == 'action_checkbox':
                self.list_display[1] = 'indented_short_title'
            else:
                self.list_display[0] = 'indented_short_title'

        opts = self.model._meta
        self.change_list_template = [
            'admin/mptt_tree/%s/%s/change_list.html' % (opts.app_label,
                                                        opts.model_name,),
            'admin/mptt_tree/%s/change_list.html' % opts.app_label,
            'admin/mptt_tree/change_list.html',
        ]

    def get_queryset(self, request):
        # always order by (tree_id, lft)
        qs = super(MpttTreeAdmin, self).get_queryset(request)
        return qs.order_by(qs.model._mptt_meta.tree_id_attr,
                           qs.model._mptt_meta.left_attr)

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances
        change list/actions page.
        """
        if 'move_node_column' not in self.list_display:
            self.list_display.append('move_node_column')

        # handle AJAX requests
        if request.is_ajax():
            if request.POST.get('__cmd__', None) == 'move_node':
                return self._move_node(request)

        extra_context = extra_context or {}
        extra_context.update({
            'mptt_tree_structure': mark_safe(
                json.dumps(_build_tree_structure(self.get_queryset(request)))
            ),
            'mptt_tree_parent_template': self.mptt_tree_parent_template,
        })

        return super(MpttTreeAdmin, self).changelist_view(request, extra_context,
                                                          *args, **kwargs)

    def get_changelist(self, request, **kwargs):
        """Extent ChangeList class"""
        if not getattr(self, '_changelist_class', None):
            cls = super(MpttTreeAdmin, self).get_changelist(request, **kwargs)
            if cls is not ChangeList:
                class TreeChangeListMixed(TreeChangeList, cls):
                    pass
                self._changelist_class = TreeChangeListMixed
            else:
                self._changelist_class = TreeChangeList

        return self._changelist_class

    def save_moved_node(self, node):
        return node.save()

    def _move_node(self, request):
        if not self.has_change_permission(request, None):
            return HttpResponse('FAIL: You do not have permissions')

        position = request.POST.get('position')
        if position in ('last-child', 'first-child', 'left', 'right'):
            try:
                cut_item = self.model._tree_manager.get(pk=request.POST.get('cut_item'))
                pasted_on = self.model._tree_manager.get(pk=request.POST.get('pasted_on'))
                self.model._tree_manager.move_node(cut_item, pasted_on, position)
            except (self.model.DoesNotExist, InvalidMove) as e:
                return HttpResponse('FAIL: ' + e.__str__())
            # Ensure that model save has been run
            source = self.model._tree_manager.get(pk=cut_item.pk)
            self.save_moved_node(source)
            tree_structure = mark_safe(json.dumps(
                _build_tree_structure(self.get_queryset(request))
            ))
            return HttpResponse('OK' + tree_structure)

        return HttpResponse('FAIL: ' + position)

    def indented_short_title(self, item):
        """
        Generate a short title for a node, indent it depending
        on the node's depth in the hierarchy.
        """
        r = ('<span class="mtree_node_indent">%s</span>'
             '<span data-item="%d" id="mtree_node_marker-%d" level="%d"'
             ' class="mtree_node_marker mtree_node_leaf">&nbsp;</span>'
             % ('.&nbsp;&nbsp;&nbsp;' * item.level, item.id, item.id, item.level,))
        if hasattr(self, 'indented_short_title_text'):
            r = ('%s<span class="indented_short_title">%s</span>'
                 % (r, self.indented_short_title_text(item),))
        else:
            r = ('%s<span class="indented_short_title">%s</span>'
                 % (r, getattr(item, 'short_title', item.__unicode__)(),))
        return mark_safe(r)
    indented_short_title.short_description = _('title')
    indented_short_title.allow_tags = True

    def move_node_column(self, node):
        action = (u'<a class="mtree_paste_target" href="#"'
                  u' data-item="%s" data-position="%s" title="%s">%s</a>')
        actions = [
            u'<nobr>',
            (u'<a href="#" data-item="%s" class="mtree_cut_item"'
             u' title="%s">&#9668;&#9658;</a>' % (node.pk, _('Cut'),)),
            u'&nbsp;&nbsp;&nbsp;',
            action % (node.pk, 'left', _('Insert before (left)'), u'&#9650;',),
            u'&nbsp;',
            action % (node.pk, 'right', _('Insert after (right)'), u'&#9660;'),
            u'&nbsp;',
            action % (node.pk, 'first-child', _('Insert as first child'), u'&#x2198;'),
            u'</nobr>',
        ]
        return u''.join(actions)
    move_node_column.allow_tags = True
    move_node_column.short_description = _('move')
