import io
import os
from PIL import Image
from django.test import TestCase
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import InMemoryUploadedFile
from sakkada.models.fields.filefield import (
    AdvancedFileField, ClearableFormImageField, ClearableFormFileField)
from main.forms import FileFieldModelForm
from main.models import FileFieldModel


def get_temporary_text_file():
    sio = io.StringIO()
    sio.write('text')
    uploadedfile = InMemoryUploadedFile(
        sio, None, 'text.txt', 'text/plain', sio.tell(), None)
    uploadedfile.seek(0)
    return uploadedfile


def get_temporary_image_file():
    bio = io.BytesIO()
    size, color = (300, 300,), (200, 50, 200, 80,)
    image = Image.new("RGBA", size, color)
    image.save(bio, format='PNG')
    uploadedfile = InMemoryUploadedFile(
        bio, None, 'image.png', 'png', bio.tell(), None)
    uploadedfile.seek(0)
    return uploadedfile


class AdvancedFileFieldTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_file_and_image_uploading(self):
        txt_file = get_temporary_text_file()
        img_file = get_temporary_image_file()

        # both txt and image files
        form = FileFieldModelForm({}, {'file': txt_file, 'image': img_file,})
        self.assertTrue(form.is_valid())
        form.save()

        # only image file (txt is optional)
        img_file.seek(0)
        form = FileFieldModelForm({}, {'file': None, 'image': img_file,})
        self.assertTrue(form.is_valid())
        form.save()

        # only txt file (invalid)
        txt_file.seek(0)
        form = FileFieldModelForm({}, {'file': txt_file, 'image': None,})
        self.assertFalse(form.is_valid())

    def test_model_fields(self):
        txt_file = get_temporary_text_file()
        img_file = get_temporary_image_file()

        for i in range(2):
            txt_file.seek(0), img_file.seek(0)
            form = FileFieldModelForm({}, {'file': txt_file, 'image': img_file,})
            form.save()

        queryset = FileFieldModel.objects.all()
        m1, m2 = queryset

        # non blank fields can not be clearable
        self.assertRaises(ImproperlyConfigured,
                          AdvancedFileField,
                          'title', blank=False, clearable=True)

        # file field clearable but not erasable - db value empty, file exists
        form = FileFieldModelForm({'file_delete': True,}, instance=queryset.get(id=m1.id))
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(os.path.exists(m1.file.path))
        self.assertFalse(queryset.get(id=m1.id).file)

        # do nothing if file is not provided in _safe_erase
        m1_updated = queryset.get(id=m1.id)
        self.assertEqual(m1._meta.get_field('file')._safe_erase(
            m1_updated.file, m1_updated), None)

        # image field not clearable but erasable - file not exists after model deletion
        form = FileFieldModelForm({'image_delete': True,}, instance=queryset.get(id=m2.id))
        self.assertTrue(form.is_valid())  # nothing happend
        form.save()
        self.assertTrue(queryset.get(id=m2.id).image is not None)
        queryset.get(id=m2.id).delete()
        self.assertTrue(os.path.exists(m2.file.path))
        self.assertFalse(os.path.exists(m2.image.path))

    def test_additional_file_properties_and_methods(self):
        txt_file = get_temporary_text_file()
        img_file = get_temporary_image_file()

        form = FileFieldModelForm({}, {'file': txt_file, 'image': img_file,})
        form.save()

        m1 = FileFieldModel.objects.first()
        fpath = m1.file.path
        image_tag = u'<img src="%s" alt="%s" width="%%s">' % (m1.image.url, m1.image.name,)

        self.assertEqual(m1.file.basename, os.path.basename(fpath))
        self.assertEqual(m1.file.extension, os.path.splitext(fpath)[1])
        self.assertEqual(m1.file.basename_splitext,
                         os.path.splitext(os.path.basename(fpath)))

        self.assertEqual(m1.image.image_tag(), image_tag % 200)
        self.assertEqual(m1.image.image_tag(max_width=50), image_tag % 50)
        self.assertEqual(m1.image.image_tag(max_width=500), image_tag % 300)

    def test_form_fields(self):
        # test passing custom kwargs without errors
        ClearableFormFileField(clearable=True)
        ClearableFormImageField(clearable=True, show_image=True)

        # test different widgets
        ClearableFormFileField(widget=forms.widgets.FileInput)
        ClearableFormImageField(widget=forms.widgets.FileInput)

    def test_widgets(self):
        txt_file = get_temporary_text_file()
        img_file = get_temporary_image_file()
        form = FileFieldModelForm({}, {'file': txt_file, 'image': img_file,})
        form.save()
        m1 = FileFieldModel.objects.first()

        form_empty = FileFieldModelForm()
        form_files = FileFieldModelForm(instance=m1)

        # delete checkbox and show_delete_checkbox
        self.assertFalse('file_delete' in str(form_empty['file']))
        self.assertTrue('file_delete' in str(form_files['file']))
        form_files['file'].field.widget.show_delete_checkbox = False
        self.assertFalse('file_delete' in str(form_files['file']))

        # delete checkbox and show_delete_checkbox
        self.assertFalse('<img' in str(form_empty['image']))
        self.assertTrue('<img' in str(form_files['image']))
        form_files['image'].field.widget.show_image = False
        self.assertFalse('<img' in str(form_files['image']))
