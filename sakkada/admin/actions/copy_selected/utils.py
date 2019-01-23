from collections import defaultdict
from django.db import router
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import capfirst
from sakkada.models.copying import Collector


# original - django.contrib.admin.utils.get_deleted_objects (v2.1.x)
def get_copied_objects(objs, request, admin_site, handlers=None):
    """
    Find all objects related to ``objs`` that should also be copied. ``objs``
    must be a homogeneous iterable of objects (e.g. a QuerySet).

    Return a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.

    Fixed: do not return protected, return collector instead
    """
    try:
        obj = objs[0]
    except IndexError:
        return [], {}, set(), []
    else:
        using = router.db_for_write(obj._meta.model)
    collector = NestedObjects(using=using, handlers=handlers)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        model = obj.__class__
        has_admin = model in admin_site._registry
        opts = obj._meta

        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), obj)

        if has_admin:
            if not admin_site._registry[model].has_add_permission(request):
                perms_needed.add(opts.verbose_name)
            try:
                admin_url = reverse('%s:%s_%s_change'
                                    % (admin_site.name,
                                       opts.app_label,
                                       opts.model_name),
                                    None, (quote(obj.pk),))
            except NoReverseMatch:
                # Change url doesn't exist -- don't display link to edit
                return no_edit_link

            # Display a link to the admin page.
            return format_html('{}: <a href="{}">{}</a>',
                               capfirst(opts.verbose_name),
                               admin_url,
                               obj)
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return no_edit_link

    to_copy = collector.nested(format_callback)

    model_count = {model._meta.verbose_name_plural: len(objs)
                   for model, objs in collector.model_objs.items()}

    return to_copy, model_count, perms_needed, collector


# original - django.contrib.admin.utils.NestedObjects (v2.1.x)
class NestedObjects(Collector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edges = {}  # {from_instance: [to_instances]}
        self.model_objs = defaultdict(set)

    def add_edge(self, source, target):
        self.edges.setdefault(source, []).append(target)

    def collect(self, objs, source=None, source_attr=None, **kwargs):
        for obj in objs:
            if source_attr and not source_attr.endswith('+'):
                related_name = source_attr % {
                    'class': source._meta.model_name,
                    'app_label': source._meta.app_label,
                }
                self.add_edge(getattr(obj, related_name), obj)
            else:
                self.add_edge(None, obj)
            self.model_objs[obj._meta.model].add(obj)
        return super().collect(objs, source=source, source_attr=source_attr,
                               **kwargs)

    def related_objects(self, related, objs):
        qs = super().related_objects(related, objs)
        return qs.select_related(related.field.name)

    def _nested(self, obj, seen, format_callback):
        if obj in seen:
            return []
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            children.extend(self._nested(child, seen, format_callback))
        if format_callback:
            ret = [format_callback(obj)]
        else:
            ret = [obj]
        if children:
            ret.append(children)
        return ret

    def nested(self, format_callback=None):
        """
        Return the graph as a nested list.
        """
        seen = set()
        roots = []
        for root in self.edges.get(None, ()):
            roots.extend(self._nested(root, seen, format_callback))
        return roots
