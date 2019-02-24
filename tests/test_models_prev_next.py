from django.db import models
from django.conf import settings
from django.test import TestCase
from main.models import PrevNextTestModel as Model


class QueryStringTests(TestCase):
    def setUp(self):
        super().setUp()
        # settings.DEBUG = True

        Model.objects.create(title='a', slug='a', weight=500, nweight=4)
        Model.objects.create(title='a', slug='b', weight=500, nweight=None)
        Model.objects.create(title='b', slug='c', weight=500, nweight=None)
        Model.objects.create(title='b', slug='d', weight=500, nweight=None)
        Model.objects.create(title='c', slug='e', weight=500, nweight=1)
        Model.objects.create(title='c', slug='f', weight=500, nweight=2)

    def tearDown(self):
        super().tearDown()
        # settings.DEBUG = False

    def test_get_current_ordering(self):
        qset_default = Model.objects.all()
        qset_defined = Model.objects.all().order_by('-nweight', 'title')
        qset_with_id = Model.objects.all().order_by('-weight', '-id', 'title')
        instance = Model.objects.first()

        self.assertEqual(list(Model._meta.ordering), ['-weight',])
        self.assertEqual(instance._get_current_ordering(qset_default),
                         ['-weight', 'id'])
        self.assertEqual(instance._get_current_ordering(qset_defined),
                         ['-nweight', 'title', 'id'])
        self.assertEqual(instance._get_current_ordering(qset_with_id),
                         ['-weight', '-id'])

    def test_get_next_or_prev_by_order(self):
        qset_default = Model.objects.all()
        qset_defined = Model.objects.all().order_by('-title')
        obj = qset_default.get(slug='c')

        # support of expressions is not implemented yet
        self.assertRaises(ValueError,
                          obj._get_next_or_prev_by_order,
                          order_by=(models.F('title'),))

        # test _get_next_or_prev_by_order kwargs:
        #   order_by, is_next, nulls_first, queryset,
        #   as_queryset, cache_name, force

        # test order_by kwarg
        self.assertEqual(
            obj._get_next_or_prev_by_order(as_queryset=True)[2],
            ['-weight', 'id'])
        self.assertEqual(
            obj._get_next_or_prev_by_order(order_by=('-title',),
                                           as_queryset=True)[2],
            ['-title', 'id'])

        # test is_next kwarg
        common_kwargs = {'force': True, 'order_by': ('slug',),}
        self.assertEqual(
            obj._get_next_or_prev_by_order(**common_kwargs),
            Model.objects.get(slug='d'))
        self.assertEqual(
            obj._get_next_or_prev_by_order(is_next=True, **common_kwargs),
            Model.objects.get(slug='d'))
        self.assertEqual(
            obj._get_next_or_prev_by_order(is_next=False, **common_kwargs),
            Model.objects.get(slug='b'))

        # test nulls_first kwarg
        obj_with_null = Model.objects.get(slug='c')
        obj_wout_null = Model.objects.get(slug='e')
        common_kwargs = {'force': True, 'as_queryset': True,}
        differ_kwargs = [
            {'is_next': True, 'order_by': ('-nweight',), 'nulls_first': True,},
            {'is_next': True, 'order_by': ('-nweight',), 'nulls_first': False,},
            {'is_next': False, 'order_by': ('-nweight',), 'nulls_first': True,},
            {'is_next': False, 'order_by': ('-nweight',), 'nulls_first': False,},
            {'is_next': True, 'order_by': ('-title',), 'nulls_first': True,},
            {'is_next': True, 'order_by': ('-title',), 'nulls_first': False,},
            {'is_next': False, 'order_by': ('-title',), 'nulls_first': True,},
            {'is_next': False, 'order_by': ('-title',), 'nulls_first': False,},
        ]
        dest_filters = (
            "(AND: (OR: (AND: ('nweight', None), ('id__gt', :id)), ('nweight__isnull', False)), (NOT (AND: ('pk', :id))))",
            "(AND: ('nweight', None), ('id__gt', :id), (NOT (AND: ('pk', :id))))",
            "(AND: ('nweight', None), ('id__lt', :id), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('nweight', None), ('id__lt', :id)), ('nweight__isnull', False)), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'b'), ('id__gt', :id)), ('title__lt', 'b')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'b'), ('id__gt', :id)), ('title__lt', 'b')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'b'), ('id__lt', :id)), ('title__gt', 'b')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'b'), ('id__lt', :id)), ('title__gt', 'b')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('nweight', 1), ('id__gt', :id)), ('nweight__lt', 1)), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('nweight', 1), ('id__gt', :id)), ('nweight__lt', 1), ('nweight__isnull', True)), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('nweight', 1), ('id__lt', :id)), ('nweight__gt', 1), ('nweight__isnull', True)), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('nweight', 1), ('id__lt', :id)), ('nweight__gt', 1)), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'c'), ('id__gt', :id)), ('title__lt', 'c')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'c'), ('id__gt', :id)), ('title__lt', 'c')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'c'), ('id__lt', :id)), ('title__gt', 'c')), (NOT (AND: ('pk', :id))))",
            "(AND: (OR: (AND: ('title', 'c'), ('id__lt', :id)), ('title__gt', 'c')), (NOT (AND: ('pk', :id))))",
        )

        test_filters = []
        for obj in (obj_with_null, obj_wout_null,):
            test_filters += [
                obj._get_next_or_prev_by_order(**kwargs,
                                               **common_kwargs)[1].__str__().replace(str(obj.pk), ':id')
                for kwargs in differ_kwargs
            ]

        for left, right in zip(test_filters, dest_filters):
            self.assertEqual(left, right)

        # test queryset kwarg
        common_kwargs = {'as_queryset': True, 'force': True,}
        self.assertEqual(
            obj._get_next_or_prev_by_order(queryset=None,
                                           **common_kwargs)[2],
            ['-weight', 'id'])
        self.assertEqual(
            obj._get_next_or_prev_by_order(queryset='non-queryset-object',
                                           **common_kwargs)[2],
            ['-weight', 'id'])
        self.assertEqual(
            obj._get_next_or_prev_by_order(queryset=qset_defined,
                                           **common_kwargs)[2],
            ['-title', 'id'])

        # test as_queryset kwarg
        self.assertEqual(
            obj._get_next_or_prev_by_order(order_by=('-slug',),
                                           as_queryset=False, force=True),
            Model.objects.get(slug='d'))

        as_queryset = obj._get_next_or_prev_by_order(order_by=('-slug',),
                                                     as_queryset=True)

        self.assertTrue(isinstance(as_queryset, tuple))
        self.assertEqual(len(as_queryset), 3)
        self.assertEqual(type(as_queryset[0]), models.query.QuerySet)
        self.assertEqual(type(as_queryset[1]), models.Q)
        self.assertEqual(type(as_queryset[2]), list)

        # test cache_name kwarg
        obj = Model.objects.get(slug='c')

        self.assertFalse(hasattr(obj, '_prev_nextprev_cache'))
        self.assertFalse(hasattr(obj, '_next_nextprev_cache'))

        obj._get_next_or_prev_by_order(is_next=True)
        obj._get_next_or_prev_by_order(is_next=False)

        self.assertTrue(hasattr(obj, '_prev_nextprev_cache'))
        self.assertTrue(hasattr(obj, '_next_nextprev_cache'))

        obj._get_next_or_prev_by_order(cache_name='cache', is_next=True)
        obj._get_next_or_prev_by_order(cache_name='cache', is_next=False)

        self.assertTrue(hasattr(obj, '_prev_cache_nextprev_cache'))
        self.assertTrue(hasattr(obj, '_next_cache_nextprev_cache'))

        # test force kwarg
        obj = Model.objects.get(slug='c')

        next1 = obj._get_next_or_prev_by_order(is_next=True)
        next2 = obj._get_next_or_prev_by_order(is_next=True)
        next3 = obj._get_next_or_prev_by_order(is_next=True, force='nocache')
        next4 = obj._get_next_or_prev_by_order(is_next=True, force=True)
        next5 = obj._get_next_or_prev_by_order(is_next=True, force=True)

        self.assertTrue(next1 is next2)
        self.assertFalse(next1 is next3)
        self.assertFalse(next3 is next4)
        self.assertFalse(next4 is next5)

    def test_public_methods(self):
        obj = Model.objects.get(slug='c')

        prev = obj.get_prev_by_order(order_by=('slug',))
        next = obj.get_next_by_order(order_by=('slug',))

        self.assertEqual(prev.slug, 'b')
        self.assertEqual(next.slug, 'd')
