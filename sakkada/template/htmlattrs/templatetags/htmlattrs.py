import re
import copy
import types
from functools import reduce
from django.template import Library, Node, TemplateSyntaxError
from django.template.base import FilterExpression
from django.forms.forms import BoundField
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.utils.html import format_html
from django.conf import settings


# Settings section
# ----------------
# REATTRS - parse string with multiple html attrs, allow "+" sign around "="
# REATTRSSTRICT - same as REATTRS, but without "+" near "=", only clear attrs
# REATTR - parse single attr value, work like REATTRS ("+" sign allowed), but
#          without spaces near signs and without surround spaces,
#          used for checking attr strings parsed by django template engine,
#          raise error if not matched and DEBUG mode is on
# RECLASS - parse css classes, allow "!" sign to remove specified class
# RETAG - parse common opening html tag

REATTRS = re.compile(
    '(?:^|\\s)'  # start from start-of-line or with space char
    '([a-z0-9_:\\.-]+)'  # take attr name (g1)
    '(?: \\s*(\\+=|=\\+|=)\\s*'  # take attr sign, "+=", "=+" or "=" (g2)
    '  (?: ("|\')(.*?)(?<!\\\\)\\3 | ([^\\s"\'][^\\s]*)(?=\\s|$) )'
    # try to take left quote (g3), if left quote is taken, try to take anything
    # upto right quote, which is not prepended by slash (g4), else try to take
    # any chars, except spaces and quotes upto any space or end-of-line (g5)
    ')?'
    '(?(2) |(?=\\s|$))',
    # if sign+value part is not presented, check that space char or end-of-line
    # located after attr-name (support for html5 boolean attrs)
    re.I | re.X)
REATTRSSTRICT = re.compile(
    # same as REATTRS but for parse attrs in html source strings for htmlattrs
    # filter, main difference is that this regex do not allow "+" signs around
    # "=" sign (strict html)
    '(?:^|\\s)'
    '([a-z0-9_:\\.-]+)'
    '(?: \\s*(=)\\s*'
    '  (?: ("|\')(.*?)(?<!\\\\)\\3 | ([^\\s"\'][^\\s]*)(?=\\s|$) )'
    ')?'
    '(?(2) |(?=\\s|$))',
    re.I | re.X)
REATTR = re.compile(
    '^'  # start from start-of-line or with space char
    '([a-z0-9_:\\.-]+)'  # take attr name (g1)
    '(?: (\\+=|=\\+|=)'  # take attr sign (g2)
    '  (?: ("|\')(.*?)(?<!\\\\)\\3 | ([^\\s"\'][^\\s]*)(?=$) )'
    # try to take left quote (g3), if left quote is taken, try to take anything
    # upto right quote, which is not prepended by slash (g4), else try to take
    # any chars with no starting quote and without spaces upto end-of-line (g5)
    ')?'
    '(?(2) |(?=$))',
    re.I | re.X)
RECLASS = re.compile(
    '(?:^|\\s)'  # start from start-of-line or with space char
    '(!?)'  # posible "!" sign ("!" - remove class, otherwise - add class)
    '(-?[a-z_][a-z0-9_-]*)(?=\\s|$)',
    # class name value, chars, digits, dashes and underscores,
    # should be followed only by end-of-line or space char
    re.I)
RETAG = '<(?!/)(%s[^>]*)/?>'  # just opening html tag

DEBUG = settings.DEBUG
CONTAINER = '__htmlattrs_container__'
NAMESPACES = ['main',]

ATTR_NAME_PARSER_CONFIG = getattr(settings,
                                  'HTMLATTRS_ATTR_NAME_PARSER_CONFIG', {
    # order for values checking if no param name specified, also all priority
    # params will be presented in result params (first value is default)
    'priority': ['ns', 'method', 'type',],
    # available values for params name detection if it not specified and also
    # for validation if param name in "strict" list
    'values': {
        'ns': ['main', 'empty', 'required', 'error', 'valid',],
        'method': ['set', 'setdefault', 'setifnochanged'],
        'type': ['string', 'classlist',],
    },
    # strict params should have value from "values" or error will be raised,
    # all strict params should be defined in "values" dict
    'strict': ['method', 'type',],
    # default values for specific attr names
    'preset': {
        'class': {'type': 'classlist',},
    },
})

