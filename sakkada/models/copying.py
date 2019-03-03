"""
Functional copy of built-in django.db.models.deletion module (v2.1.x).
Instead of deletion, this module and Collector provide copying functionality.

Default on_copy handlers:
- CASCADE       - copy related objects as deep as possible
- CASCADE_SELF  - copy only realted object it self without "collect_related"
- SET           - set field value for all instances directly to provided value
- SET_NULL      - set field value to null for all instances
- SET_DEFAULT   - set default field value for all instances
- DO_NOTHING    - do nothing (ignore relation)

Relational Field Types by directions:
┌──────────────────┬───────────────────┬─────────────────┐
│Class             │Forward            │Backward         │
├──────────────────┼───────────────────┼─────────────────┤
│ForeingKey        │ForeingKey         │ManyToOneRel     │
├──────────────────┼───────────────────┼─────────────────┤
│OneToOneField     │OneToOneField      │OneToOneRel      │
├──────────────────┼───────────────────┼─────────────────┤
│ManyToManyField   │ManyToManyField(-) │ManyToManyRel(-) │
│{Through Model}   │ManyToOneRel       │ManyToOneRel     │
├──────────────────┼───────────────────┼─────────────────┤
│GenericRelation   │GenericRelation    │GenericRel(-)    │
├──────────────────┼───────────────────┼─────────────────┤
│GenericForeignKey │GenericForeignKey  │-                │
└──────────────────┴───────────────────┴─────────────────┘
(-) - ignorable fields

Relational field Types by relation flags:
┌───────────────────┬───────────┬────────────┬────────────┬─────────────┐
│Class              │one_to_one │one_to_many │many_to_one │many_to_many │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│OneToOneField      │1          │            │            │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│OneToOneRel        │1          │            │            │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│ForeingKey         │           │            │1           │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│ManyToOneRel       │           │1           │            │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│ManyToManyField(-) │           │            │            │1            │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│ManyToManyRel(-)   │           │            │            │1            │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│GenericRelation    │           │1           │            │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│GenericRel(-)      │           │            │1           │             │
├───────────────────┼───────────┼────────────┼────────────┼─────────────┤
│GenericForeignKey  │           │            │1           │             │
└───────────────────┴───────────┴────────────┴────────────┴─────────────┘
(-) - ignorable fields

Copying objects retrieving algorithm:
1.  Parent objects in Multi-Table inherited models are copyied anyway, by
    default handler is CASCADE_SELF. It is strongly not recommended
    to redefine handler for "{parent}_ptr" fields.
2.  Primary key and (ManyToManyField, ManyToManyRel, GenericRel) fields are
    ignored anyway.
    -   Primary key is regenerated while creating new objects.
    -   ManyToManyField and ManyToManyRel fields are processed by their
        Through models (by default only copy relation without deep retrieving)
    -   GenericRel is many_to_one reverse for GenericRelation field and
        it is unusable cause GenericForeignKey is many_to_one field for such
        types of relations.
    Also fields with DO_NOTHING handler and relational fields
    if collect_related=False are ignored too.
3.  By default, only Backward relational (OneToOneRel and ManyToOneRel)
    and GenericRelation (private fields with "bulk_related_objects" method)
    fields have predefined on_copy handler - CASCADE.
    Forward relational fields (ForeignKey, OneToOneField, GenericForeignKey)
    and non-relational fields can be processed only by defining handler
    explicitely.

On copy handlers run while retrieving, not while generating.

Handler key defined by following pattern:
    "{app_label}.{model_name}:{field_name}", where model and field can be only
    forward relational or non-relational fields.

Simple way to understand, how to define key:
    -   for non relational  - field.model:field.name
    -   for relations:
        -   for forward     - field.model:field.name
        -   for backward    - field.remote_field.model:field.remote_field.name

Default on_copy handlers:
-   OneToOneField parent field  - CASCADE_SELF
-   OneToOneRel backward field  - CASCADE
-   ManyToOneRel backward field - CASCADE
"""

import mimetypes
from operator import attrgetter
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models, connections, transaction
from django.db.models import (
    OneToOneField, OneToOneRel,
    ForeignKey, ManyToOneRel,
    ManyToManyField, ManyToManyRel)
