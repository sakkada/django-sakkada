from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, \
                        HttpResponseForbidden, HttpResponseNotFound
from django.conf import settings
from django.utils import simplejson
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.views.main import ChangeList
from mptt.exceptions import InvalidMove

TREE_ADMIN_MEDIA = '%s%s' % (settings.STATIC_URL, 'admin/mptt_tree/')

def ajax_boolean_cell(item, attr, text=''):
    text = text and '&nbsp;(%s)' % unicode(text)
    cbox = getattr(item, attr) and ' checked="checked"' or ''
    cbox = u'<div id="wrap_%s_%d">' \
            u'<input type="checkbox"%s onclick="return inplace_toggle_boolean(%d, \'%s\')"; />' \
             u'%s</div>' % (attr, item.id, cbox, item.id, attr, text)
    return cbox

def ajax_boolean(attr, short_description = ''):
    """
    Convenience function: Assign the return value of this method to a variable
    of your ModelAdmin class and put the variable name into list_display.
    Example:
        class SomeTreeAdmin(MpttTreeAdmin):
            list_display = ('__unicode__', 'active_toggle')
            ajax_active = ajax_boolean('active', _('is active'))
    """
    def _fn(self, item):
        return ajax_boolean_cell(item, attr)
    _fn.allow_tags = True
    _fn.short_description = short_description or attr
    _fn.editable_boolean_field = attr
    return _fn

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

    opts = cls._mptt_meta
    for p_id, parent_id, level in cls.objects.order_by(opts.tree_id_attr, opts.left_attr) \
                                             .values_list("pk", "%s_id" % opts.parent_attr, "level"):
        all_nodes['sort'].append(p_id)
        all_nodes[p_id] = {'id': p_id, 'children' : [], 'descendants' : [], 
                           'parent' : parent_id, 'level': level,}
        if parent_id:
            all_nodes[parent_id]['children'].append(p_id)
            add_as_descendant(parent_id, p_id)

    return all_nodes

class TreeChangeList(ChangeList):
    "TreeEditor ChangeList always need to order by 'tree_id' and 'lft'."
    def get_query_set(self, request):
        qs = super(TreeChangeList, self).get_query_set(request)
        if isinstance(self.model_admin, MpttTreeAdmin):
            return qs.order_by('tree_id', 'lft')
        return qs

class AjaxBoolAdmin(admin.ModelAdmin):
    class Media:
        js = (
            settings.STATIC_URL + 'admin/js/jquery.min.js',
            settings.STATIC_URL + 'admin/js/jquery.init.js',
            settings.STATIC_URL + 'admin/jquery/init.js',
            settings.STATIC_URL + 'admin/jquery/jquery.cookie.js',
            TREE_ADMIN_MEDIA + 'scripts.js',
        )

        css = {'all': [TREE_ADMIN_MEDIA + 'styles.css',]}

    def __init__(self, *args, **kwargs):
        """AjaxBool Admin initialisation"""
        super(AjaxBoolAdmin, self).__init__(*args, **kwargs)
        self.list_display = list(self.list_display)
        opts = self.model._meta
        self.change_list_template = [
            'admin/mptt_tree/%s/%s/ajax_change_list.html' % (opts.app_label, opts.object_name.lower()),
            'admin/mptt_tree/%s/ajax_change_list.html' % opts.app_label,
            'admin/mptt_tree/ajax_change_list.html',
        ]

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        """Handle the changelist view, add ajax_boolean functionality."""

        # handle common AJAX requests
        if request.is_ajax():
            cmd = request.POST.get('__cmd')
            if cmd == 'toggle_boolean':
                return self._toggle_boolean(request)
            else:
                return HttpResponseBadRequest('Oops. AJAX request not understood.')

        extra_context = extra_context or {}
        extra_context['TREE_ADMIN_MEDIA'] = TREE_ADMIN_MEDIA
        return super(AjaxBoolAdmin, self).changelist_view(request, extra_context, *args, **kwargs)

    # common methods
    def _collect_editable_booleans(self):
        """
        Collect all fields marked as editable booleans. We do not
        want the user to be able to edit arbitrary fields by crafting
        an AJAX request by hand.
        """
        if hasattr(self, '_ajax_editable_booleans'):
            return
        self._ajax_editable_booleans = {}

        for field in self.list_display:
            # The ajax_boolean return value has to be assigned to the ModelAdmin class
            item = getattr(self.__class__, field, None)
            if not item: continue
            attr = getattr(item, 'editable_boolean_field', None)
            if attr:
                _fn = lambda attr: (lambda self, item: [ajax_boolean_cell(item, attr)])
                _fn = _fn(attr)
                result_func = getattr(item, 'editable_boolean_result', _fn)
                self._ajax_editable_booleans[attr] = result_func

    def _toggle_boolean(self, request):
        """Handle an AJAX ajax_boolean request"""
        try:
            item_id = int(request.POST.get('item_id', None))
            attr = str(request.POST.get('attr', None))
        except:
            return HttpResponseBadRequest("Malformed request")

        if not request.user.is_staff:
            return HttpResponseForbidden("You do not have permission to access this page")

        self._collect_editable_booleans()

        if not self._ajax_editable_booleans.has_key(attr):
            return HttpResponseBadRequest("not a valid attribute %s" % attr)

        try:
            obj = self.model._default_manager.get(pk=item_id)
        except self.model.DoesNotExist:
            return HttpResponseNotFound("Object does not exist")

        try:
            before_data = self._ajax_editable_booleans[attr](self, obj)
            setattr(obj, attr, not getattr(obj, attr))
            obj.save()

            # Construct html snippets to send back to client for status update
            data = self._ajax_editable_booleans[attr](self, obj)
        except Exception, e:
            return HttpResponseServerError("Unable to toggle %s on %s" % (attr, obj))

        # Weed out unchanged cells to keep the updates small. This assumes
        # that the order a possible get_descendents() returns does not change
        # before and after toggling this attribute. Unlikely, but still...
        d = []
        for a, b in zip(before_data, data):
            if a != b:
                d.append(b)

        return HttpResponse(simplejson.dumps(d), mimetype="application/json")