# namespaces handler (generate all available namespaces)
NAMESPACES_HANDLER = getattr(
    settings, 'HTMLATTRS_NAMESPACES_HANDLER', 'base_namespaces_handler')

# allow empty quotes as value or just attr name, False by default
EMPTY_QUOTES = getattr(settings, 'HTMLATTRS_EMPTY_QUOTES', False)

# processors for each value type (whole import path or local function name)
ATTR_VALUE_PROCESSORS = getattr(settings, 'HTMLATTRS_ATTR_VALUE_PROCESSORS', {
    'string': 'string_value_processor',
    'classlist': 'classlist_value_processor',
})

# string value processor internal config
STRING_VALUE = {
    'sign_templates': {
        '+=': '{} {?}{=}',
        '=+': '{=}{?} {}',
    },
    'replacements': (
        ('<{}>', '<####>', '{}',),
        ('<{?}>', '<##?##>', '{?}',),
        ('<{=}>', '<##=##>', '{=}',),
    ),
}

WIDGET_EMPTY_CLASS = getattr(
    settings, 'HTMLATTRS_WIDGET_EMPTY_CLASS', 'WIDGET_EMPTY_CLASS')
WIDGET_ERROR_CLASS = getattr(
    settings, 'HTMLATTRS_WIDGET_ERROR_CLASS', 'WIDGET_ERROR_CLASS')
WIDGET_REQUIRED_CLASS = getattr(
    settings, 'HTMLATTRS_WIDGET_REQUIRED_CLASS', 'WIDGET_REQUIRED_CLASS')

# runtime values
attr_value_processors = {}
namespaces_handler = None
settings_prepared = False

register = Library()


# Utils section
# -------------
def import_or_local_setting(value):
    """Import setting value or get from module scope."""
    return value if callable(value) else (
        import_string(value) if '.' in value else globals()[value]
    )

def attrs_parser(extra, strict=False):
    """Parse attrs string into tuple of (name, sign, value,)."""
    values = {u'None': None, u'': True,}

    extra = re.findall(REATTRS if not strict else REATTRSSTRICT, extra)
    extra = ([(i[0], i[1], i[3] or values.get(i[4], i[4]),)
              for i in extra]) if extra else []
    return extra

def attrs_processor(extra, attrs, original_attrs=None, container=None):
    """Process html tag attrs with extra new values."""
    if not extra:
        return attrs

    attrs, container = attrs or {}, container or {}
    # get original attrs (for method processing) from kwarg or widget
    if original_attrs is None:
        original_attrs = (container['original'].field.widget.attrs
                          if container.get('original', None) else {})

    config = container.get('config', ATTR_NAME_PARSER_CONFIG)
    extra_params, ns = [], {}
    for name, sign, value in extra:
        name, params = attr_name_parser(name, config)
        if name is None:
            continue
        if 'extra' in params:
            extra_params.append((name, value, params, sign,))
            continue
        elif params['ns'] not in ns:
            ns[params['ns']] = {}
        ns[params['ns']][name] = (name, value, params, sign,)

    # set extra params to target attrs
    for name, value, params, sign in extra_params:
        if params['ns'] in ns and name in ns[params['ns']]:
            ns[params['ns']][name][2][params['extra']] = value
        elif DEBUG:
            raise ValueError('htmlattrs: extra param "%s" for attr "ns:%s %s"'
                             ' is invalid, target attr is not defined.'
                             % (params['extra'], params['ns'], name,))

    # process values in namespaces by namespace order
    nsordering = config['values']['ns']
    namespaces = container.get('namespaces', NAMESPACES)
    for namespace in nsordering:
        # ignore absent namespace attrs (should be defined both in field
        # and in attrs value to be processed)
        if not namespace in namespaces or not namespace in ns:
            continue
        namespace = ns[namespace]
        for key, attr in namespace.items():
            if attr[1] is None:
                # drop attr if value is None
                attrs.pop(key, None)
            else:
                # check attr "method" param - method of value setting
                attrsval = attrs.get(key, None)
                if attrsval and ((attr[2]['method'] == 'setdefault') or
                                 (attr[2]['method'] == 'setifnochanged' and
                                  original_attrs.get(key, None) != attrsval)):
                    continue

                # set value via specified value type processor
                attrs[key] = attr_value_processors[attr[2]['type']](attr, attrs)

    return attrs

