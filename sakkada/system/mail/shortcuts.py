import datetime
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.conf import settings
from django.core import mail


def message_from_template(context=None, template=None, email_to=None,
                          email_from=None, site=None, date=None):
    if not template or not email_to:
        raise ValueError('Shortcut: template and email_to params are required')

    context = context or {}
    site = site or Site.objects.get_current()
    date = date or datetime.datetime.now()
    email_from = email_from or settings.DEFAULT_FROM_EMAIL
    email_to = email_to if isinstance(email_to, (list, tuple)) else [email_to]

    message = {'context': context, 'current_site': site, 'current_date': date,}
    message = render_to_string(
        template, message).replace('\r', '').split('\n', 1)
    message = mail.EmailMessage(
        message[0], '\n'.join(message[1:]), email_from, email_to)

    return message
