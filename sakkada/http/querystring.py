from django.utils.safestring import mark_safe

class QueryString(object):
    """
    QueryString (GET query string tool)
    Usage:
        no__name1__name2    - exclude variables by name in "no" section
        only__name1__name2  - only variables with name in "only" section
        as__format[left]    - return querydict in format (must be at the end)
                              if left, also add &(?) at the end of querystring

        format available values:
                      query, left | query, no left | no query, left | no query, no left
            full    - "?a=a&"     | "?a=a"         | "?"            | ""
            part    - "&a=a&"     | "&a=a"         | "&"            | ""
            self    - "a=a&"      | "a=a"          | ""             | ""
            dict    - return query as is (QueryDict)

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

    def __init__(self, request):
        self.querydict = request.GET.copy()

    def __getattr__(self, name):
        data    = name.rsplit('as__')
        keys    = data[0].strip('__').split('__')[:]
        out     = data[1] if data.__len__() > 1 else 'full'
        out     = {'format': out[:4] if out[:4] in ['part', 'full', 'self', 'dict'] else 'full', 'left':out.endswith('left')}
        query   = self.querydict.copy()

        # morph query by action
        if keys.__len__() > 1 and keys[0] in ['no', 'only']:
            action, realkeys = keys[0], keys[1:]
            if 'no' == action:
                [query.pop(i, None) for i in realkeys]
            elif 'only' == action:
                [query.pop(i, None) for i in query.keys() if i not in realkeys]

        # output format
        if out['format'] != 'dict':
            first = {'full':'?', 'part':'&', 'self':''}[out['format']]
            query = query.urlencode()
            query = '%s%s' % (first, query) if query else ''
            query = query + ('&' if query else first) if out['left'] else query

        return mark_safe(query)