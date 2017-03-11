from django.utils import timezone
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.conf import settings
from django.core import mail


def message_from_template(context=None, template=None, email_to=None,
                          email_from=None, site=None, date=None,
                          template_html=None, user_email_subject_prefix=False):
    if not template or not email_to:
        raise ValueError('Shortcut "message_from_template": template and'
                         ' email_to params are required')

    context = context or {}
    site = site or Site.objects.get_current()
    date = date or timezone.now()
    email_from = email_from or settings.DEFAULT_FROM_EMAIL
    email_to = email_to if isinstance(email_to, (list, tuple)) else [email_to]

    context = {'context': context, 'site': site, 'date': date,}
    msgtext = render_to_string(template,
                               context).replace('\r', '').split('\n', 1)
    msghtml = render_to_string(template_html,
                               context) if template_html else None
    subject = msgtext[0]
    msgtext = msgtext[1] if len(msgtext) == 2 else msgtext[0]

    if user_email_subject_prefix:
        subject = u'%s%s' % (settings.EMAIL_SUBJECT_PREFIX, subject)

    if msghtml:
        message = mail.EmailMultiAlternatives(
            subject, msgtext, email_from, email_to)
        message.attach_alternative(msghtml, "text/html")
    else:
        message = mail.EmailMessage(
            subject, message, email_from, email_to)

    return message
