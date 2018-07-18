from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpRequest
from .pagination import Pagination


def paginator(queryset, number=None, per_page=10, pagination=True):
    """
    paginator shortcut
    :param queryset, model queryset for pagination
    :param number, if number is request object, get number
           from request.GET page param (?page=1)
    :param per_page, items per page
    :param pagination class or None
    """

    # get page number
    if isinstance(number, HttpRequest):
        number = number.GET.get('page', 1)
    try:
        number = abs(int(number)) or 1
    except ValueError:
        number = 1

    # get paginator object
    paginator = Paginator(queryset, per_page)

    # try to paginate
    try:
        page    = paginator.page(number)
    except (EmptyPage, InvalidPage):
        number  = paginator.num_pages
        page    = paginator.page(number)

    # attach pagination list or None
    if pagination and pagination is True:
        pagination = Pagination
    page.pagination = pagination and pagination(page) or None

    return page
