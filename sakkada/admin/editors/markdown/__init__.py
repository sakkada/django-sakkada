# -*- coding: utf-8 -*-
from django.conf import settings
from django.forms.widgets import Media, Widget, TextInput, Textarea


__all__ = ('MarkdownWidget', 'MarkdownInput', 'MarkdownTextarea',)


class MarkdownWidget(Widget):
    markdown_editor_use_cdnjs = True
    markdown_editor_use_in_admin = True
    markdown_editor_marked_local = 'admin/markdown/marked.min.js'
    markdown_editor_marked_cdnjs = (
        '//cdnjs.cloudflare.com/ajax/libs/marked/0.3.6/marked.min.js'
    )

    def __init__(self, attrs=None):
        attrs = dict({'data-dimensions': '330:270'}, **(attrs or {}))
        cls = ' '.join([attrs.get('class', ''), 'editor_markdown']).strip()
        attrs.update({'class': cls,})
        return super(MarkdownWidget, self).__init__(attrs=attrs)

    @property
    def media(self):
        js = tuple()
        if self.markdown_editor_use_in_admin:
            js = '' if settings.DEBUG else '.min'
            js = ('admin/js/vendor/jquery/jquery%s.js' % js,
                  'admin/js/jquery.init.js',)
        js += (
            'admin/js/vendor/jquery/jquery.resizable-field.js',
            'admin/js/vendor/jquery/jquery.markdown-field.js',
            (self.markdown_editor_marked_cdnjs
             if self.markdown_editor_use_cdnjs else
             self.markdown_editor_marked_local),
            'admin/markdown/markdown_editor.js',
        )

        css = {'all': ('admin/markdown/markdown_editor.css',),}
        base = getattr(super(MarkdownWidget, self), 'media', Media())
        return base + Media(js=js, css=css)


class MarkdownTextInput(TextInput, MarkdownWidget):
    pass


class MarkdownTextarea(Textarea, MarkdownWidget):
    pass