from django.contrib.contenttypes.fields import (
    GenericRelation, GenericRel,
    GenericForeignKey)


# on_copy handlers
def CASCADE(collector, field, sub_objs, using, reverse_dependency=False):
    if not field.is_relation:
        return
    if reverse_dependency:
        source = field.model
        source_attr = field.remote_field.name
    else:
        source = field.remote_field.model
        source_attr = field.name

    collector.collect(sub_objs, source=source, source_attr=source_attr,
                      reverse_dependency=reverse_dependency)


def CASCADE_SELF(collector, field, sub_objs, using, reverse_dependency=False):
    if not field.is_relation:
        return
    if reverse_dependency:
        source = field.model
        source_attr = field.remote_field.name
    else:
        source = field.remote_field.model
        source_attr = field.name

    collector.collect(sub_objs, source=source, source_attr=source_attr,
                      reverse_dependency=reverse_dependency,
                      collect_related=False)


def SET(value, deferred=False):
    def set_on_copy(collector, field, sub_objs, using,
                    reverse_dependency=False):
        field_value = value() if callable(value) and not deferred else value
        collector.add_field_update(field, field_value, sub_objs)
    return set_on_copy


def SET_NULL(collector, field, sub_objs, using, reverse_dependency=False):
    collector.add_field_update(field, None, sub_objs)


def SET_DEFAULT(collector, field, sub_objs, using, reverse_dependency=False):
    collector.add_field_update(field, field.get_default(), sub_objs)


def DO_NOTHING(collector, field, sub_objs, using, reverse_dependency=False):
    pass


FORWARD_FIELDS = (
    ForeignKey,
    OneToOneField,
    # ManyToManyField,
    GenericRelation,
    GenericForeignKey,
)
BACKWARD_FIELDS = (
    ManyToOneRel,
    OneToOneRel,
    # ManyToManyRel,
    # GenericRel,
)
IGNORABLE_FIELDS = (
    ManyToManyField,
    ManyToManyRel,
    GenericRel,
)


