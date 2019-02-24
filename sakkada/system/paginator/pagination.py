class PaginationBase(object):
    """
    usage:
        pagination = Pagination(page) # page - core paginator Page object
        pagination = Pagination(page) # page - dict {'page': 3, 'count': 200, 'perpage': 20,}
                                      #        or   {'page': 3, 'pages': 10,}
    """

    def __init__(self, page, paginate=True):
        if isinstance(page, dict):
            pages = page.get('pages') or 1 if 'pages' in page else None
            pages = pages or (page['count'] // page['perpage'] +
                              (page['count'] % page['perpage'] and 1))
            number = page['page'] if 1 <= page['page'] <= pages else 1
        else:
            pages = page.paginator.num_pages
            number = page.number

        self.pages, self.number = pages, number
        paginate and self.paginate()

    def paginate(self):
        raise NotImplementedError


class Pagination(PaginationBase):
    """
    usage:
        pagination = Pagination(page, window=2)

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

    window = 2

    def __init__(self, page, window=None):
        if isinstance(window, int) and window > 0:
            self.window = window
        super(Pagination, self).__init__(page)

    def paginate(self):
        number, pages, window = self.number, self.pages, self.window

        # get start and end
        start = number - window
        start = start if start > 1 else 1
        end = number + window
        end = end if end < pages else pages

        # save window*2 count
        if ((number - start) < window):
            end = (end + (window - (number - start)))
        elif ((end - number) < window):
            start = (start - (window - (end - number)))
        start = start if start > 1 else 1
        end = end if end < pages else pages
        # // save window*2 count

        start_dot = start > 1
        end_dot = end < pages

        self.pages = list()
        self.num_pages = pages

        self.prev = number - 1 if number > 1 else None
        self.first = 1 if start_dot else None
        self.dots_left = start-1 if start_dot and start-1 > 1 else None
        self.current = number
        self.dots_right = end+1 if end_dot and end+1 < pages else None
        self.last = pages if end_dot else None
        self.next = number + 1 if number < pages else None

        for i in range(start, end+1):
            self.pages.append({'current': i == number, 'number': i,})
