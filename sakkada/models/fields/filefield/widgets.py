from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django import forms


class ClearableFileInput(forms.widgets.FileInput):
    """A AdminFileWidget that shows a delete checkbox"""
    input_type = 'file'

    def __init__(self, show_delete_checkbox=True, attrs={}):
        super(ClearableFileInput, self).__init__(attrs)
        self.show_delete_checkbox = show_delete_checkbox

    def get_html_tpls(self, input, name, value, attrs):
        return {
            'link':     u'%s&nbsp;<a target="_blank" href="%s">%s</a>',
            'field':    u'<br>%s&nbsp;%s',
            'delete':   (
                u' <nobr><input type="checkbox" id="id_%s_delete"'
                u' name="%s_delete"/> &mdash; <label for="id_%s_delete"'
                u' style="display: inline; float: none;">%s</label></nobr>'
            ),
        }

    def get_html_tags(self, html_tpls, input, name, value, attrs):
        delete_tag = u''

        # generate checkboxes
        if self.show_delete_checkbox:
            delete_tag = html_tpls['delete'] % (name, name, name, _('Delete'))

        # input and link to current file
        field_tag = html_tpls['field'] % (_('Change:'), input)
        link_tag  = html_tpls['link'] % (_('Currently:'), value.url, value)

        return [u'<div>', link_tag, field_tag, delete_tag, u'</div>']

    def render(self, name, value, attrs=None):
        input = super(ClearableFileInput, self).render(name, value, attrs)
        if value and hasattr(value, "url"):
            html_tpls = self.get_html_tpls(input, name, value, attrs)
            html_tags = self.get_html_tags(html_tpls, input, name, value, attrs)
            return mark_safe(u''.join(html_tags))
        else:
            return mark_safe(input)

    def value_from_datadict(self, data, files, name):
        # todo: do not allow both checkbox and file
        #       (see django.forms.widget FILE_INPUT_CONTRADICTION)
        if data.get(u'%s_delete' % name):
            value = u'__delete__'
        else:
            value = super(ClearableFileInput, self).value_from_datadict(
                data, files, name)
        return value


class ClearableImageFileInput(ClearableFileInput):
    def __init__(self, show_image=True, **kwargs):
        super(ClearableImageFileInput, self).__init__(**kwargs)
        self.show_image = show_image

    def get_html_tpls(self, *args):
        tpls = super(ClearableImageFileInput, self).get_html_tpls(*args)
        if self.show_image:
            tpls.update({
                'image': u'<img src="%s" alt="%s" width="%s" height="%s"'
                         u' style="float: left; margin: 0 10px 5px 0;">',
            })
        return tpls

    def get_html_tags(self, html_tpls, input, name, value, attrs):
        tags = super(ClearableImageFileInput, self).get_html_tags(
            html_tpls, input, name, value, attrs)

        if self.show_image:
            tags[0] = u'<div style="overflow: auto;">'
            tags.insert(1, html_tpls['image'] % (value.url, value.name,
                                                 value.width, value.height))
        return tags
