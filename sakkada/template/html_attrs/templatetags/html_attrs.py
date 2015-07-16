from django.template import Library
from django.template.defaultfilters import stringfilter
from django.forms.forms import BoundField
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
import re

REGEX = re.compile(r"""([a-z0-9_]+) \s*=\s* ("|')? (?(2) (?:(.+?)(?<!\\)\2) | ([^\s'"]+))""", re.I | re.X)
RECLS = re.compile(r"""(?:^|\s+)([+-=]?)(-?[_a-z]{1}[a-z0-9-_]*)""", re.I)
RETAG = r"""<(?!/)(%s[^>?]*)/?>"""
NONE  = 'None'

register = Library()

@register.filter
@stringfilter
def html_attrs(field, extra=None):
    """Html attrs filter"""
    if not extra: return field
    extra, regex, sl_ob = regex_parser(extra)
    tags = re.finditer(RETAG % regex, field, re.I|re.X)
    tags = list(tags).__getitem__(sl_ob)
    html = field
    if tags:
        index, html  = 0, ''
        extra = extra and params_parser(extra)
        excls = cssclass_parser(extra.pop('class', False))
        for i in tags:
            tag = i.group()[1:-1].strip('/ ').split(' ', 1)
            name, attrs = len(tag) == 2 and tag or (tag[0], '')
            slash = i.group()[-2] == '/' and ' /' or ''
            attrs = attrs and params_parser(attrs) or {}
            csscl = cssclass_processor(excls, attrs.get('class', ''))
            csscl and attrs.__setitem__('class', csscl)
            attrs = params_processor(attrs, extra) or attrs
            html += field[index:i.start()] + ("<%s%s%s>" % (name, flatatt(attrs), slash))
            index = i.end()
        html += field[index:]
    return mark_safe(html)

@register.filter
def attrs(field, extra):
    """Field attrs filter"""
    if not isinstance(field, BoundField):
        return field

    as_fi = False
    if extra[-9:] == ' as field':
        extra, as_fi = extra[:-9], True
    attrs = params_processor(field.field.widget.attrs, extra)

    if attrs and as_fi:
        field.field.widget.attrs = attrs
    elif attrs:
        bound, wattr = field, field.field.widget.attrs
        bound.field.widget.attrs = attrs
        field = bound.as_widget()
        bound.field.widget.attrs = wattr
    return field

def regex_parser(extra):
    """Get extra attrs and tag regex"""
    params = extra.rsplit('|', 1)
    if len(params) == 2:
        regex, extra = params
        if regex[-1] == ']':
            regex, slices = regex.rsplit('[', 1)
            try:
                # try to get slice object from string
                slices = slices[:-1].split(':')[:3]
                slices = [int(i) if i else None for i in slices]
                # imitate direct indexing if no ":" char exist because of stop param in slice
                # is default, see also http://docs.python.org/library/functions.html#slice
                slices.__len__() == 1 and slices.append(None)
            except ValueError, e:
                slices = (None,)
        else:
            slices = (None,)
    else:
        regex = 'a-z{1}\w*'
        slices = (None,)
    return extra, regex, slice(*slices)

def params_parser(extra):
    """Parse string params into dict"""
    extra = re.findall(REGEX, extra)
    extra = dict([(i[0], i[2] or i[3]) for i in extra]) if extra else {}
    return extra

def params_processor(attrs, extra):
    """Process html tag params"""
    extra = extra and (params_parser(extra) if isinstance(extra, basestring) else dict(extra)) or None
    attrs = attrs and (params_parser(attrs) if isinstance(attrs, basestring) else dict(attrs)) or {}
    if not extra: return None

    extra['class'] = cssclass_parser(extra.get('class'))
    extra['class'] = cssclass_processor(extra['class'], attrs.get('class'))
    for i in extra.items():
        if not i[1]: continue
        attrs.__setitem__(*i) if i[1] != NONE else attrs.pop(i[0], None)
    return attrs

def cssclass_parser(extra):
    """Parse string param with some rules"""
    extra = extra and re.findall(RECLS, extra) or []
    extra = extra and [(c[0] or '+', c[1]) for c in extra]
    return extra

def cssclass_processor(extra, cattr):
    """Process class param with some rules"""
    if not extra: return cattr
    cattr = set(cattr and cattr.split() or [])

    if extra[0][0] == '=':
        cattr = set([extra[0][1]])
        extra = extra[1:]
    if extra:
        mdict = {'+': 'add', '=': 'add', '-': 'discard'}
        for i in extra:
            getattr(cattr, mdict[i[0]])(i[1])
    return ' '.join(sorted(cattr)).strip()
