from django.db import models

class PrevNextModel(object):
    def _get_current_ordering(self, queryset):
        """Get current ordering fields with directions"""
        pk = self._meta.pk.name
        query = queryset.query

        # get order_by declaration (django/models/sql/compiler-get_ordering)
        if query.extra_order_by:
            ordering = query.extra_order_by
        elif not query.default_ordering:
            ordering = query.order_by
        else:
            ordering = query.order_by or query.model._meta.ordering or [pk]

        # add pk ordering for uniqueness
        ordering = [i.replace('pk', pk) if i in ['pk', '-pk'] else i for i in ordering]
        if pk in ordering or '-%s' % pk in ordering:
            ordering = ordering[0:[i.lstrip('-') for i in ordering].index(pk)+1]
        else:
            ordering.append(pk)

        return ordering

    def _get_next_or_previous_by_order(self, is_next=True, order_by=[],
                                              queryset=False, cachename=False,
                                               force=False, as_queryset=False):
        """Get next or previous element according current order_by settings"""
        cachename = "__%s%s_in_nextprev_order_cache" % ('next' if is_next else 'prev',
                                                        '_' + cachename if cachename else '')
        if force or not hasattr(self, cachename):
            # get queryset and current ordering data
            queryset    = queryset if isinstance(queryset, models.query.QuerySet) \
                                   else self._default_manager.get_query_set()
            queryset    = queryset.order_by(*order_by) if len(order_by) else queryset
            ordering    = self._get_current_ordering(queryset)
            order       = {'name': [i.lstrip('-') for i in ordering],
                           'dir': [not i.startswith('-') if is_next else i.startswith('-') \
                                   for i in ordering]}
            ordering    = ordering if is_next else [i.lstrip('-') if i[0]=='-' else '-%s' % i \
                                                    for i in ordering]

            # generate filter list
            filter = []
            for name in order['name']:
                index   = order['name'].index(name)
                direc   = order['dir'][index]
                value   = getattr(self, name)
                equals  = dict([(i, getattr(self, i)) for i in order['name'][0:index]])

                # null values specific processing: if direction is reverse - ignore
                if value is None:
                    # ignore for not loop by null values
                    if not direc: continue
                    key, value = '%s__isnull' % name, False
                    cmps = models.Q(**{key: value,})
                else:
                    key = '%s__%s' % (name, direc and 'gt' or 'lt')
                    cmps = models.Q(**{key: value,})

                    # add isnull filter for reverse direction on nullable fields
                    isnull = self.__class__._meta.get_field_by_name(name)[0].null
                    if not direc and isnull:
                        cmps = cmps | models.Q(**{'%s__isnull' % name: True,})

                filter.append((models.Q(**equals) & cmps))

            # get filter and exclude self.pk for strict filtering
            filter = reduce(lambda x, y: y | x, filter) & ~models.Q(pk=self.pk)

            # return as queryset, filter and ordering params if True
            if as_queryset:
                return queryset.filter(filter).order_by(*ordering), filter, ordering

            queryset = queryset.filter(filter).order_by(*ordering)[0:1]
            queryset = list(queryset) # preventing count call
            queryset = queryset[0] if len(queryset) else None
            # disable cache once if 'nocache'
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