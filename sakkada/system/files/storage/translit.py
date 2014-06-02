import unicodedata
from pytils.translit import translify
from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename


class TranslitNameFileSystemStorage(FileSystemStorage):
    """
    Transliterate cyrillic unicode filename, ignore any other symbols.
    Requires pytils (translify) for transliteration.
    """

    def get_valid_name(self, name):
        """Transliterate (from russian cyrillic) and lowerize name of file."""
        if isinstance(name, unicode):
            name = unicodedata.normalize('NFKD', name)
            name = name.encode('cp1251', 'ignore').decode('cp1251')
            name = translify(name).lower()
        return get_valid_filename(name)
