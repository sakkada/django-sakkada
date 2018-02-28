# -*- coding: utf-8 -*-
import os

from django.test import TestCase
from sakkada.template.htmlattrs.templatetags import htmlattrs


class RegexTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_main_regex(self):
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
              ('c', '=+', '', '', 'c'), ('d', '+=+', '', '', 'd'),
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

        REGEX = htmlattrs.REGEX
        for pattern, results in checkers:
            self.assertEqual(REGEX.findall(pattern), results)

    def test_class_value_type_regex(self):
        pattern = ("aname -bname -_cname _dname e--name__"
                   " __-fname !gname !-hname -0name 1name name2")
        results = [('', 'aname'), ('', '-bname'), ('', '-_cname'),
                   ('', '_dname'), ('', 'e--name__'), ('', '__-fname'),
                   ('!', 'gname'), ('!', '-hname'), ('', 'name2')]

        RECLS = htmlattrs.RECLS
        self.assertEqual(RECLS.findall(pattern), results)


class ParsersTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_attrs_parser(self):
        checkers = [
            ('a=a b=None c d+=d',
             [(u'a', u'=', u'a',), (u'b', u'=', None,),
              (u'c', u'', True,), (u'd', u'+=', u'd',),],),
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
        ]
        checkers_with_exception = [
            ('method.wrong::data-type', ValueError,),
            ('wrong::data-type', ValueError,),
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