def attr_name_parser(value, config):
    """Parse attr name according attr name parser config."""
    priority, values = config['priority'], config['values']
    strict, preset = config['strict'], config['preset'] or {}

    extra = value.split('::', 1)
    extra, name = extra[0] if len(extra) == 2 else None, extra[-1]
    extra = extra.split(':') if extra else []

    params = {}
    for param in extra:
        param = param.split('.', 1)
        pname, pvalue = param[0] if len(param) == 2 else None, param[-1]

        # try to get param name by value from "values" by "priority"
        if not pname:
            for i in priority:
                if pvalue in values[i]:
                    pname = i
                    break
            if not pname and DEBUG:
                raise ValueError('htmlattrs: value "%s" is invalid in'
                                 ' "%s" attr.' % (pvalue, value))
        # validate "priority" params values by "values"
        elif pname in strict and not pvalue in values[pname]:
            if DEBUG:
                raise ValueError('htmlattrs: value "%s" is invalid in'
                                 ' "%s" attr, allowed values are "%s".'
                                 % (pvalue, value, ', '.join(values[pname]),))
            pname = None
        # set value if it valid
        if pname:
            params[pname] = pvalue

    for i in priority:
        if i not in params:
            params[i] = preset.get(name, {}).get(i, values[i][0])

    # extra params should not be one of "values"
    if 'extra' in params and params['extra'] in values:
        if DEBUG:
            raise ValueError('htmlattrs: extra param name "%s" is invalid in'
                            ' "%s" attr, it should not be one of "%s".'
                            % (pvalue, value, ', '.join(values.keys()),))
        else:
            name = params = None  # ignore attr

    return (name, params,)

def regex_with_attrs_parser(extra):
    """
    Parse regex string with attrs for htmlattrs filter and tag.
    Takes regex-with-attr string and return attrs as string, regex string and
    slice python object.

    Get extra attrs and regex with slice from string value by pattern:
        [[<{separater}>]regex[{slice}]{separater}]attrs
    Defaults:
        separater   - "|"
        regex       - [a-z]{1}\\w*
        slice       - [:] (slice(None), whole list)
    Examples:
        input|class="red"
        input[1:]|class="blue"
        <@>(?:input|select)[1]@title="some | title" # when "|" used in attrs
    """
    original = extra
    if extra[0] != '<':
        extra = '<|>%s' % extra
    elif not '>' in extra:
        if DEBUG:
            raise ValueError('htmlattrs: htmlattrs filter regex definition'
                             ' error - ">" char missed')
        return ('', '', slice(None),)

    split = extra[extra.index('>')+1:].rsplit(extra[1:extra.index('>')], 1)
    if len(split) == 2:
        regex, extra = split
    else:
        regex, extra = '[a-z]{1}\\w*', original
    regex, sliceobj = regex_parser(regex)
    return extra, regex, sliceobj

def regex_parser(regex):
    """
    Parse regex string for htmlattrs filter and tag.
    Divide input string into regex string and slice python object.

    Get regex with slice from string value by pattern:
        regex[{slice}]
    Defaults:
        slice       - [:] (slice(None), whole list)
    Examples:
        input
        input[1:]
        (?:input|select)[1]
    """
    if regex and regex[-1] == ']' and '[' in regex:
        original, (regex, sliceobj,) = regex, regex.rsplit('[', 1)
        try:
            # try to get slice object from string
            sliceobj = sliceobj[:-1].split(':')[:3]
            sliceobj = [int(i) if i else None for i in sliceobj]
            # imitate direct indexing if no ":" char exist because
            # stop param in slice is default, see also
            # http://docs.python.org/library/functions.html#slice
            len(sliceobj) == 1 and sliceobj.append(sliceobj[0]+1 or None)
        except ValueError as e:
            regex = original  # revert original regex
            sliceobj = (None,)
    else:
        sliceobj = (None,)
    return regex, slice(*sliceobj)

