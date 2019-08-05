"""
ColorizedFormatter
------------------

Usage.

In formatters section of LOGGING settings:

    ...
    'formatters': {
        ...
        'app.console': {
            '()': 'sakkada.utils.log.ColorizedFormatter',
            'format': '{lvl.color}{lvl.title}{p.r}: {p.ywb}{message}{p.r} '
                      '({p.yw}{asctime}{p.r}{p.we},{p.r} '
                      '{p.cn}{name}{p.r}{p.we}:{p.r}{p.gn}{funcName}{p.r}'
                      '{p.we}:{p.r}{p.yw}{lineno}{p.r})',
            'datefmt' : "%d.%m.%Y %H:%M:%S",
            'style': '{',
        },
        'app.console.sql': {
            '()': 'sakkada.utils.log.ColorizedFormatter',
            'format': '{p.cnb}SQL{p.r}: {p.we}{message}{p.r}',
            'style': '{',
        },
    },
    ...

"""

import logging
import collections
from django.core.management.color import supports_color


Level = collections.namedtuple('Level', ['title', 'color',])

Palette = collections.namedtuple('Palette', [
    'bk', 'rd', 'gn', 'yw', 'be', 'ma', 'cn', 'we',
    'bkb', 'rdb', 'gnb', 'ywb', 'beb', 'mab', 'cnb', 'web', 'r',
])

colorpalette = Palette(**{
    'bk': '\x1b[30;2m',
    'rd': '\x1b[31;2m',
    'gn': '\x1b[32;2m',
    'yw': '\x1b[33;2m',
    'be': '\x1b[34;2m',
    'ma': '\x1b[35;2m',
    'cn': '\x1b[36;2m',
    'we': '\x1b[37;2m',
    'bkb': '\x1b[30;1m',
    'rdb': '\x1b[31;1m',
    'gnb': '\x1b[32;1m',
    'ywb': '\x1b[33;1m',
    'beb': '\x1b[34;1m',
    'mab': '\x1b[35;1m',
    'cnb': '\x1b[36;1m',
    'web': '\x1b[37;1m',
    'r': '\x1b[0m',
})

bandwpalette = Palette(**{
    'bk': '',
    'rd': '',
    'gn': '',
    'yw': '',
    'be': '',
    'ma': '',
    'cn': '',
    'we': '',
    'bkb': '',
    'rdb': '',
    'gnb': '',
    'ywb': '',
    'beb': '',
    'mab': '',
    'cnb': '',
    'web': '',
    'r': '',
})


class ColorizedFormatter(logging.Formatter):
    levels = {
        'DEBUG': {'title': 'DBG', 'color': 'gnb',},
        'INFO': {'title': 'INF', 'color': 'cnb',},
        'WARNING': {'title': 'WRN', 'color': 'ywb',},
        'ERROR': {'title': 'ERR', 'color': 'rdb',},
        'CRITICAL': {'title': 'CRT', 'color': 'rdb',},
        'NOTSET': {'title': 'NST', 'color': 'bc',},
    }

    def __init__(self, *args, **kwargs):
        self.palette = colorpalette if supports_color() else bandwpalette
        super().__init__(*args, **kwargs)

    def format(self, record):
        leveldata = self.levels.get(record.levelname)

        record.p = self.palette
        record.lvl = Level(title=leveldata['title'],
                           color=getattr(self.palette, leveldata['color']))
        if record.exc_text:
            record.exc_text = '\n'.join((
                self.palette.rdb + '===' + self.palette.r,
                self.palette.ywb + record.exc_text + self.palette.r,
            ))

        return super().format(record)
