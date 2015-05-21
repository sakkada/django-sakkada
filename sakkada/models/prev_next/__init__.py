from django.db import models


class PrevNextModel(models.Model):
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
        else:
            ordering = query.order_by or query.get_meta().ordering or [pk]

        # append pk ordering for uniqueness if not exists,
        # else cut any fields after pk (because pk is unique)
        ordering = [i.replace('pk', pk) if i in ['pk', '-pk'] else i
                    for i in ordering]
        nodirect = [i.lstrip('-') for i in ordering]
        if pk in nodirect:
            ordering = ordering[0:nodirect.index(pk)+1]
        else:
            ordering.append(pk)

        return ordering

    def _get_next_or_previous_by_order(self, order_by=None, queryset=None,
                                       cachename=None, is_next=True,
                                       force=False, as_queryset=False):
        """Get next or previous element according current queryset ordering"""
        cachename = '_%s' % cachename if cachename else ''
        cachename = '__%s%s_nextprev_cache' % ('next' if is_next else 'prev',
                                               cachename)

        if force or not hasattr(self, cachename):
            # get queryset and current ordering data
            queryset = (self._default_manager.get_queryset()
                        if not isinstance(queryset, models.query.QuerySet)
                        else queryset)
            queryset = queryset.order_by(*order_by) if order_by else queryset
            ordering = self._get_current_ordering(queryset)
            nodirect = [i.lstrip('-') for i in ordering]

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
                    if not direction:
                        continue
                    key, value = '%s__isnull' % name, False
                    cmps = models.Q(**{key: value,})
                else:
                    key = '%s__%s' % (name, direction and 'gt' or 'lt')
                    cmps = models.Q(**{key: value,})

                    # add isnull filter for reverse direction on nullable fields
                    null = self.__class__._meta.get_field_by_name(name)[0].null
                    if not direction and null:
                        cmps = cmps | models.Q(**{'%s__isnull' % name: True,})

                filter.append((models.Q(**equals) & cmps))

            # compile filter and exclude self.pk for strict filtering
            filter = reduce(lambda x, y: y | x, filter) & ~models.Q(pk=self.pk)
            queryset = queryset.filter(filter).order_by(*ordering)

            # return as (queryset, filter and ordering params) if as_queryset
            if as_queryset:
                return queryset, filter, ordering
            queryset = list(queryset[0:1]) # preventing count call
            queryset = queryset[0] if queryset else None
            # do not save to cache if 'nocache'
            if force == 'nocache':
                return queryset
            setattr(self, cachename, queryset)

        return getattr(self, cachename)

    def get_next_by_order(self, **kwargs):
        kwargs['is_next'] = True
        return self._get_next_or_previous_by_order(**kwargs)

    def get_prev_by_order(self, **kwargs):
        kwargs['is_next'] = False
        return self._get_next_or_previous_by_order(**kwargs)
