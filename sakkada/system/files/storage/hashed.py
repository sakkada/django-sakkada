"""
Forked from https://github.com/ecometrica/django-hashedfilenamestorage
Changes:
    - Storage defined as a usual class directly
    - Added segments param to define filename segmentation rule
    - Added uniquify_names param to control storage filename
        generation behaviour
"""

import hashlib
import os
import sys
import random

from errno import EEXIST

from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import force_text


class NoAvailableName(Exception):
    pass


class HashedNameFileSystemStorage(FileSystemStorage):
    segments = None
    uniquify_names = False

    def __init__(self, segments=None, uniquify_names=None, *args, **kwargs):
        """
        segments param: tuple value (seglength, segcount), seglength * segcount
            should be less than 40 (sha1 len), usually used (1,2) or (2,2);
            add prefix to filename with segcount segments by seglen chars
            example: (2,2) => 1234567890... -> 12/34/1234567890,
                     (1,2) => 1234567890... -> 1/2/341234567890.
        """

        if (segments and segments.__len__() == 2
                     and segments[0] * segments[1] <= 40):
            self.segments = segments

        if self.uniquify_names is not None:
            self.uniquify_names = uniquify_names

        super(HashedNameFileSystemStorage, self).__init__(*args, **kwargs)

    def get_available_name(self, name):
        if self.uniquify_names:
            return self._get_available_name(name)
        else:
            raise NoAvailableName()

    def _get_available_name(self, name, content=None, chunk_size=None):
        dirname, basename = os.path.split(name)
        ext = os.path.splitext(basename)[1].lower()
        root = (self._compute_hash_by_name(name) if self.uniquify_names
                else self._compute_hash_by_content(content=content,
                                                   chunk_size=chunk_size))
        root = self._segments(root)

        return os.path.join(dirname, '%s%s' % (root, ext,))

    def _segments(self, value):
        segments = None
        if self.segments:
            slen, scnt = self.segments
            segments = [value[i:i+slen] for i in range(0, slen*scnt, slen)]
            segments = '/'.join(i for i in segments if i)
        return segments and '%s/%s' % (segments, value,) or value

    def _compute_hash_by_name(self, name):
        # generate hash from filename and some random value
        encoding = sys.getfilesystemencoding()
        hasher = hashlib.sha1()
        hasher.update('%s#%.20f' % (name.encode(encoding, 'ignore'),
                                    random.random(),))
        return hasher.hexdigest()

    def _compute_hash_by_content(self, content, chunk_size=None):
        if chunk_size is None:
            chunk_size = getattr(content, 'DEFAULT_CHUNK_SIZE',
                                 File.DEFAULT_CHUNK_SIZE)
        hasher = hashlib.sha1()
        cursor = content.tell()
        content.seek(0)
        try:
            while True:
                data = content.read(chunk_size)
                if not data:
                    break
                hasher.update(data)
            return hasher.hexdigest()
        finally:
            content.seek(cursor)

    def save(self, name, content):
        # Get the proper name for the file, as it will actually be saved.
        if name is None:
            name = content.name

        if not hasattr(content, 'chunks'):
            content = File(content)

        name = self._get_available_name(name)
        name = self._save(name, content)

        # Store filenames with forward slashes, even on Windows
        return force_text(name.replace('\\', '/'))

    def _save(self, name, content, *args, **kwargs):
        try:
            return super(HashedNameFileSystemStorage,
                         self)._save(name, content, *args, **kwargs)
        except NoAvailableName:
            # File already exists, so we can safely do nothing
            # because their contents match. Raises if uniquify_names is False.
            pass
        except OSError, e:
            # We have a safe storage layer and file exists, else raise.
            if e.errno != EEXIST:
                raise

        return name
