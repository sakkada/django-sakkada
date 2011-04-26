from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.conf import settings
from django import forms

class ClearableFileWidget(forms.widgets.FileInput):
    """A AdminFileWidget that shows a delete checkbox"""
    input_type = 'file'

    def __init__(self, show_delete_checkbox=True, attrs={}):
        super(ClearableFileWidget, self).__init__(attrs)
        self.show_delete_checkbox = show_delete_checkbox

    def render(self, name, value, attrs=None):
        input = super(ClearableFileWidget, self).render(name, value, attrs)
        if value and hasattr(value, "url"):
            item_link   = u'%s&nbsp;<a target="_blank" href="%s%s">%s</a>'
            item_field  = u'<br>%s&nbsp;%s'
            item_check  = u' <nobr><input type="checkbox" name="%s_delete" id="id_%s_delete"/> &mdash;' \
                          u' <label style="display: inline; float: none;" for="id_%s_delete">%s</label></nobr>'
            check_tag   = u''

            # generate delete checkbox
            if self.show_delete_checkbox:
                check_tag = item_check % (name, name, name, _('Delete'))

            output = []
            output.append(u'<div>')
            output.append(item_link % (_('Currently:'), settings.MEDIA_URL, value, value))
            output.append(item_field % (_('Change:'), input))
            output.append(check_tag)
            output.append(u'</div>')
            return mark_safe(u''.join(output))
        else:
            return mark_safe(input)

    def value_from_datadict(self, data, files, name):
        return u'__deleted__' if data.get(u'%s_delete' % name) else super(ClearableFileWidget, self).value_from_datadict(data, files, name)