class Collector:
    field_on_copy = None
    field_updates = None

    def __init__(self, using, handlers=None):
        self.using = using
        self.data = {}  # {model: {instances,},}
        self.field_updates = {}  # {model: {{field}: {value},},}
        self.field_on_copy = handlers or self.field_on_copy or {}
        # {'<app_label>.<model_name>:<forward_field_name>': handler,}

        # Tracks copying-order dependency for ability to defer constraint
        # checks. Only concrete model classes should be included, as
        # the dependencies exist only between actual database tables.
        # Proxy models are represented here by their concrete parent.
        self.dependencies = {}  # {model: {models}}

    def add(self, objs, source=None, reverse_dependency=False):
        """
        Add 'objs' to the collection of objects to be copied. If the call is
        the result of a cascade, 'source' should be the model that caused it.
        Return a list of all objects that were not already collected.
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

        if source is not None:
            if reverse_dependency:
                source, model = model, source
            self.dependencies.setdefault(source._meta.concrete_model,
                                         set()).add(model._meta.concrete_model)
        return new_objs

    def add_field_update(self, field, value, objs):
        """Schedule a field update."""
        self.field_updates.setdefault(field.model, {})[field] = value

    # get candidates methods section
    def get_candidate_relations_forward(self, opts):
        # The candidate relations are forward N-1 and 1-1 relations
        # (ForeingKey, OneToOneField, GenericForeignKey).
        # N-N (i.e. ManyToManyField) relations aren't candidates for copying.
        return [
            f for f in opts.get_fields(include_hidden=True)
            if (f.is_relation and not f.auto_created and
                (f.many_to_one or (f.concrete and f.one_to_one)))
        ]

    def get_candidate_relations_backward(self, opts):
        # The candidate relations are backward 1-N and 1-1 relations
        # (ManyToOneRel, OneToOneRel).
        # N-N (i.e. ManyToManyRel) relations aren't candidates for copying.
        return [
            f for f in opts.get_fields(include_hidden=True)
            if (f.is_relation and f.auto_created and not f.concrete and
                (f.one_to_one or f.one_to_many))
        ]

    def get_candidate_relations_private(self, opts):
        # The candidate relations are N-1 generic (private) relations
        # (GenericRelation).
        # Backward  field is also ignored.
        # 1-N GenericRel relations aren't candidates for copy.
        return [
            f for f in opts.get_fields(include_hidden=True)
            if f in opts.private_fields and hasattr(f, 'bulk_related_objects')
        ]

    def get_key_for_field(self, field):
        """Generates unique key for detecting model+field pair."""
        if field.is_relation:
            if isinstance(field, FORWARD_FIELDS):
                meta = field.model._meta
            elif isinstance(field, BACKWARD_FIELDS):
                meta, field = field.remote_field.model._meta, field.remote_field
        else:
            meta = field.model._meta
        return '{}.{}:{}'.format(meta.app_label, meta.model_name, field.name)

    # retrieving forward and backward relations section
    def get_forward_relations(self, objs, field):
        """
        Get a list of objects for forward relational field.
        Used instead of direct attr getting for recreate new instances
        in memory. In case of existing objects using, some negative side
        effects take place, e.g. not saving new id values.

        Method should works like:
            return [getattr(obj, field.name) for obj in objs]
        But with re-instantiation all entire set.
        """
        if not objs:
            return []

        model = field.remote_field.model
        values = [getattr(obj, field.name, None) for obj in objs]
        values = {obj.pk for obj in values if obj}
        result = []

        batches = self.get_connection_batches(values, field)
        for batch in batches:
            sub_objs = model._base_manager.using(self.using).filter(
                **{'%s__in' % model._meta.pk.name: batch,}
            )
            result += list(sub_objs)

        return result

    def get_backward_relations(self, objs, field):
        batches = self.get_connection_batches(objs, field.remote_field)
        result = []
        for batch in batches:
            sub_objs = self.related_objects(field, batch)
            result += list(sub_objs)

        return result

    def get_connection_batches(self, objs, field):
        """
        Return the objs in suitably sized batches for the used connection.
        """
        conn_batch_size = max(
            connections[self.using].ops.bulk_batch_size([field.name], objs), 1)
        if len(objs) > conn_batch_size:
            return [objs[i:i + conn_batch_size]
                    for i in range(0, len(objs), conn_batch_size)]
        else:
            return [objs]

    def related_objects(self, related, objs):
        """
        Get a QuerySet of objects related to `objs` via the relation `related`.
        """
        return related.related_model._base_manager.using(self.using).filter(
            **{'%s__in' % related.field.name: objs}
        )

    def collect(self, objs, source=None, collect_related=True,
                source_attr=None, reverse_dependency=False):
        """
        Add 'objs' to the collection of objects to be copied as well as all
        parent instances. 'objs' must be a homogeneous iterable collection of
        model instances (e.g. a QuerySet). If 'collect_related' is True,
        related objects will be handled by their respective on_copy handler.

        If the call is the result of a cascade, 'source' should be the model
        that caused.

        If 'reverse_dependency' is True, 'source' will be copied before the
        current model, rather than after.
        """
        new_objs = self.add(objs, source=source,
                            reverse_dependency=reverse_dependency)
        if not new_objs:
            return

        model = new_objs[0].__class__

        CANDIDATES = {
            'parents': model._meta.concrete_model._meta.parents.values(),
            'forward': self.get_candidate_relations_forward(model._meta),
            'backward': self.get_candidate_relations_backward(model._meta),
            'private': self.get_candidate_relations_private(model._meta),
        }

        for field in model._meta.get_fields(include_hidden=True):
            # ManyToManyField and ManyToManyRel and GenericRel are ignored
            if ((not field.is_relation and field.primary_key) or
                    isinstance(field, IGNORABLE_FIELDS)):
                continue

            key = self.get_key_for_field(field)
            on_copy = self.field_on_copy.get(key, None)

            # Parents OneToOneField relations (forward 1-1).
            # Recursively collect concrete model's parent models (Multi
            # Table Inherited models, collect by "{model}_ptr" fields).
            # Parent objects will be created first, before inherited.
            # Default handler is CASCADE_SELF.
            if field in CANDIDATES['parents']:
                parent_objs = self.get_forward_relations(new_objs, field)
                on_copy = on_copy or CASCADE_SELF
                on_copy(self, field, parent_objs, self.using,
                        reverse_dependency=True)

            if (on_copy == DO_NOTHING or
                    (not collect_related and field.is_relation)):
                continue

            # Forward OneToOneField, ForeingKey or GenericForeignKey fields
            # (forward 1-1, N-1).
            # There is no default handler value, they are ignored by default.
            if field in CANDIDATES['forward'] and on_copy:
                related_objs = self.get_forward_relations(new_objs, field)
                on_copy(self, field, related_objs, self.using,
                        reverse_dependency=True)

            # Backward OneToOneRel and ManyToOneRel fields (backward 1-1, 1-N).
            # Default handler is CASCADE.
            elif field in CANDIDATES['backward']:
                on_copy = on_copy or CASCADE
                sub_objs = self.get_backward_relations(new_objs, field)
                on_copy(self, field.remote_field, sub_objs, self.using,
                        reverse_dependency=False)

            # GenericRelation with "bulk_related_objects" (1-N)
            # Default handler is CASCADE.
            elif field in CANDIDATES['private']:
                # It's something like generic foreign key.
                sub_objs = field.bulk_related_objects(new_objs, self.using)
                on_copy = on_copy or CASCADE
                on_copy(self, field, sub_objs, self.using,
                        reverse_dependency=False)

            # Any non-relational field
            # There is no default handler value, they are ignored by default.
            elif not field.is_relation and on_copy:
                on_copy(self, field, None, self.using, reverse_dependency=True)

    # generating section
    def sort(self):
        """Sort collected objects by relations dependencies."""
        sorted_models = []
        concrete_models = set()
        models = list(self.data)
        while len(sorted_models) < len(models):
            found = False
            for model in models:
                if model in sorted_models:
                    continue
                deps = self.dependencies.get(model._meta.concrete_model)
                if not (deps and deps.difference(concrete_models)):
                    sorted_models.append(model)
                    concrete_models.add(model._meta.concrete_model)
                    found = True
            if not found:
                return
        self.data = {model: self.data[model] for model in sorted_models[::-1]}

    def get_uploaded_file_from_path(self, path, quiet=True):
        try:
            with open(path, 'rb') as image:
                file = SimpleUploadedFile(image.name, image.read())
                file.content_type = mimetypes.guess_type(path)[0]
        except IOError:
            if not quiet:
                raise
            file = None
        return file

    def save_instance(self, instance, old_pk_value, old_new_pk_registry):
        instance.save()
        old_new_pk_registry[instance._meta.model].update({
            old_pk_value: instance.pk,
        })
        return instance

    def copy_object(self, instance, old_new_pk_registry, commit=True):
        # save old pk value and set pk to None (save as new)
        old_pk_value = instance.pk
        instance.pk = None

        for field in instance._meta.get_fields(include_hidden=True):
            if isinstance(field, models.FileField):
                oldval = getattr(instance, field.name, None)
                if oldval:
                    newval = self.get_uploaded_file_from_path(oldval.path)
                    newval and setattr(instance, field.name, newval)
            elif isinstance(field, (models.ForeignKey,
                                    models.OneToOneField, GenericForeignKey)):
                oldval = getattr(instance, field.name, None)
                newval = oldval and old_new_pk_registry.get(
                    oldval._meta.model, {}).get(oldval.pk, None)
                if newval:
                    newval = oldval._meta.model.objects.get(pk=newval)
                    setattr(instance, field.name, newval)

        if commit:
            newitem = self.save_instance(instance, old_pk_value,
                                         old_new_pk_registry)

        return newitem, old_pk_value

    def copy(self):
        # sort collected instances by pk and model dependencies
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter('pk'))
        self.sort()

        old_new_pk_registry, copied_objects = {}, []
        with transaction.atomic(using=self.using, savepoint=False):
            # update fields values
            for model, fields_values in self.field_updates.items():
                for field, value in fields_values.items():
                    for obj in self.data.get(model, []):
                        if callable(value):
                            value(obj, field)
                        else:
                            setattr(obj, field.name, value)

            # generate new objects
            for item in self.data.items():
                old_new_pk_registry.setdefault(item[0], {})
                for i in item[1]:
                    item = self.copy_object(i, old_new_pk_registry)
                    copied_objects.append(item)

        return copied_objects
