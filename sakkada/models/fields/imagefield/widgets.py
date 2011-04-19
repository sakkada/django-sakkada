from django import forms
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.conf import settings
from django.utils.html import escape
from sorl.thumbnail.main import DjangoThumbnail
from sorl.thumbnail.base import ThumbnailException
from sorl.thumbnail.fields import ALL_ARGS

class DeleteImageWidget(forms.widgets.FileInput):
    """A AdminFileWidget that shows a delete checkbox"""
    input_type = 'file'

    def __init__(self, show_delete_checkbox=True, thumbnail=None, thumbnail_tag=None, attrs={}):
        super(DeleteImageWidget, self).__init__(attrs)
        self.show_delete_checkbox, self.thumbnail, self.thumbnail_tag = show_delete_checkbox, thumbnail, thumbnail_tag

    def render(self, name, value, attrs=None):
        input = super(DeleteImageWidget, self).render(name, value, attrs)
        if value and hasattr(value, "url"):
            item_thumb  = u'<div style="float: left; margin: 0 10px 0 0;">%s</div>'
            item_link   = u'%s&nbsp;<a target="_blank" href="%s%s">%s</a>'
            item_field  = u'<br>%s&nbsp;%s'
            item_check  = u' <nobr><input type="checkbox" name="%s_delete" id="id_%s_delete"/> &mdash;' \
                          u' <label style="display: inline; float: none;" for="id_%s_delete">%s</label></nobr>'
            thumb_tag, check_tag = u'', u''

            # generate thumbnail tag
            if self.thumbnail_tag:
                kwargs = dict([(ALL_ARGS[k], v) for k, v in self.thumbnail.items()])
                try:
                    thumb = DjangoThumbnail(value, **kwargs)
                except ThumbnailException:
                    return mark_safe(input)
                opts = dict(src=escape(thumb), width=thumb.width(), height=thumb.height())
                thumb_tag = mark_safe(self.thumbnail_tag % opts)
                thumb_tag = item_thumb % thumb_tag

            # generate delete checkbox
            if self.show_delete_checkbox:
                check_tag = item_check % (name, name, name, _('Delete'))

            output = []
            output.append(u'<div>')
            output.append(thumb_tag)
            output.append(item_link % (_('Currently:'), settings.MEDIA_URL, value, value))
            output.append(item_field % (_('Change:'), input))
            output.append(check_tag)
            output.append(u'</div>')
            return mark_safe(u''.join(output))
        else:
            return mark_safe(input)

    def value_from_datadict(self, data, files, name):
        return u'__deleted__' if data.get(u'%s_delete' % name) else super(DeleteImageWidget, self).value_from_datadict(data, files, name)