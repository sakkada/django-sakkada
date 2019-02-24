from django.http import QueryDict
from django.test import TestCase, RequestFactory
from sakkada.http.querystring import QueryString


class QueryStringTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def tearDown(self):
        pass

    def test_various_combinations_of_params(self):
        request = self.factory.get('/url/?a=1&c&b=2')
        querystring = QueryString(request)

        checkers = [
            # no and only params
            ('no__a', '?c=&b=2',),
            ('no__a__c', '?b=2',),
            ('no__a__c__b', '',),  # empty
            ('no__c__d__e', '?a=1&b=2',),
            ('only__a', '?a=1',),
            ('only__a__c', '?a=1&c=',),
            ('only__a__b__c', '?a=1&c=&b=2',),

            # as format (part, full, self, dict) with/without left
            ('as__part', '&a=1&c=&b=2',),
            ('as__partleft', '&a=1&c=&b=2&',),
            ('no__a__b__c__as__part', '',),  # empty
            ('no__a__b__c__as__partleft', '&',),  # empty

            ('as__full', '?a=1&c=&b=2',),
            ('as__fullleft', '?a=1&c=&b=2&',),
            ('no__a__b__c__as__full', '',),  # empty
            ('no__a__b__c__as__fullleft', '?',),  # empty

            ('as__self', 'a=1&c=&b=2',),
            ('as__selfleft', 'a=1&c=&b=2&',),
            ('no__a__b__c__as__self', '',),  # empty
            ('no__a__b__c__as__selfleft', '',),  # empty

            ('as__dict', QueryDict('a=1&c&b=2'),),
            ('as__dictleft', QueryDict('a=1&c&b=2'),),  # left ignored if dict
            ('no__a__b__c__as__dict', QueryDict(),),  # empty
            ('no__a__b__c__as__dictleft', QueryDict(),),  # left ignored
        ]

        for attribute, result in checkers:
            self.assertEqual(getattr(querystring, attribute), result)
