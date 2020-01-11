import markdown
from django import forms
from django.db import models
from django.conf import settings
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
from sakkada.admin.editors.markdown import MarkdownTextInput, MarkdownTextarea


MARKDOWN_INIT_KWARGS = {
    'extensions': [],
    'extension_configs': {},
    'output_format': "html",
    'tab_length': 2,
    **getattr(settings, 'MARKDOWN_INIT_KWARGS', {})
}
MARKDOWN_HELP_TEXT = (
    '<a target="_blank" href="https://en.wikipedia.org/wiki/Markdown">'
    'Wikipedia</a>'
    ' | '
    '<a target="_blank" href="https://www.markdownguide.org/">'
    'Guide</a>'
    ' | '
    '<a target="_blank" href="https://daringfireball.net/projects/markdown/">'
    'Documentation</a>'
    ' | '
    '<a target="_blank" href="https://marked.js.org/demo/">'
    'Demo</a>'
)


class MarkdownStringValue(str):
    """Markdown string value container."""
    def markdown(self):
        return markdown.markdown(self, **MARKDOWN_INIT_KWARGS)


class MarkdownCharFormField(forms.CharField):
    """Markdown form CharField."""
    markdown_value_class = MarkdownStringValue

    def __init__(self, *args, **kwargs):
        self.markdown_value_class = kwargs.pop('value_class',
                                               self.markdown_value_class)
        super().__init__(**kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return (self.markdown_value_class(value)
                if isinstance(value, str) else value)


class MarkdownAttribute(models.fields.DeferredAttribute):
    def __set__(self, obj, value):
        obj.__dict__[self.field.attname] = self.field.to_python(value)


class BaseMarkdownModelField:
    markdown_value_class = MarkdownStringValue
    markdown_form_class = MarkdownCharFormField
    markdown_cache_field = None

    def __init__(self, *args, **kwargs):
        self.markdown_cache_field = kwargs.pop('cache_field', None)
        self.markdown_value_class = kwargs.pop('value_class',
                                               self.markdown_value_class)
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, MarkdownAttribute(self))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.markdown_cache_field:
            kwargs['cache_field'] = self.markdown_cache_field
        if self.markdown_value_class is not MarkdownStringValue:
            kwargs['value_class'] = self.markdown_value_class
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.markdown_value_class(value)

    def to_python(self, value):
        if isinstance(value, MarkdownStringValue) or value is None:
            return value
        return self.markdown_value_class(value)

    def pre_save(self, instance, add):
        value = getattr(instance, self.name, None)
        if self.markdown_cache_field and value:
            setattr(instance, self.markdown_cache_field, value.markdown())
        return super().pre_save(instance, add)

    def formfield(self, **kwargs):
        return super().formfield(**{
            'form_class': self.markdown_form_class,
            'value_class': self.markdown_value_class,
            **kwargs,
        })


class MarkdownCharField(BaseMarkdownModelField, models.CharField):
    pass


class MarkdownTextField(BaseMarkdownModelField, models.TextField):
    pass


# Register fields to use custom widgets in the Admin
FORMFIELD_FOR_DBFIELD_DEFAULTS.update({
    MarkdownCharField: {'widget': MarkdownTextInput,},
    MarkdownTextField: {'widget': MarkdownTextarea,},
})