def monkey_patch_bound_field(field):
    """
    Update (ok, monkey patch) bound field instance (once).
    Patch "as_widget" method for consuming updated attrs value
    and add CONTAINER attribute for storing and htmlattrs specific data.
    """
    if hasattr(field, CONTAINER):
        return field

    # get namespace list and attrname config dict
    config = copy.deepcopy(ATTR_NAME_PARSER_CONFIG)
    namespaces = namespaces_handler(field)

    # copy bound field and set container
    field, original = copy.copy(field), field
    field.__setattr__(CONTAINER, {
        'original': original, 'config': config,
        'namespaces': namespaces, 'attrs': None,
    })

    # extend any data in CONTAINER for current field if required
    if hasattr(field.form, 'extend_htmlattrs_field_container'):
        field.form.extend_htmlattrs_field_container(field)

    # patch as_widget method to consume updated attrs
    def as_widget(self, widget=None, attrs=None, only_initial=False):
        container = getattr(self, CONTAINER)
        widget = widget or self.field.widget

        # replace widget attrs with modified by template filter/tag to allow
        # removing attrs by attr=None method and revert backward after render
        if container['attrs']:
            widget.attrs, original_attrs = container['attrs'], widget.attrs
        result = container['original'].as_widget(widget, attrs, only_initial)
        if container['attrs']:
            widget.attrs = original_attrs
        return result
    field.as_widget = types.MethodType(as_widget, field)

    return field


# Value types processors and namespaces handler
# ---------------------------------------------
def string_value_processor(attr, attrs):
    """Process string value type with value inheritance."""
    name, value, params, sign = attr
    previous = attrs.get(name, '')

    # inheritance: template first, sign second, value with {} third
    # anchors surrounded by <> will be escaped with replacements
    if 'template' in params:
        template = reduce(lambda x, y: x.replace(*y[:2]),
                          STRING_VALUE['replacements'], params['template'])
    elif '+' in sign:
        template = STRING_VALUE['sign_templates'][sign]
    elif value is True:
        template = None
    elif value == '' and not EMPTY_QUOTES:
        template = None
        value = True
    else:
        template = reduce(lambda x, y: x.replace(*y[:2]),
                          STRING_VALUE['replacements'], value)
        if '{}' not in template:
            template = None
        else:
            value = ''

    if not template:
        return value

    # process pattern anchors
    tpl, prev = [i.split('{?}') for i in template.split('{}')], bool(previous)
    for i in range(1, len(tpl)):
        l, r, rwhole = tpl[i-1], tpl[i], len(tpl[i])<3 or i==len(tpl)-1

        if len(l) > 1:  # left segment
            l[:] = [''.join(l[0:None if prev else 1])]

        if len(r) > 1:  # right segment
            r[0:None if rwhole else -1] = [''.join(r[
                0 if prev else (-1 if rwhole else -2):None if rwhole else -1
            ])]

    # compile result value and restore escaped anchors
    value = previous.join(i[0] for i in tpl).replace('{=}', value)
    value = reduce(lambda x, y: x.replace(*y[1:]),
                   STRING_VALUE['replacements'], value)
    return value

def classlist_value_processor(attr, attrs):
    """Process class list value type."""
    name, value, params, sign = attr
    previous = attrs.get(name, '')

    # parse class attr value by RECLASS, get clist value according sign
    # and previous class attr value and set methods dict (add or remove)
    value = value and re.findall(RECLASS, value) or []
    clist = set(previous.split() if '+' in sign and previous else [])
    mdict = {'': 'add', '!': 'discard',}

    # remove class if it prepended by "!" or add otherwise
    if value:
        for i in value:
            getattr(clist, mdict[i[0]])(i[1])

    # return sorted class list joined by space
    return u' '.join(sorted(clist)).strip()

