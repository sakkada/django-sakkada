import re
import django
from django.test import TestCase
from django import forms
from django.core import validators
from django.template import Template, Context
from sakkada.template.htmlattrs.templatetags import htmlattrs


class TestForm(forms.Form):
    required_field = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'red', 'size': '40',}),
        validators=[validators.RegexValidator('required-value')])
    optional_field = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'blue', 'size': '40',}),
        required=False)

    def extend_htmlattrs_field_container(self, field):
        container = getattr(field, htmlattrs.CONTAINER, {})
        # add valueis10 namespace to supported namespaces
        container['config']['values']['ns'].append('valueis10')


class RegexTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_REATTRS(self):
        checkers = [
            # value without spaces and starting quotes
            ('attr=any-~!@#$%^&*()_+}{:?><\'"-value',
             [('attr', '=', '', '', 'any-~!@#$%^&*()_+}{:?><\'"-value'),],),
            # value with quotes and without
            ('a=a b="b" c="c"d="d" e=e"e f="ff\\" ff" g=\'"g"\' h="h"# i="i j="j" k="k l=l\'',
             [('a', '=', '', '', 'a'), ('b', '=', '"', 'b', ''),
              ('c', '=', '"', 'c', ''), ('e', '=', '', '', 'e"e'),
              ('f', '=', '"', 'ff\\" ff', ''), ('g', '=', "'", '"g"', ''),
              ('h', '=', '"', 'h', ''), ('i', '=', '"', 'i j=', ''),
              ('l', '=', '', '', "l'"),],),
            # multiple also with spaces around sign
            ('a = a  b=b c= c d =d',
             [('a', '=', '', '', 'a'), ('b', '=', '', '', 'b'),
              ('c', '=', '', '', 'c'), ('d', '=', '', '', 'd'),],),
            # variant of sign
            ('a=a b+=b c=+c d+=+d e+ =e f=++f g++=g h==h',
             [('a', '=', '', '', 'a'), ('b', '+=', '', '', 'b'),
              ('c', '=+', '', '', 'c'), ('d', '+=', '', '', '+d'),
              ('f', '=+', '', '', '+f'), ('h', '=', '', '', '=h'),],),
            # attr name allowed chars
            ('any-_:.azAZ09-attr-name=value',
             [('any-_:.azAZ09-attr-name', '=', '', '', 'value'),],),
            # attr starts with space or at start-of-line and ends
            # at space or end-of-line if value and it without quotes
            ('a=a #b=b #c d e# f=f# g="g"#',
             [('a', '=', '', '', 'a'), ('d', '', '', '', ''),
              ('f', '=', '', '', 'f#'), ('g', '=', '"', 'g', ''),],),
        ]

        REATTRS = htmlattrs.REATTRS
        for pattern, results in checkers:
            self.assertEqual(REATTRS.findall(pattern), results)

    def test_REATTRSSTRICT(self):
        checkers = [
            # value without spaces and starting quotes
            ('attr=any-~!@#$%^&*()_+}{:?><\'"-value',
             [('attr', '=', '', '', 'any-~!@#$%^&*()_+}{:?><\'"-value'),],),
            # value with quotes and without
            ('a=a b="b" c="c"d="d" e=e"e f="ff\\" ff" g=\'"g"\' h="h"# i="i j="j" k="k l=l\'',
             [('a', '=', '', '', 'a'), ('b', '=', '"', 'b', ''),
              ('c', '=', '"', 'c', ''), ('e', '=', '', '', 'e"e'),
              ('f', '=', '"', 'ff\\" ff', ''), ('g', '=', "'", '"g"', ''),
              ('h', '=', '"', 'h', ''), ('i', '=', '"', 'i j=', ''),
              ('l', '=', '', '', "l'"),],),
            # multiple also with spaces around sign
            ('a = a  b=b c= c d =d',
             [('a', '=', '', '', 'a'), ('b', '=', '', '', 'b'),
              ('c', '=', '', '', 'c'), ('d', '=', '', '', 'd'),],),
            # attr name allowed chars
            ('any-_:.azAZ09-attr-name=value',
             [('any-_:.azAZ09-attr-name', '=', '', '', 'value'),],),
            # attr starts with space or at start-of-line and ends
            # at space or end-of-line if value and it without quotes
            ('a=a #b=b #c d e# f=f# g="g"#',
             [('a', '=', '', '', 'a'), ('d', '', '', '', ''),
              ('f', '=', '', '', 'f#'), ('g', '=', '"', 'g', ''),],),
            # no any variant of sign
            ('a=a b+=b c=+c d+=+d e+ =e f=++f g++=g h==h',
             [('a', '=', '', '', 'a'), ('c', '=', '', '', '+c'),
              ('f', '=', '', '', '++f'), ('h', '=', '', '', '=h'),],),
        ]

        REATTRSSTRICT = htmlattrs.REATTRSSTRICT
        for pattern, results in checkers:
            self.assertEqual(REATTRSSTRICT.findall(pattern), results)

    def test_REATTR(self):
        checkers = [
            # value without spaces and starting quotes
            'attr=any-~!@#$%^&*()_+}{:?><\'"-value',
            # value with quotes and without
            'a=a', "a='a'", 'a="a"',
            # attr name allowed chars
            'any-_:.azAZ09-attr-name=value',
            # attr starts with space or at start-of-line and ends
            # at space or end-of-line if value and it without quotes
        ]
        uncheckers = [
            # any other variants
            'a = a', 'b= b', 'c =c', ' d=d', 'e=e ',
        ]

        REATTR = htmlattrs.REATTR
        for pattern in checkers:
            self.assertTrue(REATTR.match(pattern))
        for pattern in uncheckers:
            self.assertIsNone(REATTR.match(pattern))

    def test_RECLASS(self):
        pattern = ("aname -bname -_cname _dname e--name__"
                   " __-fname !gname !-hname -0name 1name name2")
        results = [('', 'aname'), ('', '-bname'), ('', '-_cname'),
                   ('', '_dname'), ('', 'e--name__'), ('', '__-fname'),
                   ('!', 'gname'), ('!', '-hname'), ('', 'name2')]

        RECLASS = htmlattrs.RECLASS
        self.assertEqual(RECLASS.findall(pattern), results)

    def test_RETAG(self):
        checkers = [
            ('<a href="/url">Text</a>', ['<a href="/url">',], 'a',),
            ('<img scr="img.jpg" />', ['<img scr="img.jpg" />',], 'img',),
            ('</div>', [], 'img',),
            ('<b><i>I</i> <i a="v">I2</i></b>', ['<i>', '<i a="v">',], 'i',),
        ]

        RETAG = htmlattrs.RETAG
        for pattern, results, tagname in checkers:
            result = re.finditer(RETAG % tagname, pattern, re.I)
            self.assertEqual([i.group() for i in result], results)


class ParsersProcessorsFunctionsTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # parsers
    def test_attrs_parser(self):
        checkers = [
            ('a=a b=None c d+=d e="" error::class+="is-invalid"'
             ' required:extra.template::placeholder="{}{?}{=}"',
             [(u'a', u'=', u'a',), (u'b', u'=', None,),
              (u'c', u'', True,), (u'd', u'+=', u'd',), (u'e', u'=', True,),
              (u'error::class', '+=', 'is-invalid',),
              (u'required:extra.template::placeholder', '=', '{}{?}{=}',),],),
        ]

        attrs_parser = htmlattrs.attrs_parser
        for pattern, results in checkers:
            self.assertEqual(attrs_parser(pattern), results)

    def test_attr_name_parser(self):
        checkers = [
            ('ns.main:method.setdefault:type.string:param.value::data-type',
             ('data-type', {'ns': 'main', 'type': 'string',
                            'method': 'setdefault', 'param': 'value',},),),
            ('name',
             ('name', {'ns': 'main', 'type': 'string', 'method': 'set',},),),
            ('ns:wrong::name',
             ('name', {'ns': 'main', 'type': 'string', 'method': 'set',},),),
            ('wrong::name',
             ('name', {'ns': 'main', 'type': 'string', 'method': 'set',},),),
            ('ns.main:ns.error::name',
             ('name', {'ns': 'error', 'type': 'string', 'method': 'set',},),),
            ('main:error::name',
             ('name', {'ns': 'error', 'type': 'string', 'method': 'set',},),),
            ('ns.main:error::name',
             ('name', {'ns': 'error', 'type': 'string', 'method': 'set',},),),
            ('ns.wrong::name',
             ('name', {'ns': 'wrong', 'type': 'string', 'method': 'set',},),),
            ('error:extra.ns::name', (None, None,),),
        ]
        checkers_with_exception = [
            ('method.wrong::data-type', ValueError,),
            ('wrong::data-type', ValueError,),
            ('error:extra.ns::name', ValueError,),
        ]

        config = {
            'priority': ['ns', 'method', 'type',],
            'values': {
                'ns': ['main', 'error', 'required',],
                'method': ['set', 'setdefault',],
                'type': ['string', 'classlist',],
            },
            'strict': ['method', 'type',],
            'preset': {
                'class': {'type': 'classlist',},
            },
        }

        attr_name_parser = htmlattrs.attr_name_parser
        for pattern, results in checkers:
            self.assertEqual(attr_name_parser(pattern, config), results)

        # set errors rising mode (silent to false)
        htmlattrs.DEBUG = True
        for pattern, exception in checkers_with_exception:
            self.assertRaises(exception, attr_name_parser, pattern, config)
        htmlattrs.DEBUG = False

    def test_regex_parser(self):
        checkers = [
            ('input', ('input', slice(None,),),),
            ('input[1:]', ('input', slice(1, None,),),),
            ('(?:input|select)[1]', ('(?:input|select)', slice(1, 2, None)),),
            ('label[-2]', ('label', slice(-2, -1, None)),),
            ('label[-1]', ('label', slice(-1, None, None)),),
            ('label[0]', ('label', slice(0, 1, None)),),
            ('label[1]', ('label', slice(1, 2, None)),),
            ('label[2]', ('label', slice(2, 3, None)),),
            ('label[nonslice]', ('label[nonslice]', slice(None,)),),
            ('label[2', ('label[2', slice(None,)),),  # incorrect definition
            ('label2]', ('label2]', slice(None,)),),  # incorrect definition
        ]

        regex_parser = htmlattrs.regex_parser
        for pattern, results in checkers:
            self.assertEqual(regex_parser(pattern), results)

    def test_regex_with_attrs_parser(self):
        checkers = [
            ('class="red"',
             ('class="red"', r'[a-z]{1}\w*', slice(None,),),),  # default regex
            ('input|class="red"',
             ('class="red"', 'input', slice(None,),),),
            ('input[1:]|class="blue"',
             ('class="blue"', 'input', slice(1, None,),),),
            ('<@>(?:input|select)[1]@title="some | title"',
             ('title="some | title"', '(?:input|select)', slice(1,2,),),),
            ('<@input[1]@title="some | title"',
             ('', '', slice(None,),),),  # incorrect definition
        ]

        regex_with_attrs_parser = htmlattrs.regex_with_attrs_parser
        for pattern, results in checkers:
            self.assertEqual(regex_with_attrs_parser(pattern), results)

    # processsors
    def test_string_value_processor(self):
        attrs = {'len': '32',}
        checkers = [
            (('title', 'Red', {
                'ns': 'main', 'method': 'set', 'type': 'string'}, '='),
             {'len': '32', 'title': 'Red',},),
            (('title', 'Green', {
                'ns': 'required', 'method': 'set', 'type': 'string'}, '+='),
             {'len': '32', 'title': 'Red Green',},),
            (('title', 'Blue', {
                'ns': 'error', 'method': 'set', 'type': 'string',
                'template': '{}{?} & {=}'}, '='),
             {'len': '32', 'title': 'Red Green & Blue',},),
            (('title', '{} are {?}White', {
                'ns': 'error', 'method': 'set', 'type': 'string',}, '='),
             {'len': '32', 'title': 'Red Green & Blue are White',},),
            (('len', True, {
                'ns': 'main', 'method': 'set', 'type': 'string',}, '='),
             {'len': True, 'title': 'Red Green & Blue are White',},),
            (('a', '', {
                'ns': 'main', 'method': 'set', 'type': 'string',}, '='),
             {'len': True, 'a': True, 'title': 'Red Green & Blue are White',},),
        ]
        checkers_empty_quotes = [
            (('a', '', {
                'ns': 'main', 'method': 'set', 'type': 'string'}, '='),
             {'len': True, 'a': '', 'title': 'Red Green & Blue are White',},),
        ]

        string_processor = htmlattrs.attr_value_processors['string']
        for attr, results in checkers:
            attrs[attr[0]] = string_processor(attr, attrs)
            self.assertEqual(attrs, results)

        # set errors rising mode (silent to false)
        htmlattrs.EMPTY_QUOTES = True
        for attr, results in checkers_empty_quotes:
            attrs[attr[0]] = string_processor(attr, attrs)
            self.assertEqual(attrs, results)
        htmlattrs.EMPTY_QUOTES = False

    def test_classlist_value_processor(self):
        attrs = {'class': 'a',}
        checkers = [
            (('class', 'b', {
                'ns': 'main', 'method': 'set', 'type': 'classlist'}, '='),
             {'class': 'b',},),
            (('class', 'c', {
                'ns': 'main', 'method': 'set', 'type': 'classlist'}, '+='),
             {'class': 'b c',},),
            (('class', 'd !b', {
                'ns': 'main', 'method': 'set', 'type': 'classlist'}, '=+'),
             {'class': 'c d',},),
            (('class', '!d', {
                'ns': 'main', 'method': 'set', 'type': 'classlist'}, '+='),
             {'class': 'c',},),
        ]

        class_processor = htmlattrs.attr_value_processors['classlist']
        for attr, results in checkers:
            attrs[attr[0]] = class_processor(attr, attrs)
            self.assertEqual(attrs, results)

    def test_attrs_processor(self):
        # light test for attrs_processor, full test will be in html tests
        emptyform = TestForm()

        extra = [
            ['class', '+=', 'form-control',],
            ['error::class', '+=', 'is-invalid',],
            ['required::class', '+=', 'is-required !red',],
            ['disabled', '', True,],
            ['attr', '=', 'value',],
            ['ns.required::attr', '=', 'is->required',],
            ['ns.required:extra.template::attr', '=', '{}->{?}{=}',],
        ]

        results = {
            'size': '40',
            'class': 'form-control is-required',
            'disabled': True,
            'attr': 'value->is->required',
        }

        boundfield = emptyform['required_field']
        boundfield = htmlattrs.monkey_patch_bound_field(boundfield)
        container = getattr(boundfield, htmlattrs.CONTAINER)
        attrs = container['attrs'] or dict(boundfield.field.widget.attrs)
        attrs = htmlattrs.attrs_processor(extra, attrs, container=container)

        self.assertEqual(attrs, results)

    # functions
    def test_base_namespaces_handler(self):
        boundform = TestForm({'optional_field': 'optional-value',})
        boundform.is_valid()
        invalidform = TestForm({'required_field': 'wrong-value',})
        invalidform.is_valid()
        emptyform = TestForm()

        checkers = [
            (boundform['optional_field'], ['main', 'valid',],),
            (boundform['required_field'], ['main', 'empty', 'required',
                                           'error',],),
            (invalidform['required_field'], ['main', 'required', 'error',],),
            (invalidform['optional_field'], ['main', 'empty',],),
            (emptyform['optional_field'], ['main', 'empty',],),
            (emptyform['required_field'], ['main', 'empty', 'required',],),
        ]

        base_namespaces_handler = htmlattrs.base_namespaces_handler
        for boundfield, results in checkers:
            self.assertEqual(base_namespaces_handler(boundfield), results)

    def test_monkey_patch_bound_field(self):
        emptyform = TestForm()
        orignal_field = emptyform['required_field']
        patched_field = htmlattrs.monkey_patch_bound_field(orignal_field)
        container = getattr(patched_field, htmlattrs.CONTAINER, False)

        # check field is copied and orignal saved in container
        self.assertFalse(orignal_field is patched_field)
        self.assertTrue(orignal_field is container['original'])

        # check form's method extend_htmlattrs_field_container results
        self.assertTrue('valueis10' in container['config']['values']['ns'])


