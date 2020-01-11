from django.test import TestCase
from django import forms
from django.core.validators import MaxLengthValidator
from sakkada.models.fields.multivalue import (
    CharMultipleValuesFormField, TextMultipleValuesFormField,
    CharMultipleValuesField, TextMultipleValuesField,
    TypedMultipleChoiceField, MultipleValuesDeferredAttribute)
from main.forms import MultiValueFieldModelForm, ExtendedCharMultipleValuesFormField
from main.models import MultiValueFieldModel


class MultiValueFieldTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_model_field_class_and_init_default_values(self):
        # check class defined values
        self.assertEqual((
            CharMultipleValuesField.multi_value_form_field_class,
            CharMultipleValuesField.multi_value_form_field_class_choices,
            CharMultipleValuesField.multi_value_delimiter,
            CharMultipleValuesField.multi_value_coerce,
        ), (
            CharMultipleValuesFormField,
            TypedMultipleChoiceField,
            ',',
            str,
        ))

        self.assertEqual((
            TextMultipleValuesField.multi_value_form_field_class,
            TextMultipleValuesField.multi_value_form_field_class_choices,
            TextMultipleValuesField.multi_value_delimiter,
            TextMultipleValuesField.multi_value_coerce,
        ), (
            TextMultipleValuesFormField,
            TypedMultipleChoiceField,
            '\n',
            str,
        ))

        # check init method values
        cfield = CharMultipleValuesField()
        tfield = TextMultipleValuesField()

        self.assertEqual(cfield.delimiter, CharMultipleValuesField.multi_value_delimiter)
        self.assertEqual(cfield.coerce, CharMultipleValuesField.multi_value_coerce)
        self.assertEqual(tfield.delimiter, TextMultipleValuesField.multi_value_delimiter)
        self.assertEqual(tfield.coerce, TextMultipleValuesField.multi_value_coerce)

        cfield = CharMultipleValuesField(delimiter='|', coerce=int)

        self.assertEqual(cfield.delimiter, '|')
        self.assertEqual(cfield.coerce, int)

    def test_field_contribute_to_class_and_deconstruct(self):
        self.assertEqual(
            type(MultiValueFieldModel.char_default),
            MultipleValuesDeferredAttribute
        )

        cfield_default = CharMultipleValuesField()
        cfield_changed = CharMultipleValuesField(delimiter='/', coerce=int)

        self.assertEqual(
            cfield_default.deconstruct(),
            (None, 'sakkada.models.fields.multivalue.CharMultipleValuesField', [], {})
        )
        self.assertEqual(
            cfield_changed.deconstruct(),
            (None, 'sakkada.models.fields.multivalue.CharMultipleValuesField', [],
             {'coerce': int, 'delimiter': '/',},)
        )

    def test_model_field_value_processing(self):
        obj = MultiValueFieldModel()
        obj.char_default = ['a', 'b', 'c',]
        obj.save()

        cfield_default = CharMultipleValuesField()
        cfield_changed = CharMultipleValuesField(delimiter='|', coerce=int)

        # to_python testing
        with self.assertRaises(ValueError):
            cfield_default.to_python(1)  # any non list, tuple, str and None values

        # test to_python ans coerce
        self.assertEqual(cfield_default.to_python(' 1,  2, 3'), ['1', '2', '3',])
        self.assertEqual(cfield_default.to_python([1, 2, 3]), ['1', '2', '3',])
        self.assertEqual(cfield_default.to_python((None, 2, '3',)), ['None', '2', '3',])

        # test to_python empty values
        self.assertEqual(cfield_default.to_python(None), None)
        self.assertEqual(cfield_default.to_python(''), [])
        self.assertEqual(cfield_default.to_python([]), [])
        self.assertEqual(cfield_default.to_python(tuple()), [])

        # test coerce with int type and different delimiter
        self.assertEqual(cfield_changed.to_python('1 | 2 |3 '), [1, 2, 3,])
        self.assertEqual(cfield_changed.to_python([1, '2', 3.0,]), [1, 2, 3,])

        # test coerce errors
        with self.assertRaises(ValueError):
            cfield_changed.to_python('1|nonint')  # any non int value
        with self.assertRaises(ValueError):
            cfield_changed.to_python([1, 2, 'nonint'])  # any non int value

        # check attribute setting correctness (it uses to_python)
        obj = MultiValueFieldModel.objects.first()

        obj.char_default = '1, 2,3'
        self.assertEqual(obj.char_default, ['1', '2', '3',])

        obj.char_default = [1, '2', 'strval']
        self.assertEqual(obj.char_default, ['1', '2', 'strval'])

        obj.char_default = None
        self.assertEqual(obj.char_default, None)

        obj.char_default = ''
        self.assertEqual(obj.char_default, [])

        obj.char_default = tuple()
        self.assertEqual(obj.char_default, [])

        with self.assertRaises(ValueError):
            obj.char_default = 1

        # get_prep_value testing
        self.assertEqual(cfield_default.get_prep_value(None), None)
        self.assertEqual(cfield_default.get_prep_value(''), '')
        self.assertEqual(cfield_default.get_prep_value('1,2,3'), '1,2,3')
        self.assertEqual(cfield_default.get_prep_value(' 1,2 , 3'), '1,2,3')
        self.assertEqual(cfield_default.get_prep_value([1, '2', 'a',]), '1,2,a')
        self.assertEqual(cfield_default.get_prep_value((1, '2', 'b',)), '1,2,b')

        with self.assertRaises(ValueError):
            cfield_default.get_prep_value(1)  # any non list, tuple, str or None values

        self.assertEqual(cfield_changed.get_prep_value(None), None)
        self.assertEqual(cfield_changed.get_prep_value(''), '')
        self.assertEqual(cfield_changed.get_prep_value('1|2|3'), '1|2|3')
        self.assertEqual(cfield_changed.get_prep_value(' 1|2 | 3'), '1|2|3')
        self.assertEqual(cfield_changed.get_prep_value([1, '2', 3.0,]), '1|2|3')
        self.assertEqual(cfield_changed.get_prep_value((1, '2', 4.0,)), '1|2|4')

        with self.assertRaises(ValueError):
            cfield_changed.get_prep_value(1)  # any non list, tuple, str or None values
        with self.assertRaises(ValueError):
            cfield_changed.get_prep_value([1, '2.0',])  # any non int value
        with self.assertRaises(ValueError):
            cfield_changed.get_prep_value([1, 'a',])  # any non int value

        # value_to_string testing
        obj = MultiValueFieldModel.objects.first()

        cfield = obj._meta.get_field('char_default')
        self.assertEqual(cfield.value_to_string(obj), 'a,b,c')

        obj.char_default = '1, 2, a , b  '
        self.assertEqual(cfield.value_to_string(obj), '1,2,a,b')

        obj.char_default = [1, 2, 3, 'a',]
        self.assertEqual(cfield.value_to_string(obj), '1,2,3,a')

    def test_model_form_field_initials(self):
        obj = MultiValueFieldModel()
        obj.char_default = ['a', 'b', 'c',]
        obj.text_default = ['a', 'b', 'c',]
        obj.save()

        obj = MultiValueFieldModel.objects.first()
        form = MultiValueFieldModelForm()

        # initial coerce value
        self.assertEqual(form['char_default'].field.coerce, str)
        self.assertEqual(form['cfield_integer'].field.coerce, int)
        self.assertEqual(form['cfield_float_with_choices_and_default'].field.coerce, float)
        self.assertEqual(CharMultipleValuesFormField().coerce.__name__, '<lambda>')

        # initial delimiter value
        self.assertEqual(form['char_default'].field.delimiter, ',')
        self.assertEqual(form['comma_separated'].field.delimiter, ',')
        self.assertEqual(form['slash_separated'].field.delimiter, '/')
        self.assertEqual(form['newline_separated'].field.delimiter, '\n')
        self.assertEqual(CharMultipleValuesFormField().delimiter, ',')
        self.assertEqual(TextMultipleValuesFormField().delimiter, '\n')

        # initial empty_value value
        self.assertEqual(form['char_default'].field.empty_value, [])
        self.assertEqual(CharMultipleValuesFormField().empty_value, [])
        self.assertEqual(CharMultipleValuesFormField(empty_value='anyvalue').empty_value,
                         'anyvalue')  # as described in source code, do it on your own risk

        # initial form_class
        self.assertEqual(form['char_default'].field.__class__,
                         CharMultipleValuesFormField)
        self.assertEqual(form['comma_separated'].field.__class__,
                         CharMultipleValuesFormField)
        self.assertEqual(form['text_default'].field.__class__,
                         TextMultipleValuesFormField)
        self.assertEqual(form['newline_separated'].field.__class__,
                         TextMultipleValuesFormField)

        self.assertEqual(form['cfield_with_extended_form_field'].field.__class__,
                         ExtendedCharMultipleValuesFormField)

        self.assertEqual(form['cfield_float_with_choices_and_default'].field.__class__,
                         TypedMultipleChoiceField)
        self.assertEqual(form['cfield_integer_with_choices_checkboxes'].field.__class__,
                         TypedMultipleChoiceField)
        self.assertEqual(form['tfield_integer_with_choices'].field.__class__,
                         TypedMultipleChoiceField)

        # initial widget
        self.assertEqual(form['char_default'].field.widget.__class__,
                         forms.TextInput)
        self.assertEqual(form['text_default'].field.widget.__class__,
                         forms.Textarea)
        self.assertEqual(form['cfield_integer'].field.widget.__class__,
                         forms.TextInput)
        self.assertEqual(form['cfield_float_with_choices_and_default'].field.widget.__class__,
                         forms.SelectMultiple)
        self.assertEqual(form['cfield_integer_with_choices_checkboxes'].field.widget.__class__,
                         forms.CheckboxSelectMultiple)

    def test_model_form_field_validation(self):
        obj = MultiValueFieldModel()
        obj.char_default = ['1', '2', '3',]
        obj.text_default = ['a', 'b', 'c',]
        obj.save()

        valid_data = {
            'char_default': '1,2,3',
            'text_default': '1\n2\n3',

            'comma_separated': 'a, b, c',
            'slash_separated': '1/2',
            'newline_separated': '1\n2',

            'cfield_blank': '',
            'cfield_with_extended_form_field': 'a, b',

            'cfield_integer': '1, 2, 3',
            'cfield_integer_with_default': '1, 2, 3',

            'cfield_float_with_choices_and_default': [1.0, '2.0',],
            'cfield_integer_with_choices_checkboxes': [1, '2',],
            'cfield_integer_with_grouped_choices': [2, '11',],
            'tfield_integer_with_choices': [1, '2',],
        }

        form = MultiValueFieldModelForm(data=valid_data)
        self.assertTrue(form.is_valid())

        form = MultiValueFieldModelForm(data={
            **valid_data,
            'cfield_integer': '1,2,nonint',  # coerce error
        })
        self.assertFalse(form.is_valid())
        self.assertTrue('cfield_integer' in form.errors)

        form = MultiValueFieldModelForm(data={
            **valid_data,
            'cfield_integer': '',  # non blank fields
        })
        self.assertFalse(form.is_valid())

        # it is a typed choice field, it requires a list
        form = MultiValueFieldModelForm(data={
            **valid_data,
            'cfield_float_with_choices_and_default': 'not a list',
        })
        self.assertFalse(form.is_valid())

        form = MultiValueFieldModelForm(data={
            **valid_data,
            'cfield_float_with_choices_and_default': [1.0, 'nonfloat'],  # coerce error
        })
        self.assertFalse(form.is_valid())

        # has_changed testing
        form = MultiValueFieldModelForm(
            data=valid_data, instance=obj,
            initial={'cfield_integer': '1,nonint',}  # test ValidationError in has_changed
        )
        form['comma_separated'].field.disabled = True  # has_changed test
        form.is_valid()

        self.assertFalse('comma_separated' in form.changed_data)  # disabled
        self.assertFalse('char_default' in form.changed_data)
        self.assertTrue('text_default' in form.changed_data)

        # model fields validation testing (also call default coerce lambda)
        class MultiValueFieldModelTestForm(MultiValueFieldModelForm):
            cfield_non_editable = CharMultipleValuesFormField(required=False)

        obj.cfield_non_editable = ['1', '2', '3',]
        obj.save()

        form = MultiValueFieldModelTestForm(
            data={**valid_data, 'cfield_non_editable': '3,2,1',},
            instance=obj
        )
        form.is_valid()

        self.assertEqual(form.cleaned_data['cfield_non_editable'], ['3', '2', '1',])

        obj.cfield_integer = None
        obj.cfield_integer_with_default = []
        obj.cfield_integer_with_grouped_choices = [2, '11', 33,]

        with self.assertRaises(forms.ValidationError) as cm:
            obj.full_clean()
        self.assertTrue('cfield_integer' in cm.exception.error_dict)
        self.assertTrue('cfield_integer_with_default' in cm.exception.error_dict)
        self.assertTrue('cfield_integer_with_grouped_choices' in cm.exception.error_dict)

        charfield = obj._meta.get_field('cfield_integer')

        self.assertEqual(charfield.run_validators([]), None)
        self.assertEqual(charfield.run_validators(tuple()), None)
        self.assertEqual(charfield.run_validators(None), None)
        self.assertTrue(hasattr(charfield, 'validators_charfield') and
                        len(charfield.validators_charfield) == 1 and
                        type(charfield.validators_charfield[0]) == MaxLengthValidator)

    def test_model_form_field_methods(self):
        obj = MultiValueFieldModel()
        obj.char_default = ['a', 'b', 'c',]
        obj.text_default = ['a', 'b', 'c',]
        obj.save()

        form = MultiValueFieldModelForm(instance=obj)

        # prepare_value testing
        self.assertEqual(form['char_default'].field.prepare_value(['1', '2', '3',]), '1,2,3')
        self.assertEqual(form['char_default'].field.prepare_value([]), '')
        self.assertEqual(form['char_default'].field.prepare_value(''), '')
        self.assertEqual(form['char_default'].field.prepare_value(None), None)
        self.assertEqual(form['cfield_integer'].field.prepare_value([1, 3, 12345,]), '1,3,12345')
        self.assertEqual(form['text_default'].field.prepare_value(['a', 'b']), 'a\nb')
        self.assertEqual(form['comma_separated'].field.prepare_value(['a', 'b']), 'a,b')
        self.assertEqual(form['slash_separated'].field.prepare_value(['a', 'b']), 'a/b')
        self.assertEqual(form['newline_separated'].field.prepare_value(['a', 'b']), 'a\nb')

        # select and checkbox fields have their own prepare_value methods
        self.assertEqual(
            form['cfield_integer_with_choices_checkboxes'].field.prepare_value([1, 3, 7,]),
            [1, 3, 7,])
        self.assertEqual(
            form['cfield_float_with_choices_and_default'].field.prepare_value([1.0, 1.5,]),
            [1.0, 1.5,])

    def test_model_mixin_for_get_display(self):
        obj = MultiValueFieldModel()
        obj.tfield_integer_with_choices = [1, 2, 3,]
        obj.save()

        self.assertEqual(obj.get_cfield_float_with_choices_and_default_display(), 'One, Two')
        self.assertEqual(obj.get_cfield_integer_with_choices_checkboxes_display(), 'One, Two')
        self.assertEqual(obj.get_cfield_integer_with_grouped_choices_display(), 'One, Twenty two')
        self.assertEqual(obj.get_tfield_integer_with_choices_display(), 'One, Two, Three')

        obj.tfield_integer_with_choices = None
        self.assertEqual(obj.get_tfield_integer_with_choices_display(), '')
