from django.db import models

class PrevNextModel(object):
    def _get_current_ordering(self, queryset):
        """Get current ordering fields with directions"""
        id = self._meta.pk.name
        query = queryset.query

        if query.extra_order_by:
            ordering = query.extra_order_by
        elif not query.default_ordering:
            ordering = query.order_by
        else:
            ordering = query.order_by or query.model._meta.ordering
        if not ordering:
            ordering = [id]
        ordering = [i.replace('pk', id) if i in ['pk', '-pk'] else i for i in ordering]
        if id in ordering or '-'+id in ordering:
            ordering = ordering[0:[i.lstrip('-') for i in ordering].index(id)+1]
        else:
            ordering.append(id)

        return ordering

    def _get_next_or_previous_by_order(self, is_next=True, order_by=[], queryset=False, cachename=False):
        """Get next or previous element according current order_by settings"""
        cachename = "__%s%s_in_nextprev_order_cache" % ('next' if is_next else 'prev', '_' + cachename if cachename else '')
        if not hasattr(self, cachename):
            queryset    = queryset or self._default_manager.get_query_set()
            queryset    = queryset.order_by(*order_by) if len(order_by) else queryset
            ordering    = self._get_current_ordering(queryset)
            order       = {'name':[i.lstrip('-') for i in ordering], 'direction':[i[0] != '-' for i in ordering]}
            ordering    = ordering if is_next else [i.lstrip('-') if i[0]=='-' else '-'+i for i in ordering]

            filter = models.Q()
            cmps = is_next and {'next':'gt', 'prev':'lt'} or {'next':'lt', 'prev':'gt'}
            for name in order['name']:
                index       = order['name'].index(name)
                key         = '%s__%s' % (name, order['direction'][index] and cmps['next'] or cmps['prev'])
                equals      = dict([(i, getattr(self, i)) for i in order['name'][0:index]])
                equals[key] = getattr(self, name)
                filter      = models.Q(**equals) | filter

            queryset = queryset.filter(filter).order_by(*ordering)[0:1]
            obj = len(queryset) and queryset[0]
            setattr(self, cachename, obj)
        return getattr(self, cachename)

    def get_next_by_order(self, **kwargs):
        kwargs['is_next'] = True
        return self._get_next_or_previous_by_order(**kwargs)

    def get_prev_by_order(self, **kwargs):
        kwargs['is_next'] = False
        return self._get_next_or_previous_by_order(**kwargs)