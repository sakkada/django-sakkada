import os
import re
import sys
from django.db import models
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files.storage import FileSystemStorage
from django.utils.functional import LazyObject


def get_storage_by_field(field):
    if isinstance(field.storage, LazyObject):
        # field.storage._wrapped or field.storage._setup()
        field.storage._setup()
        storage = field.storage._wrapped
    else:
        storage = field.storage
    return storage


class Command(BaseCommand):
    help = "Get files list that no longer have an db entry."

    def add_arguments(self, parser):
        parser.add_argument(
            '-r', '--regex', dest='regex', default='none', help=(
                "Regex for directory search list."
                "Directory names starts with no slash, after media_root directory. "
                "If media_root at '/home/django/site/public_html/media/', and "
                "directories in it are 'static' and 'upload', regex for 'upload' "
                "will be like '^upload(/|$).*$', default 'none' (raise error)."
            )
        )

        parser.add_argument('-l', '--list', dest='list', default='fs', help=(
            "Response data type (fs/db/dirs/nodirs): "
            "fs=files on filesystem that no longer have an db entry; "
            "fsall=all files on filesystem; "
            "db=filefields in database that no longer have an fs entry; "
            "dball=all filefields in database; "
            "dbfs=filefields in database that have an db entry; "
            "dirs=directories for search files; "
            "nodirs=directories excluded from search list by regex. Default 'fs'."
        ))

    def handle(self, *args, **options):
        # filename = None if options['filename'] == 'none' else options['filename']
        result = options['list']
        regex = None if options['regex'] == 'none' else options['regex']
        if result not in ['fs', 'fsall', 'db', 'dball', 'dbfs', 'dirs', 'nodirs']:
            sys.stdout.write(
                "Use only 'fs', 'fsall', 'db', 'dball', 'dbfs', "
                "'dirs', 'nodirs' for -l param."
                "\nUse 'python manage.py help files_clean' for help message.")
            return
        if not regex:
            sys.stdout.write(
                "Regex param (-r) is required."
                "\nUse 'python manage.py help files_clean' for help message."
                "\nExample: \"^upload/(?!upload(/|$)).*$\"")
            return

        registry, dbfilesmeta, dbfiles, fsfiles = {}, {}, [], []
        directories = {'allowed': [], 'disallowed': []}

        # TODO: use fs or db if it is really need
        #       fsall - no db, dball - no fs

        # get filesystem files list data
        # TODO: allow to set media_root customizible
        media_root = settings.MEDIA_ROOT.replace('\\', '/')
        for base, dirs, files in os.walk(media_root):
            root = base.replace('\\', '/').replace(media_root, '').lstrip('/')
            if not re.match(regex, root):
                directories['disallowed'].append(root)
                continue
            else:
                directories['allowed'].append(root)
            fsfiles += [os.path.join(media_root, root, i).replace('\\', '/') for i in files]
        fsfiles.sort()

        if result in ['dirs', 'nodirs']:
            sys.stdout.write('\n'.join(directories['allowed' if result == 'dirs' else 'disallowed']))
            return

        # get database files list data
        for model in apps.get_models():
            fields = dict([(f.name, f) for f in model._meta.fields if isinstance(f, models.FileField)])

            for name, field in fields.items():
                storage = get_storage_by_field(field)
                if not isinstance(storage, FileSystemStorage):
                    # TODO: allow to use other storage classes (may be for dbonly commands)
                    sys.stderr.write('Illegal fileField storage class "%s" (%s, %s).' %
                                     (storage.__class__.__name__, model.__name__, name))
                    fields.__delitem__(name)
                location = storage.location.replace('\\', '/')
                if not location.startswith(media_root):
                    sys.stderr.write('Illegal fileField storage location (%s, %s).\n'
                                     'Current:    %s\nMust be in: %s' %
                                     (model.__name__, name, location, media_root))
                    fields.__delitem__(name)

            if not fields or not model.objects.count():
                continue
            registry[model.__name__] = {'class': model, 'fields': fields,}

        for data in registry.values():
            model, fields = data['class'], data['fields']
            # todo: add isnull support
            excludes = dict([('%s__exact' % f.name, '') for f in fields.values()])
            values = model.objects.exclude(**excludes)\
                          .values('pk', *[f.name for f in fields.values()])

            for i in values:
                pk = i.pop('pk')
                for key, val in i.items():
                    if not val:
                        continue
                    val = os.path.join(settings.MEDIA_ROOT, val).replace('\\', '/')
                    entry = [model.__name__, model._meta.db_table, pk, key, val]
                    if val in dbfilesmeta:
                        dbfilesmeta[val].append(entry)
                    else:
                        dbfilesmeta[val] = [entry]

        dbfiles = [f for f in dbfilesmeta.keys()]
        dbfiles.sort()
        dbfiles = set(dbfiles)
        fsfiles = set(fsfiles)

        # fsfiles
        if result in ('fs', 'fsall'):
            if result == 'fs':
                difference = list(fsfiles-dbfiles)
            else:
                difference = list(fsfiles)
            difference.sort()

            sys.stdout.write('\n')
            sys.stdout.write('\n'.join(difference))
            return

        # dbfiles
        if result in ('db', 'dball', 'dbfs'):
            if result == 'db':
                difference = list(dbfiles-fsfiles)
            elif result == 'dball':
                difference = list(dbfiles)
            else:
                difference = list(dbfiles.intersection(fsfiles))
            difference.sort()

            sys.stdout.write('model_name\ttb_name\tid\tfield_name\tpath\tcount')
            for i in difference:
                sys.stdout.write('\n')
                sys.stdout.write('\n'.join([
                    '\t'.join([str(b) for b in (a+[len(dbfilesmeta[i])])]) for a in dbfilesmeta[i]
                ]))
            return
