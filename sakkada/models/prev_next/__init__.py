from functools import reduce
from django.db import models, connections


class PrevNextModel(models.Model):
    class Meta:
        abstract = True

    def _get_current_ordering(self, queryset):
        """Get current ordering fields with directions"""
        query, pk = queryset.query, self._meta.pk.name

        # note: taken from django source
        # get order_by declaration for current queryset:
        #   taken from django/models/sql/compiler.SQLCompiler:get_order_by
        #   at begining of method (there is no standalone method
        #   to get order_by field names for queryset instance),
        #   added order by "pk" by default for uniqueness (in else section)

        if query.extra_order_by:
            ordering = query.extra_order_by
        elif not query.default_ordering:
            ordering = query.order_by
        elif query.order_by:
            ordering = query.order_by
        elif query.get_meta().ordering:
            ordering = query.get_meta().ordering
        else:
            ordering = [pk]

        # append pk ordering for uniqueness if not exists,
        # else cut any fields after pk (because pk is unique)
        ordering = [i.replace('pk', pk) if i in ['pk', '-pk'] else i
                    for i in ordering]
        if any(not isinstance(i, str) or '__' in i or '?' in i
               for i in ordering):
            raise ValueError('PrevNextModel at this moment supports only'
                             ' local order_by fields defined as strings.')

        nodirect = [i.lstrip('-') for i in ordering]
        if pk in nodirect:
            ordering = ordering[0:nodirect.index(pk)+1]
        else:
            ordering.append(pk)

        return ordering

    def _get_next_or_prev_by_order(self, order_by=None,
                                   is_next=True, nulls_first=None,
                                   queryset=None, as_queryset=False,
                                   cache_name=None, force=False):
        """Get next or previous element according current queryset ordering"""
        cache_name = '_%s' % cache_name if cache_name else ''
        cache_name = '_%s%s_nextprev_cache' % ('next' if is_next else 'prev',
                                               cache_name)

        if force or not hasattr(self, cache_name) or as_queryset:
            # get queryset and current ordering data
            queryset = (type(self)._default_manager.get_queryset()
                        if not isinstance(queryset, models.query.QuerySet)
                        else queryset)
            queryset = queryset.order_by(*order_by) if order_by else queryset
            ordering = self._get_current_ordering(queryset)

            nodirect = [i.lstrip('-') for i in ordering]
            nulls_first = (connections[queryset.db].features.nulls_order_largest
                           if nulls_first is None else bool(nulls_first))

            if is_next:
                directions = [not i.startswith('-') for i in ordering]
            else:
                directions = [i.startswith('-') for i in ordering]
                ordering = [i.lstrip('-') if b else '-%s' % i
                            for i, b in zip(ordering, directions)]

            # generate filter list
            filter = []
            for i, (name, direction,) in enumerate(zip(nodirect, directions)):
                value = getattr(self, name)
                equals = dict([(i, getattr(self, i)) for i in nodirect[0:i]])

                # null values processing: if direction is reverse - ignore,
                # generate filter according each ordering fields and direction
                if value is None:
                    # ignore to disable loop by null values
                    if not nulls_first ^ direction:
                        continue
                    key, value = '%s__isnull' % name, False
                    cmps = models.Q(**{key: value,})
                else:
                    key = '%s__%s' % (name, direction and 'gt' or 'lt')
                    cmps = models.Q(**{key: value,})

                    # add isnull filter for reverse direction on nullable fields
                    null = self.__class__._meta.get_field(name).null
                    if not direction ^ nulls_first and null:
                        cmps = cmps | models.Q(**{'%s__isnull' % name: True,})

                filter.append((models.Q(**equals) & cmps))

            # compile filter and exclude self.pk for strict filtering
            filter = reduce(lambda x, y: y | x, filter) & ~models.Q(pk=self.pk)
            queryset = queryset.filter(filter).order_by(*ordering)

            # return as (queryset, filter and ordering params) if as_queryset
            if as_queryset:
                return queryset, filter, ordering
            queryset = list(queryset[0:1])  # preventing count call
            queryset = queryset[0] if queryset else None
            # do not save to cache if 'nocache'
            if force == 'nocache':
                return queryset
            setattr(self, cache_name, queryset)

        return getattr(self, cache_name)

    def get_next_by_order(self, **kwargs):
        kwargs['is_next'] = True
        return self._get_next_or_prev_by_order(**kwargs)

    def get_prev_by_order(self, **kwargs):
        kwargs['is_next'] = False
        return self._get_next_or_prev_by_order(**kwargs)
