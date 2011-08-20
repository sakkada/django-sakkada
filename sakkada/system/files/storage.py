from pytils.translit import translify
from django.core.files.storage import FileSystemStorage as FileSystemStorageOriginal
from django.utils.text import get_valid_filename
import os
import unicodedata

class FileSystemStorage(FileSystemStorageOriginal):

    def get_valid_name(self, name):
        """
        Returns a filename, based on the provided filename, that's suitable for
        use in the target storage system.

        Extend: transliterate (from russian) and lowerize name of file.
        """
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('cp1251', 'ignore').decode('cp1251')
        name = translify(name).lower()
        return get_valid_filename(name)

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.

        Extend: set _xxx suffix istead adding underscore
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)

        # get current suffix if exist
        suffix = file_root[-4:]
        suffix_added = len(suffix) == 4 and suffix[0] == '_' and suffix[1:].isdigit()
        suffix = int(suffix[1:])+1 if suffix_added else 1
        suffix_less_file_root = file_root[:-4] if suffix_added else file_root

        while self.exists(name):
            if suffix > 999:
                raise OSError('Unable to generate unique filename.')

            file_root = suffix_less_file_root + '_' + suffix.__str__().zfill(3)
            suffix += 1

            # file_ext includes the dot.
            name = os.path.join(dir_name, file_root + file_ext)

        return name