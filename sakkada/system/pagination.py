def pagination(page, window=2):
    """
    pagination (110322)
    ----------
    usage:
        pg = pagination(page, 2) # page - core paginator Page object
        pg = pagination(page, 2) # page - dict {'page': 3, 'count': 200, 'onpage': 20}

    template:
        {% if pagination and pagination.num_pages > 1 %}
        <ul id="pagination">
            {% if pagination.first %}<li class="first"><a href="?page={{ pagination.first }}">{% trans "first" %}</a></li>{% endif %}
            {% if pagination.prev %}<li class="prev"><a href="?page={{ pagination.prev }}">{% trans "prev" %}</a></li>{% endif %}
            {% if pagination.dots_left %}<li class="dots_left"><a href="?page={{ pagination.dots_left }}">...</a></li>{% endif %}

            {% for page in pagination.pages %}
            {% if page.current %}
            <li class="current"><span>{{ page.number }}</span></li>
            {% else %}
            <li><a href="?page={{ page.number }}">{{ page.number }}</a></li>
            {% endif %}
            {% endfor %}

            {% if pagination.dots_right %}<li class="dots_right"><a href="?page={{ pagination.dots_right }}">...</a></li>{% endif %}
            {% if pagination.next %}<li class="next"><a href="?page={{ pagination.next }}">{% trans "next" %}</a></li>{% endif %}
            {% if pagination.last %}<li class="last"><a href="?page={{ pagination.last }}">{% trans "last" %}</a></li>{% endif %}
        </ul>
    {% endif %}
    """

    if isinstance(page, dict):
        pages       = page['count']//page['onpage'] + (page['count'] % page['onpage'] and 1)
        current     = page['page'] if 1 <= page['page'] <= pages else 1
    else:
        pages       = page.paginator.num_pages
        current     = page.number
    window      = window if window > 0 else 2
    start       = current - window
    start       = start if start > 1 else 1
    end         = current + window
    end         = end if end < pages else pages

    # save window*2 count
    if ((current - start) < window):
        end = (end + (window - (current - start)))
    elif ((end - current) < window):
        start = (start - (window - (end - current)))
    start       = start if start > 1 else 1
    end         = end if end < pages else pages
    # // save window*2 count

    start_dot   = start > 1
    end_dot     = end < pages

    pagination                  = dict()
    pagination['pages']         = list()
    pagination['num_pages']     = pages

    pagination['prev']          = current - 1 if current > 1 else None
    pagination['first']         = 1 if start_dot else None
    pagination['dots_left']     = start-1 if start_dot and start-1>1 else None
    pagination['current']       = current
    pagination['dots_right']    = end+1 if end_dot and end+1<pages else None
    pagination['last']          = pages if end_dot else None
    pagination['next']          = current + 1 if current < pages else None

    for i in range(start, end+1):
        pagination['pages'].append({'current': i == current, 'number':i})

    pagination['wind_left']     = start-2 if start_dot else None
    pagination['wind_right']    = end-current if end_dot else None

    return pagination