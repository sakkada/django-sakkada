from django.utils.safestring import mark_safe


class QueryString(object):
    """
    QueryString (GET query string tool)
    Usage:
        no__name1__name2    - exclude variables by name in "no" section
        only__name1__name2  - only variables with name in "only" section
        as__format[left]    - return querydict in format (must be at the end)
                              if left, also add &(?) at the end of querystring

    Format available values:
        ┌─────────┬───────────┬───────────┬───────────┬───────────────┐
        │         │ query,    │ query,    │ no query, │ no query,     │
        │         │ left      │ no left   │ left      │ no left       │
        ├─────────┼───────────┼───────────┼───────────┼───────────────┤
        │ full    │ "?a=a&"   │ "?a=a"    │ "?"       │ ""            │
        │ part    │ "&a=a&"   │ "&a=a"    │ "&"       │ ""            │
        │ self    │ "a=a&"    │ "a=a"     │ ""        │ ""            │
        ├─────────┼───────────┴───────────┴───────────┴───────────────┤
        │ dict    │ return query as is (QueryDict)                    │
        └─────────┴───────────────────────────────────────────────────┘
    Examples:
        http://example.com/?a=a&b=b&c=c
        q = QueryString(request)
        q.as__dict              # copy of QueryDict from request
        q.no__a__b__as__self    # c=c
        q.no__a__b__as__full    # ?c=c
        q.no__c__as__partleft   # &a=a&b=b&
        q.only__c__as__partleft # &c=c&
    """

    querydict = None

    formats = ('part', 'full', 'self', 'dict',)
    filters = ('no', 'only',)
    first_letter = {'full': '?', 'part': '&', 'self': '',}

    def __init__(self, request):
        self.querydict = request.GET.copy()

    def __getattr__(self, name):
        data = name.rsplit('as__')
        keys = data[0].strip('__').split('__')[:]
        out = data[1] if data.__len__() > 1 else 'full'
        out = {'format': out[:4] if out[:4] in self.formats else 'full',
               'left': out.endswith('left'),}
        query = self.querydict.copy()

        # morph query by filter
        if keys.__len__() > 1 and keys[0] in self.filters:
            action, keys, realkeys = keys[0], keys[1:], list(query.keys())
            if 'no' == action:
                [query.pop(i, None) for i in keys]
            else:  # only
                [query.pop(i, None) for i in realkeys if i not in keys]

        # output format
        if out['format'] != 'dict':
            first = self.first_letter[out['format']]
            query = query.urlencode()
            query = mark_safe(''.join((
                first if query else '', query,  # first letter and querystring
                ('&' if query else first) if out['left'] else '',  # last letter
            )))

        return query