class MpttTreeAdmin(AjaxBoolAdmin):
    list_per_page = 999

    def __init__(self, *args, **kwargs):
        super(AjaxBoolAdmin, self).__init__(*args, **kwargs)

        self.list_display = list(self.list_display)
        if 'indented_short_title' not in self.list_display:
            if self.list_display[0] == 'action_checkbox':
                self.list_display[1] = 'indented_short_title'
            else:
                self.list_display[0] = 'indented_short_title'

        opts = self.model._meta
        self.change_list_template = [
            'admin/mptt_tree/%s/%s/tree_change_list.html' % (opts.app_label, opts.object_name.lower()),
            'admin/mptt_tree/%s/tree_change_list.html' % opts.app_label,
            'admin/mptt_tree/tree_change_list.html',
        ]

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

        extra_context = extra_context or {}
        extra_context['TREE_ADMIN_MEDIA'] = TREE_ADMIN_MEDIA
        extra_context['tree_structure'] = mark_safe(simplejson.dumps(_build_tree_structure(self.model)))

        return super(AjaxBoolAdmin, self).changelist_view(request, extra_context, *args, **kwargs)

    def get_changelist(self, request, **kwargs):
        """Returns the ChangeList class for use on the changelist page."""
        return TreeChangeList

    def indented_short_title(self, item):
        """
        Generate a short title for a page, indent it depending 
        on the page's depth in the hierarchy.
        """
        r = '<span onclick="return page_tree_handler(\'%d\');" id="page_marker-%d"' \
            ' class="page_marker" style="width: 12px;" level="%d">&nbsp;</span>' \
            % (item.id, item.id, item.level)
        if hasattr(item, 'get_absolute_url'):
            r = '<input type="hidden" class="medialibrary_file_path" value="%s">%s' \
                % (item.get_absolute_url(), r)
        if hasattr(self, 'indented_short_title_text'):
            r = '%s<span class="indented_short_title">%s</span>' \
                % (r, self.indented_short_title_text(item))
        else:
            r = '%s<span class="indented_short_title">%s</span>' \
                % (r, getattr(item, 'short_title', item.__unicode__)())
        return mark_safe(r)
    indented_short_title.short_description = _('title')
    indented_short_title.allow_tags = True

    def _move_node(self, request):
        position = request.POST.get('position')
        if position in ('last-child', 'first-child', 'left', 'right'):
            cut_item = self.model._tree_manager.get(pk=request.POST.get('cut_item'))
            pasted_on = self.model._tree_manager.get(pk=request.POST.get('pasted_on'))
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
        actions.append(u'<a href="#" onclick="return cut_item(\'%s\', this)" ' \
                       u'title="%s">move</a>&nbsp;&nbsp;&nbsp;' % (page.pk, _('Cut')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'left\')" ' \
                       u'title="%s">&#9650;</a>' % (page.pk, _('Insert before (left)')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'right\')" ' \
                       u'title="%s">&#9660;</a>&nbsp;&nbsp;' % (page.pk, _('Insert after (right)')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'first-child\')" ' \
                       u'title="%s">&#x2198;</a>' % (page.pk, _('Insert as first child')))
        actions.append(u'<a class="paste_target" href="#" onclick="return paste_item(\'%s\', \'last-child\')" ' \
                       u'title="%s">&#x21d8;</a>' % (page.pk, _('Insert as last child')))
        actions.append(u'</nobr>')
        return actions

    def actions_column(self, page):
        return u' '.join(self._actions_column(page))
    actions_column.allow_tags = True
    actions_column.short_description = _('actions')