# -*- coding: utf-8 -*-
# some ideas taken from https://github.com/ulule/django-separatedvaluesfield
# some ideas taken from https://github.com/sakkada/django-eavkit
from __future__ import unicode_literals
from django import forms
from django.db import models
from django.core.validators import MaxLengthValidator
from django.forms.fields import TypedMultipleChoiceField
from django.utils import six
from django.utils.encoding import force_text


# Multiple values form fields classes
# -----------------------------------
class BaseMultipleValuesFormField(forms.CharField):
    delimiter = None

    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', lambda value: value)
        self.delimiter = kwargs.pop('delimiter', None) or self.delimiter
        self.empty_value = kwargs.pop('empty_value', [])  # default is list
        super(BaseMultipleValuesFormField, self).__init__(
            empty_value=self.empty_value, *args, **kwargs)

    def _coerce(self, value):
        # validates that the values can be coerced to the right type
        # returns coerced list of values like in TypedMultipleChoiceField
        # django: used in clean and has_changed methods
        if value == self.empty_value or value in self.empty_values:
            return self.empty_value
        values = []
        for vitem in value:
            try:
                values.append(self.coerce(vitem))
            except (ValueError, TypeError, forms.ValidationError):
                raise forms.ValidationError('Value "%s" is incorrect.' % vitem)
        return values

    def clean(self, value):
        value = super(BaseMultipleValuesFormField, self).clean(value)
        return self._coerce(value)

    def to_python(self, value):
        # value convertation from string to python list with _coerce call
        # allowed to raise ValidationErrors if required
        value = super(BaseMultipleValuesFormField, self).to_python(value)
        return (self._coerce(value.split(self.delimiter))
                if value else self.empty_value)

    def prepare_value(self, value):
        # value convertation from python list to string
        if isinstance(value, (list, tuple)):
            value = self.delimiter.join([unicode(i) for i in value])
        return value

    def has_changed(self, initial, data):
        """Return True if data differs from initial."""
        # data is a string, initial is a list here
        if self.disabled:
            return False
        try:
            return self.to_python(data) != self._coerce(initial)
        except forms.ValidationError:
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

    def to_python(self, value):
        # receives list value from field's clean method for example
        # receives string value from deferred attribute for example
        # returns list of coerced values or
        # returns empty value in the following way:
        #   if value is None return it (we care about it only if forms)
        #   otherwise always return empty list
        assert(isinstance(value, (list, tuple, six.string_types, type(None))))
        if not value:
            return value if value is None else []

        values = ([i.strip() for i in value.split(self.delimiter)]
                  if isinstance(value, six.string_types) else value)
        return [self.coerce(v) for v in values]

    def validate(self, value, model_instance):
        # extended method without calling super version from Field
        # receices list or None, checks for choices correctness for every
        # item in list, and checks for null and blank for whole list value
        if not self.editable:
            return

        # value is already a list here (from to_python), so check every item
        if self.choices and value not in self.empty_values:
            for vitem in value:
                for option_key, option_value in self.choices:
                    if isinstance(option_value, (list, tuple)):
                        # This is an optgroup, so look inside for options.
                        for optgroup_key, optgroup_value in option_value:
                            if vitem == optgroup_key:
                                return
                    elif vitem == option_key:
                        return
                raise exceptions.ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': vitem,},
                )

        # check whole value as usual
        if value is None and not self.null:
            raise exceptions.ValidationError(
                self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(
                self.error_messages['blank'], code='blank')

    def get_prep_value(self, value):
        # may be still list of values because to_python method will be called
        # in CharField and TextField fields' get_prep_value method
        value = super(BaseMultipleValuesField, self).get_prep_value(value)
        # convert list to string if required for database
        if isinstance(value, (list, tuple)):
            value = self.delimiter.join([six.text_type(s) for s in value])
        return (value if isinstance(value, (six.string_types, type(None))) else
                force_text(value))

    def get_choices(self, include_blank=True, **kwargs):
        # disable blank option anyway for multiple select
        return super(BaseMultipleValuesField, self).get_choices(
            include_blank=False, **kwargs)

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        # set coerce anyway, by default it equals to default text_type
        kwargs.update(coerce=kwargs.get('coerce', self.coerce))
        if not self.choices:
            kwargs.update(delimiter=kwargs.get('delimiter', self.delimiter))

        return super(BaseMultipleValuesField, self).formfield(
            form_class=form_class or self.multi_value_form_field_class,
            choices_form_class=(choices_form_class or
                                self.multi_value_form_field_class_choices),
            **kwargs)

    def value_to_string(self, obj):
        # returns a string value of this field from the passed obj
        # this is used by the serialization framework
        return self.get_prep_value(self.value_from_object(obj))


class CharMultipleValuesField(BaseMultipleValuesField, models.CharField):
    def __init__(self, *args, **kwargs):
        super(CharMultipleValuesField, self).__init__(*args, **kwargs)
        # save and remove added by django MaxLengthValidator validator
        # save validator to check length of result string value (see validate)
        self.validators_charfield = [i for i in self.validators
                                     if isinstance(i, MaxLengthValidator)]
        self.validators = [i for i in self.validators
                           if not isinstance(i, MaxLengthValidator)]

    def run_validators(self, value):
        # all user defined validators receives list of values or None
        # validators_charfield receives result string and check it
        super(CharMultipleValuesField, self).run_validators(value)
        if value in self.empty_values:
            return
        for v in self.validators_charfield:
            v(self.get_prep_value(value))  # check result string value


class TextMultipleValuesField(BaseMultipleValuesField, models.TextField):
    multi_value_form_field_class = TextMultipleValuesFormField
    multi_value_delimiter = u'\n'

    def formfield(self, **kwargs):
        if self.choices:
            kwargs.update(widget=kwargs.get('widget', None))  # unset Textarea
        return super(TextMultipleValuesField, self).formfield(**kwargs)
