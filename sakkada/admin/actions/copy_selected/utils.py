# -- coding: utf-8 --
import mimetypes
from collections import OrderedDict, defaultdict
from operator import attrgetter
from django.db import connections, models, transaction
from django.db.models.deletion import get_candidate_relations_to_delete
from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.utils import six
from django.utils.html import format_html
from django.utils.text import capfirst
from django.utils.encoding import force_text


def get_copied_objects(objs, opts, user, admin_site, using):
    """
    Find all objects related to ``objs`` that should also be copied. ``objs``
    must be a homogeneous iterable of objects (e.g. a QuerySet).

    Returns a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.
    """
    collector = NestedObjects(using=using)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta

        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
                                   force_text(obj))

        if has_admin:
            try:
                admin_url = reverse('%s:%s_%s_change'
                                    % (admin_site.name,
                                       opts.app_label,
                                       opts.model_name),
                                    None, (quote(obj._get_pk_val()),))
            except NoReverseMatch:
                # Change url doesn't exist -- don't display link to edit
                return no_edit_link

            p = '%s.%s' % (opts.app_label,
                           get_permission_codename('add', opts))
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return format_html(u'{}: <a href="{}">{}</a>',
                               capfirst(opts.verbose_name),
                               admin_url,
                               obj)
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return no_edit_link

    to_copy = collector.nested(format_callback)

    return to_copy, perms_needed, collector