class TemplateFiltersTagsTests(TestCase):
    maxDiff = None

    def setUp(self):
        self.boundform = TestForm({'optional_field': 'optional-value',})
        self.boundform.is_valid()
        self.invalidform = TestForm({'required_field': 'wrong-value',})
        self.invalidform.is_valid()
        self.emptyform = TestForm()

    def tearDown(self):
        pass

    def render_string(self, value):
        template = Template(value)
        context = Context({
            'boundform': self.boundform,
            'invalidform': self.invalidform,
            'emptyform': self.emptyform,
        })
        content = template.render(context).strip()
        if django.VERSION[:2] == (2,0,):
            content = re.sub('<(input[^/>]+)>', '<\\1 />', content)

        # get blocks, divided by === and ---
        blocks = [[j.strip() for j in re.split(r'\n\s*---\s*\n', i)]
                  for i in re.split(r'\n\s*===\s*\n', content)]
        # get blocks, divided by === and ---
        blocks = [([i.strip() for i in left.split('\n')],
                   [i.strip() for i in right.split('\n')],)
                  for left, right in blocks]
        return sum([list(zip(left, right)) for left, right in blocks], [])

    def test_attrs_filter(self):
        checkers = """
            {% load htmlattrs %} {# set, extend and remove value (main ns) #}
         1  {{ emptyform.required_field }}
         2  {{ emptyform.required_field|attrs:'class="field"' }}
         3  {{ emptyform.required_field|attrs:'main::class="field"' }}
         4  {{ emptyform.required_field|attrs:'ns.main::class="field"' }}
         5  {{ emptyform.required_field|attrs:'main:class="field"' }}
         6  {{ emptyform.required_field|attrs:'main::main:class="field"' }}

         7  {{ emptyform.required_field|attrs:'class+="blue"' }}
         8  {{ emptyform.required_field|attrs:'class+="!red"' }}
         9  {{ emptyform.required_field|attrs:'class=None' }}
        10  {{ emptyform.required_field|attrs:'id=None type=None name=None' }}{# unchangable attrs (see docs) #}
            ---

         1  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
         2  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         3  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         4  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         5  <input type="text" name="required_field" class="red" size="40" main:class="field" required id="id_required_field">
         6  <input type="text" name="required_field" class="red" size="40" main:class="field" required id="id_required_field">

         7  <input type="text" name="required_field" class="blue red" size="40" required id="id_required_field">
         8  <input type="text" name="required_field" class="" size="40" required id="id_required_field">
         9  <input type="text" name="required_field" size="40" required id="id_required_field">
        10  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
            === {# syntax of additional params #}
        11  {{ emptyform.required_field|attrs:'size=30' }}
        12  {{ emptyform.required_field|attrs:'set::size=30' }}
        13  {{ emptyform.required_field|attrs:'method.set::size=30' }}
        14  {{ emptyform.required_field|attrs:'setdefault::size=20 setdefault::length=20' }}
        15  {{ emptyform.required_field|attrs:'setifnochanged::size=30' }}
        16  {{ emptyform.required_field|attrs:'size=20'|attrs:'setifnochanged::size=30' }} {# see docs for usage example #}

        17  {{ emptyform.required_field|attrs:'class+="blue !green"' }}
        18  {{ emptyform.required_field|attrs:'type.classlist::class+="blue !green"' }}
        19  {{ emptyform.required_field|attrs:'classlist::class+="blue !green"' }}
        20  {{ emptyform.required_field|attrs:'string::class+="blue !green"' }}
            ---
        11  <input type="text" name="required_field" class="red" size="30" required id="id_required_field">
        12  <input type="text" name="required_field" class="red" size="30" required id="id_required_field">
        13  <input type="text" name="required_field" class="red" size="30" required id="id_required_field">
        14  <input type="text" name="required_field" class="red" size="40" length="20" required id="id_required_field">
        15  <input type="text" name="required_field" class="red" size="30" required id="id_required_field">
        16  <input type="text" name="required_field" class="red" size="20" required id="id_required_field">

        17  <input type="text" name="required_field" class="blue red" size="40" required id="id_required_field">
        18  <input type="text" name="required_field" class="blue red" size="40" required id="id_required_field">
        19  <input type="text" name="required_field" class="blue red" size="40" required id="id_required_field">
        20  <input type="text" name="required_field" class="red blue !green" size="40" required id="id_required_field">
            === {# namespaces and templates for string values #}
        21  {{ emptyform.required_field|attrs:'size=30' }}
        22  {{ emptyform.required_field|attrs:'size=30 empty::size+=40 required::size+=50' }}
        23  {{ boundform.required_field|attrs:'size=30 empty::size+=40 required::size+=50 error::size+=60' }}
        24  {{ boundform.required_field|attrs:'size=30 empty::size+=40 required::size+=50 error::size+=60 valid::size+=70' }}
        25  {{ boundform.optional_field|attrs:'size=30 empty::size+=40 required::size+=50 error::size+=60 valid::size+=70' }}

        26  {{ boundform.required_field|attrs:'error::a+=1 required::a+=2 empty::a+=3 a=4' }} {# ns ordering #}
            {# available namespaces #}
        27  {{ emptyform.required_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
        28  {{ emptyform.optional_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
        29  {{ boundform.required_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
        30  {{ boundform.optional_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
        31  {{ invalidform.required_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
        32  {{ invalidform.optional_field|attrs:'main::attr=main empty::attr+=empty required::attr+=required error::attr+=error valid::attr+=valid' }}
            {# inheritance with templates in strings, in extra params and by "+" in sign (+= and =+) #}
        33  {{ emptyform.optional_field|attrs:'attr=old-value empty::attr=new-value empty:extra.template::attr="{}--and-conditional-and--{?}{=}{?}--and-conditional-again-and--{}--and-unconditional-text"' }}
        34  {{ emptyform.optional_field|attrs:'empty::attr=new-value empty:extra.template::attr="{}--and-conditional-and--{?}{=}{?}--and-conditional-again-and--{}--and-unconditional-text"' }}
        35  {{ emptyform.optional_field|attrs:'attr=old-value empty::attr={}--conditional--{?}new-value{?}--another-conditional--{}' }}
        36  {{ emptyform.optional_field|attrs:'size+=50 empty::size=+30' }}
            ---
        21  <input type="text" name="required_field" class="red" size="30" required id="id_required_field">
        22  <input type="text" name="required_field" class="red" size="30 40 50" required id="id_required_field">
        23  <input type="text" name="required_field" class="red" size="30 40 50 60" required id="id_required_field">
        24  <input type="text" name="required_field" class="red" size="30 40 50 60" required id="id_required_field">
        25  <input type="text" name="optional_field" value="optional-value" class="blue" size="30 70" id="id_optional_field">

        26  <input type="text" name="required_field" class="red" size="40" a="4 3 2 1" required id="id_required_field">

        27  <input type="text" name="required_field" class="red" size="40" attr="main empty required" required id="id_required_field">
        28  <input type="text" name="optional_field" class="blue" size="40" attr="main empty" id="id_optional_field">
        29  <input type="text" name="required_field" class="red" size="40" attr="main empty required error" required id="id_required_field">
        30  <input type="text" name="optional_field" value="optional-value" class="blue" size="40" attr="main valid" id="id_optional_field">
        31  <input type="text" name="required_field" value="wrong-value" class="red" size="40" attr="main required error" required id="id_required_field">
        32  <input type="text" name="optional_field" class="blue" size="40" attr="main empty" id="id_optional_field">

        33  <input type="text" name="optional_field" class="blue" size="40" attr="old-value--and-conditional-and--new-value--and-conditional-again-and--old-value--and-unconditional-text" id="id_optional_field">
        34  <input type="text" name="optional_field" class="blue" size="40" attr="new-value--and-unconditional-text" id="id_optional_field">
        35  <input type="text" name="optional_field" class="blue" size="40" attr="old-value--conditional--new-value--another-conditional--old-value" id="id_optional_field">
        36  <input type="text" name="optional_field" class="blue" size="30 40 50" id="id_optional_field">
            ===
        37  {{ emptyform.required_field|attrs:'class=green' }}
        38  {{ emptyform.required_field|attrs:'class+=green' }}
        39  {{ emptyform.required_field|attrs:'class=+green' }} {# ordered by alphabet #}
        40  {{ emptyform.required_field|attrs:'class+="green !red"' }}
        41  {{ emptyform.required_field|attrs:'class+="!red"' }}
        42  {{ emptyform.required_field|attrs:'class+="green"'|attrs:'class+="blue !green"' }}
        43  {{ emptyform.required_field|attrs:'class+="green red"' }} {# duplicates are ingored #}
            ---
        37  <input type="text" name="required_field" class="green" size="40" required id="id_required_field">
        38  <input type="text" name="required_field" class="green red" size="40" required id="id_required_field">
        39  <input type="text" name="required_field" class="green red" size="40" required id="id_required_field">
        40  <input type="text" name="required_field" class="green" size="40" required id="id_required_field">
        41  <input type="text" name="required_field" class="" size="40" required id="id_required_field">
        42  <input type="text" name="required_field" class="blue red" size="40" required id="id_required_field">
        43  <input type="text" name="required_field" class="green red" size="40" required id="id_required_field">
        """

        results = self.render_string(checkers)
        for result, reference in results:
            self.assertEqual(result, reference)

    def test_attrs_tag(self):
        checkers = """
            {% load htmlattrs %} {# attrs management test #}
         1  {{ emptyform.required_field }}
         2  {% attrs emptyform.required_field class="field" %}
         3  {% attrs emptyform.required_field placeholder=emptyform.required_field.label %}
         4  {% attrs emptyform.required_field placeholder=emptyform.required_field.label|upper size=None %}
         5  {% attrs emptyform.required_field placeholder=emptyform.required_field.label|upper as field %}
         6  {{ field|attrs:'disabled' }} {# as field synax check #}
         7  {% with WIDGET_REQUIRED_CLASS="required" WIDGET_EMPTY_CLASS="empty" %}
         8  {% attrs emptyform.required_field class="field" %} {# WIDGET_*_CLASS context variables test #}
         9  {% endwith %}
            ---

         1  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
         2  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         3  <input type="text" name="required_field" class="red" size="40" placeholder="Required field" required id="id_required_field">
         4  <input type="text" name="required_field" class="red" placeholder="REQUIRED FIELD" required id="id_required_field">
         5
         6  <input type="text" name="required_field" class="red" size="40" placeholder="REQUIRED FIELD" disabled required id="id_required_field">
         7
         8  <input type="text" name="required_field" class="empty field required" size="40" required id="id_required_field">
         9
        """

        results = self.render_string(checkers)
        for result, reference in results:
            self.assertEqual(result, reference)

    def test_htmlattrs_tag(self):
        checkers = """
            {% load htmlattrs %} {# regex and separater #}
         1  {{ emptyform.required_field }}
         2  {{ emptyform.required_field|htmlattrs:'class="field"' }}
         3  {{ emptyform.required_field|htmlattrs:'input|class="field"' }}
         4  {{ emptyform.required_field|htmlattrs:'input.*?size="40"|class="field"' }}
         5  {{ emptyform.required_field|htmlattrs:'<@@>input@@class="field"' }}
         6  {{ emptyform.required_field|htmlattrs:'input.*?[0123456789][:]|class="field"' }}
         7  {{ emptyform.required_field|htmlattrs:'input[1:]|class="field"' }}
            ---

         1  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
         2  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         3  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         4  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         5  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         6  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         7  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
            === {# withfield filter test #}
         8  {{ emptyform.required_field|htmlattrs:'class="field" empty::class+=empty required::class+=required' }}
         9  {{ emptyform.required_field|withfield:emptyform.required_field|htmlattrs:'class="field" empty::class+=empty required::class+=required' }}
            ---
         8  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         9  <input type="text" name="required_field" class="empty field required" size="40" required id="id_required_field">
            === {# slice obj test #}
        10  {{ '<img/><img/><img/>'|htmlattrs:'src="path"' }}
        11  {{ '<img/><img/><img/>'|htmlattrs:'img[0]|src="path"' }}
        12  {{ '<img/><img/><img/>'|htmlattrs:'img[-1]|src="path"' }}
        13  {{ '<img/><img/><img/>'|htmlattrs:'img[1:]|src="path"' }}
        14  {{ '<img/><img/><img/>'|htmlattrs:'img[::2]|src="path"' }}
        15  {{ '<img/><img/><img/>'|htmlattrs:'img[::2]|src="path"'|htmlattrs:'img[1::2]|src="path-odd"' }}
            ---
        10  <img src="path" /><img src="path" /><img src="path" />
        11  <img src="path" /><img/><img/>
        12  <img/><img/><img src="path" />
        13  <img/><img src="path" /><img src="path" />
        14  <img src="path" /><img/><img src="path" />
        15  <img src="path" /><img src="path-odd" /><img src="path" />
        """

        results = self.render_string(checkers)
        for result, reference in results:
            self.assertEqual(result, reference)

    def test_htmlattrs_filter(self):
        checkers = """
            {% load htmlattrs %} {# attrs management test #}
         1  {{ emptyform.required_field }}
         2  {% htmlattrs emptyform.required_field 'input' class="field" %}
         3  {% htmlattrs emptyform.required_field 'input' placeholder=emptyform.required_field.label %}
         4  {% htmlattrs emptyform.required_field 'input' placeholder=emptyform.required_field.label|upper size=None %}
         5  {% htmlattrs emptyform.required_field 'input' placeholder=emptyform.required_field.label|upper as field %}
         6  {{ field|htmlattrs:'disabled' }} {# as field synax check #}
         7  {% with WIDGET_REQUIRED_CLASS="required" WIDGET_EMPTY_CLASS="empty" %}
         8  {% htmlattrs emptyform.required_field 'input' with emptyform.required_field class="field" %} {# WIDGET_*_CLASS context variables test #}
         9  {% endwith %}
        10  {% htmlattrs emptyform.required_field 'input' class="field" %}
        11  {% htmlattrs emptyform.required_field 'input' with emptyform.required_field class="field" required::class+="required" %}
            ---

         1  <input type="text" name="required_field" class="red" size="40" required id="id_required_field">
         2  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
         3  <input type="text" name="required_field" class="red" size="40" required id="id_required_field" placeholder="Required field">
         4  <input type="text" name="required_field" class="red" required id="id_required_field" placeholder="REQUIRED FIELD">
         5
         6  <input type="text" name="required_field" class="red" size="40" required id="id_required_field" placeholder="REQUIRED FIELD" disabled>
         7
         8  <input type="text" name="required_field" class="empty field required" size="40" required id="id_required_field">
         9
        10  <input type="text" name="required_field" class="field" size="40" required id="id_required_field">
        11  <input type="text" name="required_field" class="field required" size="40" required id="id_required_field">
        """

        results = self.render_string(checkers)
        for result, reference in results:
            self.assertEqual(result, reference)
