# -*- coding: utf-8 -*-
# some ideas taken from https://github.com/ulule/django-separatedvaluesfield
# some ideas taken from https://github.com/sakkada/django-eavkit
from __future__ import unicode_literals
from django import forms
from django.db import models
from django.core.validators import MaxLengthValidator
from django.forms.fields import TypedMultipleChoiceField
from django.utils import six


# Multiple values form fields classes
# -----------------------------------
class BaseMultipleValuesFormField(forms.CharField):
    delimiter = None

    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', lambda value: value)
        self.delimiter = kwargs.pop('delimiter', None) or self.delimiter
        super(BaseMultipleValuesFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(BaseMultipleValuesFormField, self).clean(value)
        return self.values_coerce(value)

    def values_coerce(self, value):
        if value in self.empty_values:
            return None
        values = []
        for vitem in value:
            try:
                values.append(self.coerce(vitem))
            except (ValueError, TypeError, forms.ValidationError):
                raise forms.ValidationError('Value "%s" is incorrect.' % vitem)
        return values

    def to_python(self, value):
        # value convertation from string to python list
        value = super(BaseMultipleValuesFormField, self).to_python(value)
        if not value:
            return None
        values = [self.coerce(i.strip()) for i in value.split(self.delimiter)]

    def prepare_value(self, value):
        # value convertation from python list to string
        if isinstance(value, (list, tuple)):
            value = self.delimiter.join([unicode(i) for i in value])
        return value

    def has_changed(self, initial, data):
        """Return True if data differs from initial."""
        # Always return False if the field is disabled since self.bound_data
        # always uses the initial value in this case.
        if self.disabled:
            return False
        try:
            return self.coerce(self.to_python(data)) != self.coerce(initial)
        except ValidationError:
            return True


class CharMultipleValuesFormField(BaseMultipleValuesFormField):
    widget = forms.TextInput
    delimiter = u','


class TextMultipleValuesFormField(BaseMultipleValuesFormField):
    widget = forms.Textarea
    delimiter = u'\n'


# Multiple values model fields classes
# ------------------------------------
class MultipleValuesDeferredAttribute(models.fields.DeferredAttribute):
    def __init__(self, field_name, model, field):
        super(MultipleValuesDeferredAttribute, self).__init__(field_name, model)
        self.field = field

    def __set__(self, obj, value):
        obj.__dict__[self.field_name] = self.field.to_python(value)


class BaseMultipleValuesField(object):
    multi_value_form_field_class = CharMultipleValuesFormField
    multi_value_form_field_class_choices = TypedMultipleChoiceField
    multi_value_delimiter = ','
    multi_value_coerce = six.text_type

    def __init__(self, *args, **kwargs):
        self.delimiter = kwargs.pop('delimiter', self.multi_value_delimiter)
        self.coerce = kwargs.pop('coerce', self.multi_value_coerce)
        super(BaseMultipleValuesField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super(BaseMultipleValuesField,
              self).contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name,
                MultipleValuesDeferredAttribute(self.attname, cls, self))

    def validate(self, value, model_instance):
        if not value:
            return
        spr, values = super(BaseMultipleValuesField, self), value
        for value in values:
            spr.validate(value, model_instance)

    def to_python(self, value):
        assert(isinstance(value, (list, tuple, six.string_types, type(None))))
        if not value:
            return None

        values = ([i.strip() for i in value.split(self.delimiter)]
                  if isinstance(value, six.string_types) else value)
        return [self.coerce(v) for v in values]

    def get_db_prep_value(self, value, *args, **kwargs):
        if isinstance(value, (list, tuple)):
            value = self.delimiter.join([six.text_type(s) for s in value])
        value = super(BaseMultipleValuesField,
                      self).get_db_prep_value(value, *args, **kwargs)
        # anyway convert to empty string if null is not allowed
        return six.text_type() if value is None and not self.null else value

    def get_choices(self, include_blank=True, **kwargs):
        # disable blank option anyway for multiple select
        return super(BaseMultipleValuesField, self).get_choices(
            include_blank=False, **kwargs)

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        kwargs.update(coerce=kwargs.get('coerce', self.coerce))
        if not self.choices:
            kwargs.update(delimiter=kwargs.get('delimiter', self.delimiter))

        return super(BaseMultipleValuesField, self).formfield(
            form_class=form_class or self.multi_value_form_field_class,
            choices_form_class=(choices_form_class or
                                self.multi_value_form_field_class_choices),
            **kwargs)


class CharMultipleValuesField(BaseMultipleValuesField, models.CharField):
    def __init__(self, *args, **kwargs):
        super(CharMultipleValuesField, self).__init__(*args, **kwargs)
        # save and remove added by django MaxLengthValidator validator
        # save validator to check length of result string value (see validate)
        self.validators_charfield = [i for i in self.validators
                                     if isinstance(i, MaxLengthValidator)]
        self.validators = [i for i in self.validators
                           if not isinstance(i, MaxLengthValidator)]

    def get_prep_value(self, value):
        value = super(models.CharField, self).get_prep_value(value)
        return (value if isinstance(value, (six.string_types, type(None))) else
                force_text(value))

    def validate(self, value, model_instance):
        if not value:
            return
        super(CharMultipleValuesField, self).validate(value, model_instance)
        for v in self.validators_charfield:
            v(self.get_db_prep_value(value))


class TextMultipleValuesField(BaseMultipleValuesField, models.TextField):
    multi_value_form_field_class = TextMultipleValuesFormField
    multi_value_delimiter = u'\n'

    def get_prep_value(self, value):
        value = super(models.TextField, self).get_prep_value(value)
        return (value if isinstance(value, (six.string_types, type(None))) else
                force_text(value))

    def formfield(self, **kwargs):
        if self.choices:
            kwargs.update(widget=kwargs.get('widget', None))  # unset Textarea
        return super(TextMultipleValuesField, self).formfield(**kwargs)
