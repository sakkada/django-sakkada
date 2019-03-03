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
            'link': (u'%s&nbsp;'
                     '<a id="id_%s_link" href="%s" target="_blank">%s</a>'),
            'field': u'<br>%s&nbsp;%s',
            'delete': (
                u' <nobr><input type="checkbox" id="id_%s_delete"'
                u' name="%s_delete"/> &mdash; <label for="id_%s_delete"'
                u' style="display: inline; float: none;">%s</label></nobr>'
            ),
        }

    def get_html_tags(self, html_tpls, input, name, value, attrs):
        field_tag = html_tpls['field'] % (_('Change:'), input)
        link_tag = html_tpls['link'] % (_('Currently:'),
                                        name, value.url, value)
        delete_tag = (html_tpls['delete'] % (name, name, name, _('Delete'))
                      if self.show_delete_checkbox else u'')

        return [u'<div>', link_tag, field_tag, delete_tag, u'</div>']

    def render(self, name, value, attrs=None, renderer=None):
        input = super().render(name, value, attrs=attrs, renderer=renderer)
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
    show_image_max_width = 200

    def __init__(self, show_image=True, **kwargs):
        super().__init__(**kwargs)
        self.show_image = show_image

    def get_html_tpls(self, *args):
        tpls = super().get_html_tpls(*args)
        if self.show_image:
            tpls.update({
                'image': u'<img id="id_%s_image" src="%s" alt="%s" width="%s"'
                         u' style="float: left; margin: 0 10px 5px 0;">',
            })
        return tpls

    def get_html_tags(self, html_tpls, input, name, value, attrs):
        tags = super().get_html_tags(html_tpls, input, name, value, attrs)
        if self.show_image:
            tags[0] = u'<div style="overflow: auto;">'
            tags.insert(1, html_tpls['image'] % (
                name, value.url, value.name,
                min(self.show_image_max_width, value.width),))
        return tags
