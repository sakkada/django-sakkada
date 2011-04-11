from django.db import models
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os, re, pprint

class Command(BaseCommand):
    help = "Get files list that no longer have an db entry."

    option_list = BaseCommand.option_list + (
        make_option('-r', '--regex', dest='regex', default='none', help="Regex for directory search list. "
            "Directory names starts with no slash, after media_root directory. "
            "If media_root at '/home/django/site/public_html/media/', and directories in it are "
            "'static' and 'upload', regex for 'upload' will be like '^upload(/|$).*$', default 'none' (raise error)."
        ),

        make_option('-l', '--list', dest='list', default='fs', help="Response data type (fs/db/dirs/nodirs): "
            "fs=files on filesystem that no longer have an db entry; "
            "db=filefields in database that no longer have an fs entry; "
            "dirs=directories for search files; "
            "nodirs=directories excluded from search list by regex. Default 'fs'."
        ),
    )

    def handle(self, *args, **options):
        #filename    = None if options['filename'] == 'none' else options['filename']
        result  = options['list']
        regex   = None if options['regex'] == 'none' else options['regex']
        if result not in ['fs', 'db', 'dirs', 'nodirs']:
            print "Use only 'fs', 'db', 'dirs', 'nodirs' for -l param." \
                  "\nUse 'python manage.py help files_cleanup' for help message."
            return
        if not regex:
            print "Regex param (-r) is required." \
                  "\nUse 'python manage.py help files_cleanup' for help message." \
                  "\nExample: \"^upload/(?!upload(/|$)).*$\""
            return

        registry, dbfilesmeta, dbfiles, fsfiles, directories = {}, {}, [], [], {'allowed': [], 'disallowed': []}

        # get filesystem files list data
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
            print '\n'.join(directories['allowed' if result == 'dirs' else 'disallowed'])
            return

        # get database files list data
        for model in models.get_models():
            fields = dict([(f.name, f) for f in model._meta.fields if isinstance(f, models.FileField)])
            if not fields or not model.objects.count(): continue
            registry[model.__name__] = {'class': model, 'fields': fields}

        for data in registry.values():
            model, fields = data['class'], data['fields']
            values = model.objects.all().exclude(**dict([('%s__exact' % f.name, '') for f in fields.values()])).values('pk', *[f.name for f in fields.values()])
            for i in values:
                pk = i.pop('pk')
                for key, val in i.items():
                    val = val.encode('utf8')
                    val = os.path.join(settings.MEDIA_ROOT, val).replace('\\', '/')
                    entry = [model.__name__, model._meta.db_table, pk, key, val]
                    if dbfilesmeta.has_key(val):
                        dbfilesmeta[val].append(entry)
                    else:
                        dbfilesmeta[val] = [entry]

        dbfiles = [f for f in dbfilesmeta.keys()]
        dbfiles.sort()
        dbfiles = set(dbfiles)
        fsfiles = set(fsfiles)

        # fsfiles
        if result == 'fs':
            difference = list(fsfiles-dbfiles)
            difference.sort()
            print '\n'.join(difference)
            return

        # dbfiles
        if result == 'db':
            difference = list(dbfiles-fsfiles)
            difference.sort()
            print 'model_name\ttb_name\tid\tfield_name\tpath\tcount'
            for i in difference:
                print '\n'.join(['\t'.join([str(b) for b in (a+[len(dbfilesmeta[i])])]) for a in dbfilesmeta[i]])
            return