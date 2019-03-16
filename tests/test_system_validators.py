import io
from PIL import Image
from django.test import TestCase
from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.template import Template, Context
from django.core.files.uploadedfile import InMemoryUploadedFile
from sakkada.system.validators import (
    isuploaded, FilesizeValidator, MimetypeValidator, ExtensionValidator)

from main.forms import FileFieldModelForm
from test_models_fields_fielfield import (
    get_temporary_text_file, get_temporary_image_file)


def get_non_temporary_file():
    return open(__file__, 'r')


class ValidatorsTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_isuploaded(self):
        txt_file = get_temporary_text_file()
        img_file = get_temporary_image_file()
        form = FileFieldModelForm({}, {'file': txt_file, 'image': img_file,})

        self.assertTrue(form.is_valid())

        form_file = form.cleaned_data['file']
        model_file = form.instance.file

        self.assertTrue(isuploaded(form_file))
        self.assertTrue(isuploaded(model_file))
        self.assertEqual(isuploaded(form_file, getfile=True), form_file)
        self.assertEqual(isuploaded(model_file, getfile=True), model_file._file)

    def test_filesizevalidator(self):
        txt_file = get_temporary_text_file()
        non_temporary_file = get_non_temporary_file()

        self.assertRaises(ValueError, FilesizeValidator)
        self.assertRaises(ValidationError, FilesizeValidator(min=10), txt_file)
        self.assertRaises(ValidationError, FilesizeValidator(max=2), txt_file)

        self.assertEqual(FilesizeValidator(min=3, max=5)(txt_file), None)
        self.assertEqual(FilesizeValidator(min=3)(txt_file), None)
        self.assertEqual(FilesizeValidator(max=5)(txt_file), None)
        self.assertEqual(FilesizeValidator(max=1)(non_temporary_file), None)

        self.assertEqual(FilesizeValidator(max=1), FilesizeValidator(max=1))
        self.assertNotEqual(FilesizeValidator(min=1), FilesizeValidator(min=2))

        non_temporary_file.close()

    def test_mimetypevalidator(self):
        txt_file = get_temporary_text_file()
        non_temporary_file = get_non_temporary_file()

        self.assertRaises(ValueError, MimetypeValidator)
        self.assertRaises(ValidationError, MimetypeValidator('image/pnga'), txt_file)

        self.assertEqual(MimetypeValidator('text/plain').mimetypes, ('text/plain',))
        self.assertEqual(MimetypeValidator(('text/plain',)).mimetypes, ('text/plain',))
        self.assertEqual(MimetypeValidator(mimetypes='text/plain').mimetypes, ('text/plain',))
        self.assertEqual(MimetypeValidator('text/plain')(txt_file), None)
        self.assertEqual(MimetypeValidator(('image/png', 'text/plain',))(txt_file), None)
        self.assertEqual(MimetypeValidator('any/type')(non_temporary_file), None)

        self.assertEqual(MimetypeValidator('one'), MimetypeValidator('one'))
        self.assertNotEqual(MimetypeValidator('one'), MimetypeValidator('two'))

        non_temporary_file.close()

    def test_extensionvalidator(self):
        txt_file = get_temporary_text_file()
        non_temporary_file = get_non_temporary_file()

        self.assertRaises(ValueError, ExtensionValidator)
        self.assertRaises(ValidationError, ExtensionValidator('.png'), txt_file)

        self.assertEqual(ExtensionValidator('.txt').extensions, ('.txt',))
        self.assertEqual(ExtensionValidator(('.txt',)).extensions, ('.txt',))
        self.assertEqual(ExtensionValidator(extensions='.txt').extensions, ('.txt',))
        self.assertEqual(ExtensionValidator('.txt')(txt_file), None)
        self.assertEqual(ExtensionValidator(('.png', '.txt',))(txt_file), None)
        self.assertEqual(ExtensionValidator('.any')(non_temporary_file), None)

        self.assertEqual(ExtensionValidator('.one'), ExtensionValidator('.one'))
        self.assertNotEqual(ExtensionValidator('.one'), ExtensionValidator('.two'))

        non_temporary_file.close()