def base_namespaces_handler(boundfield):
    """
    Common namespaces handler.
    Add all available namespaces for current field to namespaces list.
    If it's required to change behaviour for particular field, add
    method "extend_htmlattrs_field_container" instead of this function.
    May be changed by HTMLATTRS_NAMESPACES_HANDLER setting.
    """
    namespaces = list(NAMESPACES)
    boundfield.data or namespaces.append('empty')
    boundfield.field.required and namespaces.append('required')
    boundfield.errors and namespaces.append('error')
    boundfield.data and not boundfield.errors and namespaces.append('valid')
    return namespaces

def flatatt(attrs):
    # similar to builtin flatatt, but without sorting final attrs
    data = [(' {}' if value is True else ' {}="{}"', (attr, value,),)
            for attr, value in attrs.items() if not value in (False, None,)]
    return mark_safe(''.join(format_html(template, *tuple(args))
                             for template, args in data))


# Initial configuration
# ---------------------
# prepare functions for value processing (import from string)
if not settings_prepared:
    # prepare all available attr value processors
    for key, value in ATTR_VALUE_PROCESSORS.items():
        attr_value_processors[key] = import_or_local_setting(value)
    # prepare namespaces generater
    namespaces_handler = import_or_local_setting(NAMESPACES_HANDLER)

    # prepare only once
    settings_prepared = True


# Template tags
# -------------
@register.tag(name='attrs')
def attrs_tag(parser, token):
    """
    BoundField attrs template tag.
    Works similar to "attrs" filter, but can receive template variables,
    translates, etc. as attrs values. Also may return result field into
    template context, just by adding "as {varname}" appendix (like in builtin
    django tags).
    """
    errors = {
        'invalid_attr' : ('htmlattrs: attrs template tag error - attrs should'
                          ' be in "\\w-_.:[=value]" format, not "%s".'),
        'missing_args' : ('htmlattrs: attrs template tag error - too few'
                          ' reveived arguments, should be at least one.')
    }

    bits, asvar = token.split_contents(), None
    if len(bits) == 1:
        raise TemplateSyntaxError(errors['missing_args'])
    if len(bits) >= 4 and bits[-2] == 'as':
        bits, asvar = bits[:-2], bits[-1]

    boundfield, attrs = bits[1], bits[2:]
    boundfield = parser.compile_filter(boundfield)

    extra, values = [], {u'None': None, None: True,}
    for attr in attrs:
        match = REATTR.match(attr)
        if not match:
            if DEBUG:
                raise TemplateSyntaxError(errors['invalid_attr'] % attr)
            continue
        i = match.groups()
        name, sign, value = i[0], i[1] or '', i[3] if i[2] else (
            values[i[4]] if i[4] in values else parser.compile_filter(i[4])
        )
        extra.append([name, sign, value,])

    return AttrsNode(boundfield, extra, asvar)


class AttrsNode(Node):
    def __init__(self, field, extra, asvar):
        self.field = field
        self.extra = extra
        self.asvar = asvar

    def render(self, context):
        boundfield = self.field.resolve(context)
        extra = [[name, sign, (force_text(value.resolve(context))
                               if isinstance(value, FilterExpression) else
                               value),]
                 for name, sign, value in self.extra]

        # widget tweaks idea: if variable exist -> set ns::class value
        # insert instead of append to allow redefine ns::class value in tag
        if WIDGET_EMPTY_CLASS in context:
            extra.insert(0, ['empty::class', '+=',
                             context[WIDGET_EMPTY_CLASS],])
        if WIDGET_ERROR_CLASS in context:
            extra.insert(0, ['error::class', '+=',
                             context[WIDGET_ERROR_CLASS],])
        if WIDGET_REQUIRED_CLASS in context:
            extra.insert(0, ['required::class', '+=',
                             context[WIDGET_REQUIRED_CLASS],])

        if not isinstance(boundfield, BoundField) or not extra:
            return boundfield

        boundfield = monkey_patch_bound_field(boundfield)
        container = getattr(boundfield, CONTAINER)
        attrs = container['attrs'] or dict(boundfield.field.widget.attrs)
        attrs = attrs_processor(extra, attrs, container=container)
        container['attrs'] = attrs

        if self.asvar:
            context[self.asvar] = boundfield
            return ''
        return boundfield