class Collector(object):
    def __init__(self, using):
        self.using = using
        # Initially, {model: {instances}}, later values become lists.
        self.data = {}

        # Tracks copy-order dependency for databases without transactions
        # or ability to defer constraint checks. Only concrete model classes
        # should be included, as the dependencies exist only between actual
        # database tables; proxy models are represented here by their concrete
        # parent.
        self.dependencies = {}  # {model: {models}}

    def add(self, objs, source=None):
        """
        Adds 'objs' to the collection of objects to be copied.
        Returns a list of all objects that were not already collected.
        FIXED: removed reverse_dependency, nullable kwargs.
        """
        if not objs:
            return []
        new_objs = []
        model = objs[0].__class__
        instances = self.data.setdefault(model, set())
        for obj in objs:
            if obj not in instances:
                new_objs.append(obj)
        instances.update(new_objs)
        # Nullable relationships can be ignored -- they are nulled out before
        # deleting, and therefore do not affect the order in which objects have
        # to be deleted.
        if source is not None:
            self.dependencies.setdefault(
                source._meta.concrete_model, set()).add(model._meta.concrete_model)
        return new_objs

    def get_all_related_fields(self, objs, source=None, source_attr=None):
        # Related objects will be found by meta.get_fields()
        # and meta.virtual_fields.
        model = objs[0].__class__
        return {
            'related_objects': get_candidate_relations_to_delete(model._meta),
            'virtual_fields': [f for f in model._meta.virtual_fields
                               if hasattr(f, 'bulk_related_objects')],
        }

    def related_objects(self, related, objs):
        """
        Gets a QuerySet of objects related to ``objs`` via the relation ``related``.
        """
        return related.related_model._base_manager.using(self.using).filter(
            **{"%s__in" % related.field.name: objs,}
        )

    def collect(self, objs, source=None, source_attr=None):
        """
        Adds 'objs' to the collection of objects to be copied as well as all
        parent instances. 'objs' must be a homogeneous iterable collection of
        model instances (e.g. a QuerySet).

        If the call is the result of a cascade, 'source' should be the model
        that caused it.

        FIXED: removed reverse_dependency, nullable, collect_related kwargs.
        """
        new_objs = self.add(objs, source)
        if not new_objs:
            return

        model = new_objs[0].__class__

        related = self.get_all_related_fields(new_objs, source=source,
                                              source_attr=source_attr)
        for related_object in related['related_objects']:
            field = related_object.field
            batches = self.get_connection_batches(new_objs, field)
            for batch in batches:
                sub_objs = self.related_objects(related_object, batch)
                if sub_objs:
                    self.collect(sub_objs, source=field.rel.to,
                                 source_attr=field.name)

        for field in related['virtual_fields']:
            gfks = [i for i in field.rel.to._meta.virtual_fields
                    if (i.ct_field == field.content_type_field_name
                        and i.fk_field == field.object_id_field_name)]
            source_attr = gfks and gfks[0].name or field.rel.related_name

            # Its something like generic foreign key.
            sub_objs = field.bulk_related_objects(new_objs, self.using)
            self.collect(sub_objs, source=model, source_attr=source_attr)

    def get_connection_batches(self, objs, field):
        """
        Returns the objs in suitably sized batches for the used connection.
        """
        conn_batch_size = max(
            connections[self.using].ops.bulk_batch_size([field.name], objs), 1)
        if len(objs) > conn_batch_size:
            return [objs[i:i + conn_batch_size]
                    for i in range(0, len(objs), conn_batch_size)]
        else:
            return [objs]

    def instances_with_model(self):
        for model, instances in six.iteritems(self.data):
            for obj in instances:
                yield model, obj

    def sort(self):
        sorted_models = []
        concrete_models = set()
        models = list(self.data)
        while len(sorted_models) < len(models):
            found = False
            for model in models:
                if model in sorted_models:
                    continue
                dependencies = self.dependencies.get(model._meta.concrete_model)
                if not (dependencies and dependencies.difference(concrete_models)):
                    sorted_models.append(model)
                    concrete_models.add(model._meta.concrete_model)
                    found = True
            if not found:
                return
        self.data = OrderedDict((model, self.data[model])
                                for model in sorted_models)

    def save_object(self, instance, old_pk_value, old_new_pk_registry):
        instance.save()
        old_new_pk_registry[instance._meta.model].update({
            old_pk_value: instance.pk,
        })
        return instance

    def _get_uploaded_file_from_path(self, path, quiet=True):
        try:
            with open(path, 'rb') as image:
                file = SimpleUploadedFile(image.name, image.read())
                file.content_type = mimetypes.guess_type(path)[0]
        except IOError as e:
            if not quiet:
                raise
            file = None
        return file

    def get_object_fields(self, instance, old_new_pk_registry):
        """Get all fields of model that should be processed."""
        return {
            'fields': instance._meta.get_fields(),
            'virtual_fields': instance._meta.virtual_fields,
        }

    def copy_object(self, instance, old_new_pk_registry, commit=True):
        fields = self.get_object_fields(instance, old_new_pk_registry)

        # save old pk value and set pk to None (save as new)
        old_pk_value = instance.pk
        instance.pk = None

        for f in fields['fields']:
            if isinstance(f, models.FileField):
                oldval = getattr(instance, f.name, None)
                if oldval:
                    newval = self._get_uploaded_file_from_path(oldval.path)
                    newval and setattr(instance, f.name, newval)
            elif isinstance(f, models.ForeignKey):
                if f.rel.to in old_new_pk_registry:
                    oldval = getattr(instance, f.name, None)
                    newval = old_new_pk_registry[f.rel.to].get(
                        oldval.pk if oldval else None, None
                    )
                    if newval:
                        newval = f.rel.to.objects.get(pk=newval)
                        setattr(instance, f.name, newval)

        for f in fields['virtual_fields']:
            if isinstance(f, GenericForeignKey):
                oldval = getattr(instance, f.name, None)
                newval = oldval and old_new_pk_registry.get(oldval._meta.model,
                                                            {}).get(oldval.pk, None)
                if newval:
                    newval = oldval._meta.model.objects.get(pk=newval)
                    setattr(instance, f.name, newval)

        if commit:
            newitem = self.save_object(instance, old_pk_value,
                                       old_new_pk_registry)

        return newitem, old_pk_value

    def copy(self):
        # sort instance collections and models
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))
        self.sort()

        old_new_pk_registry, copied_objects = {}, []
        with transaction.atomic(using=self.using, savepoint=True):
            # TODO: delete any created if exception to remove created files
            items = reversed(self.data.items())
            for item in items:
                savepoint = transaction.savepoint()
                old_new_pk_registry.setdefault(item[0], {})
                for i in item[1]:
                    item = self.copy_object(i, old_new_pk_registry)
                    copied_objects.append(item)
                transaction.savepoint_commit(savepoint)

        return copied_objects


class NestedObjects(Collector):
    def __init__(self, *args, **kwargs):
        super(NestedObjects, self).__init__(*args, **kwargs)
        self.edges = {} # {from_instance: [to_instances]}
        self.model_count = defaultdict(int)

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
            self.model_count[obj._meta.verbose_name_plural] += 1
        return super(NestedObjects, self).collect(objs, source_attr=source_attr, **kwargs)

    def related_objects(self, related, objs):
        qs = super(NestedObjects, self).related_objects(related, objs)
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
