from django.conf import settings as django_settings
from django.contrib.admin.views.main import ChangeList as ChangeListOriginal
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from mptt.exceptions import InvalidMove
from meta_editor import MetaEditor, FEIN_ADMIN_MEDIA

# ------------------------------------------------------------------------
def _build_tree_structure(cls):
    """
    Build an in-memory representation of the item tree, trying to keep
    database accesses down to a minimum. The returned dictionary looks like
    this (as json dump):

        {"6": {"id": 6, "children": [7, 8, 10], "parent": null, "descendants": [7, 12, 13, 8, 10]},
         "7": {"id": 7, "children": [12], "parent": 6, "descendants": [12, 13]},
         "8": {"id": 8, "children": [], "parent": 6, "descendants": []},
         ...
    """
    all_nodes = {'sort':[]}
    def add_as_descendant(n, p):
        all_nodes[n]['descendants'].append(p)
        n_parent_id = all_nodes[n]['parent']
        if n_parent_id:
            add_as_descendant(n_parent_id, p)

    for p_id, parent_id, level in cls.objects.order_by(cls._meta.tree_id_attr, cls._meta.left_attr).values_list("pk", "%s_id" % cls._meta.parent_attr, "level"):
        all_nodes['sort'].append(p_id)
        all_nodes[p_id] = {'id': p_id, 'children' : [ ], 'descendants' : [ ], 'parent' : parent_id, 'level': level}
        if parent_id:
            all_nodes[parent_id]['children'].append(p_id)
            add_as_descendant(parent_id, p_id)
            
    return all_nodes

# ------------------------------------------------------------------------
# If the ChangeList is used by a TreeEditor, we always need to order by 'tree_id' and 'lft'.
class ChangeList(ChangeListOriginal):
    def get_query_set(self):
        qs = super(ChangeList, self).get_query_set()
        if isinstance(self.model_admin, TreeEditor):
            return qs.order_by('tree_id', 'lft')
        return qs

    """
    # change queryset to select all parents upto root
    def get_results(self, request):
        if isinstance(self.model_admin, TreeEditor):
            clauses = [Q(tree_id=tree_id, lft__lte=lft, rght__gte=rght,) for lft, rght, tree_id in self.query_set.values_list('lft', 'rght', 'tree_id')]
            if clauses:
                self.query_set = self.model._default_manager.filter(reduce(lambda p, q: p|q, clauses))

        return super(ChangeList, self).get_results(request)
    """

# ------------------------------------------------------------------------
class TreeEditor(MetaEditor):
    list_per_page = 999

    def __init__(self, *args, **kwargs):
        super(TreeEditor, self).__init__(*args, **kwargs)

        self.list_display = list(self.list_display)

        if 'indented_short_title' not in self.list_display:
            if self.list_display[0] == 'action_checkbox':
                self.list_display[1] = 'indented_short_title'
            else:
                self.list_display[0] = 'indented_short_title'
        self.list_display_links = ('indented_short_title',)

        opts = self.model._meta
        self.change_list_template = [
            'admin/fein/%s/%s/tree_editor.html' % (opts.app_label, opts.object_name.lower()),
            'admin/fein/%s/tree_editor.html' % opts.app_label,
            'admin/fein/tree_editor.html',
        ]

    def get_changelist(self, request, **kwargs):
        """Returns the ChangeList class for use on the changelist page."""
        return ChangeList

    def indented_short_title(self, item):
        """
        Generate a short title for a page, indent it depending on
        the page's depth in the hierarchy.
        """
        r = '''<span onclick="return page_tree_handler('%d')" id="page_marker-%d" class="page_marker" style="width: 12px;" level="%d">&nbsp;</span>''' % (item.id, item.id, item.level)
        if hasattr(item, 'get_absolute_url'):
            r = '''<input type="hidden" class="medialibrary_file_path" value="%s">%s''' % (item.get_absolute_url(), r)
                
        if hasattr(item, 'short_title'):
            r += '<span class="indented_short_title">%s</span>' % item.short_title()
        else:
            r += '<span class="indented_short_title">%s</span>' % unicode(item)
        return mark_safe(r)
    indented_short_title.short_description = _('title')
    indented_short_title.allow_tags = True

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """
        Handle the changelist view, the django view for the model instances
        change list/actions page.
        """

        if 'actions_column' not in self.list_display:
            self.list_display.append('actions_column')

        # handle common AJAX requests
        if request.is_ajax():
            cmd = request.POST.get('__cmd')
            if cmd == 'toggle_boolean':
                return self._toggle_boolean(request)
            elif cmd == 'move_node':
                return self._move_node(request)
            else:
                return HttpResponseBadRequest('Oops. AJAX request not understood.')

        self._refresh_changelist_caches()
        extra_context = extra_context or {}
        extra_context['FEIN_ADMIN_MEDIA']   = FEIN_ADMIN_MEDIA
        extra_context['tree_structure']     = mark_safe(simplejson.dumps(_build_tree_structure(self.model)))

        return super(TreeEditor, self).changelist_view(request, extra_context, *args, **kwargs)

    def _move_node(self, request):
        cut_item = self.model._tree_manager.get(pk=request.POST.get('cut_item'))
        pasted_on = self.model._tree_manager.get(pk=request.POST.get('pasted_on'))
        position = request.POST.get('position')

        if position in ('last-child', 'first-child', 'left', 'right'):
            try:
                self.model._tree_manager.move_node(cut_item, pasted_on, position)
            except InvalidMove, e:
                return HttpResponse('FAIL: ' + e.__str__())

            # Ensure that model save has been run
            source = self.model._tree_manager.get(pk=request.POST.get('cut_item'))
            source.save(is_moved=True)

            tree_structure = mark_safe(simplejson.dumps(_build_tree_structure(self.model)))
            return HttpResponse('OK' + tree_structure)

        return HttpResponse('FAIL: ' + position)

    def _actions_column(self, page):
        actions = []
        actions.append(u'<nobr>')
        actions.append(u'<a href="#" onclick="return cut_item(\'%s\', this)" title="%s">move</a>&nbsp;&nbsp;&nbsp;' %                           (page.pk, _('Cut')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'left\')" title="%s">&#9650;</a>' %               (page.pk, _('Insert before (left)')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'right\')" title="%s">&#9660;</a>&nbsp;&nbsp;' %  (page.pk, _('Insert after (right)')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'first-child\')" title="%s">&#x2198;</a>' %       (page.pk, _('Insert as first child')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'last-child\')" title="%s">&#x21d8;</a>' %        (page.pk, _('Insert as last child')))
        actions.append(u'</nobr>')
        return actions

    def actions_column(self, page):
        return u' '.join(self._actions_column(page))
    actions_column.allow_tags = True
    actions_column.short_description = _('actions')