@register.tag(name='htmlattrs')
def htmlattrs_tag(parser, token):
    """
    Html tags attrs template tag.
    Works similar to "htmlattrs" filter, but can receive template variables,
    translates, etc. as attrs values. Also may return result string into
    template context, just by adding "as {varname}" appendix (like in builtin
    django tags).
    """
    errors = {
        'invalid_attr' : ('htmlattrs: htmlattrs template tag error - attrs'
                          ' should be in "\\w-_.:[=value]" format, not "%s".'),
        'missing_args' : ('htmlattrs: attrs template tag error - too few'
                          ' reveived arguments, should be at least two.')
    }

    bits, asvar = token.split_contents(), None
    if len(bits) < 3:
        raise TemplateSyntaxError(errors['missing_args'])
    if len(bits) >= 5 and bits[-2] == 'as':
        bits, asvar = bits[:-2], bits[-1]

    html, regex, attrs = (parser.compile_filter(bits[1]),
                          parser.compile_filter(bits[2]), bits[3:],)

    withfield = None
    if len(attrs) >= 2 and attrs[0] == 'with':
        withfield, attrs = attrs[1], attrs[2:]
        withfield = parser.compile_filter(withfield)

    extra, values = [], {u'None': None, None: True,}
    for attr in attrs:
        match = REATTR.match(attr)
        if not match:
            if DEBUG:
                raise TemplateSyntaxError(errors['invalid_attr'] % attr)
            continue
        i = match.groups()
        name, sign, value = i[0], i[1] or '', i[3] if i[2] else (
            values[i[4]] if i[4] in values else parser.compile_filter(i[4])
        )
        extra.append([name, sign, value,])

    return HtmlAttrsNode(html, extra, regex, withfield, asvar)


class HtmlAttrsNode(Node):
    def __init__(self, html, extra, regex, withfield, asvar):
        self.html = html
        self.extra = extra
        self.regex = regex
        self.withfield = withfield
        self.asvar = asvar

    def render(self, context):
        html, regex = (force_text(self.html.resolve(context)),
                       force_text(self.regex.resolve(context)),)
        regex, sliceobj = regex_parser(regex)

        container = None
        withfield = self.withfield and self.withfield.resolve(context)
        if isinstance(withfield, BoundField):
            withfield = monkey_patch_bound_field(withfield)
            container = getattr(withfield, CONTAINER)

        extra = [[name, sign, (force_text(value.resolve(context))
                               if isinstance(value, FilterExpression) else
                               value),]
                 for name, sign, value in self.extra]

        # widget tweaks idea: if variable exist -> set ns::class value
        # insert instead of append to allow redefine ns::class value in tag
        if WIDGET_EMPTY_CLASS in context:
            extra.insert(0, ['empty::class', '+=',
                             context[WIDGET_EMPTY_CLASS],])
        if WIDGET_ERROR_CLASS in context:
            extra.insert(0, ['error::class', '+=',
                             context[WIDGET_ERROR_CLASS],])
        if WIDGET_REQUIRED_CLASS in context:
            extra.insert(0, ['required::class', '+=',
                             context[WIDGET_REQUIRED_CLASS],])

        if not regex or not extra:
            return html

        tags = re.finditer(RETAG % regex, html, re.I)
        tags = list(tags)[sliceobj]
        if not tags:
            return html

        index, compiled = 0, []
        for i in tags:
            # iterate over finded tags and replace each one in original html
            # with new tags strings with updated attrs
            tag = i.group()[1:-1].strip('/ ').split(' ', 1)
            tag, attrs = tag if len(tag) == 2 else (tag[0], '')
            slash = i.group()[-2] == '/' and ' /' or ''
            attrs = attrs and attrs_parser(attrs, strict=True) or {}
            attrs = attrs_processor(extra, {i[0]:i[2] for i in attrs},
                                    original_attrs=attrs,
                                    container=container) or attrs
            compiled.extend([html[index:i.start()],
                             ("<%s%s%s>" % (tag, flatatt(attrs), slash))])
            index = i.end()
        compiled.append(html[index:])
        compiled = mark_safe(u''.join(compiled))

        if self.asvar:
            context[self.asvar] = compiled
            return ''
        return compiled


# Template filters
# ----------------
@register.filter
def attrs(field, extra=None):
    """BoundField attrs template filter."""
    if not isinstance(field, BoundField) or not extra:
        return field
    field = monkey_patch_bound_field(field)

    container = getattr(field, CONTAINER)
    attrs = container['attrs'] or dict(field.field.widget.attrs)  # copy
    extra = attrs_parser(extra)
    attrs = attrs_processor(extra, attrs, container=container)
    container['attrs'] = attrs

    return field

@register.filter
def htmlattrs(html, extra=None):
    """Html tags attrs template filter."""
    container = None
    if isinstance(html, dict) and html['unique'] == CONTAINER:
        # if value from withfield filter, get container
        withfield, html = html['field'], html['html']
        withfield = monkey_patch_bound_field(withfield)
        container = getattr(withfield, CONTAINER, None)

    if not isinstance(html, str):
        html = mark_safe(force_text(html))
    if not extra:
        return html

    extra, regex, sliceobj = regex_with_attrs_parser(extra)
    if not regex or not extra:
        return html

    tags = re.finditer(RETAG % regex, html, re.I)
    tags = list(tags)[sliceobj]
    if not tags:
        return html

    index, compiled = 0, []
    extra = attrs_parser(extra)
    for i in tags:
        # iterate over finded tags and replace each one in original html
        # with new tags strings with updated attrs
        tag = i.group()[1:-1].strip('/ ').split(' ', 1)
        tag, attrs = tag if len(tag) == 2 else (tag[0], '')
        slash = i.group()[-2] == '/' and ' /' or ''
        attrs = attrs and attrs_parser(attrs, strict=True) or []
        attrs = attrs_processor(extra, {i[0]:i[2] for i in attrs},
                                original_attrs=attrs,
                                container=container) or attrs
        compiled.extend([html[index:i.start()],
                         ("<%s%s%s>" % (tag, flatatt(attrs), slash))])
        index = i.end()
    compiled.append(html[index:])

    # return safe compiled html string
    return mark_safe(u''.join(compiled))

@register.filter
def withfield(html, field=None):
    """Template filter for providing BoundField into htmlattrs filter."""
    if not isinstance(field, BoundField):
        return html
    return {'html': html, 'field': field, 'unique': CONTAINER,}

@register.filter(name='field_type')
def field_type(field):
    """
    Template filter that returns field class name (in lower case).
    E.g. if field is CharField then {{ field|field_type }} will
    return 'charfield'.
    """
    return (field.field.__class__.__name__.lower()
            if isinstance(field, BoundField) else '')

@register.filter(name='widget_type')
def widget_type(field):
    """
    Template filter that returns field widget class name (in lower case).
    E.g. if field's widget is TextInput then {{ field|widget_type }} will
    return 'textinput'.
    """
    return (field.field.widget.__class__.__name__.lower()
            if isinstance(field, BoundField) else '')

@register.filter
def widget_render_context(field, extra=None):
    """Get context from widget's render method directly to template."""
    if not isinstance(field, BoundField):
        return {}

    # input extra params
    extra = ({i[0]: i[2] for i in attrs_parser(extra, strict=True)}
             if extra else {})
    only_initial = extra.get('only_initial', False)
    widget = extra.get('widget', None)
    widget = (import_string(widget if '.' in widget else
                            'django.forms.%s' % widget)()
              if widget else None)

    if not widget:
        widget = field.field.widget
    if field.field.localize:
        widget.is_localized = True

    name = field.html_initial_name if only_initial else field.html_name

    # get attrs, try to get attrs from monkeypathed field first
    attrs = container = getattr(field, CONTAINER, {}).get('attrs', {})
    attrs = field.build_widget_attrs(attrs, widget)
    auto_id = field.auto_id
    if auto_id and 'id' not in attrs and 'id' not in widget.attrs:
        attrs['id'] = field.html_initial_id if only_initial else auto_id

    return widget.get_context(name, field.value(), attrs)
