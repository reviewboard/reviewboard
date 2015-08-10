from __future__ import unicode_literals

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from mock import Mock

from djblets.db.query import LocalDataQuerySet
from djblets.testing.testcases import TestCase


class LocalDataQuerySetTests(TestCase):
    """Tests for djblets.db.query.LocalDataQuerySet."""
    def test_clone(self):
        """Testing LocalDataQuerySet.clone"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)
        clone = queryset.clone()

        self.assertEqual(list(clone), values)
        values.append(4)
        self.assertNotEqual(list(clone), values)

    def test_count(self):
        """Testing LocalDataQuerySet.count"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)

        self.assertEqual(queryset.count(), 3)

    def test_exclude(self):
        """Testing LocalDataQuerySet.exclude"""
        obj1 = Mock()
        obj1.a = 1
        obj1.b = 2

        obj2 = Mock()
        obj2.a = 10
        obj2.b = 20

        queryset = LocalDataQuerySet([obj1, obj2])
        queryset = queryset.exclude(a=1)

        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset[0], obj2)

    def test_exclude_with_multiple_args(self):
        """Testing LocalDataQuerySet.exclude with multiple arguments"""
        obj1 = Mock()
        obj1.a = 1
        obj1.b = 2

        obj2 = Mock()
        obj2.a = 1
        obj2.b = 20

        obj3 = Mock()
        obj3.a = 1
        obj3.b = 40

        queryset = LocalDataQuerySet([obj1, obj2, obj3])
        queryset = queryset.exclude(a=1, b=20)

        self.assertEqual(len(queryset), 2)
        self.assertEqual(list(queryset), [obj1, obj3])

    def test_filter(self):
        """Testing LocalDataQuerySet.filter"""
        obj1 = Mock()
        obj1.a = 1
        obj1.b = 2

        obj2 = Mock()
        obj2.a = 10
        obj2.b = 20

        obj3 = Mock()
        obj3.a = 1
        obj3.b = 40

        queryset = LocalDataQuerySet([obj1, obj2, obj3])
        queryset = queryset.filter(a=1)

        self.assertEqual(len(queryset), 2)
        self.assertEqual(list(queryset), [obj1, obj3])

    def test_filter_with_multiple_args(self):
        """Testing LocalDataQuerySet.filter with multiple arguments"""
        obj1 = Mock()
        obj1.a = 1
        obj1.b = 2

        obj2 = Mock()
        obj2.a = 1
        obj2.b = 20

        obj3 = Mock()
        obj3.a = 2
        obj3.b = 20

        queryset = LocalDataQuerySet([obj1, obj2, obj3])
        queryset = queryset.filter(a=1, b=20)

        self.assertEqual(len(queryset), 1)
        self.assertEqual(queryset[0], obj2)

    def test_get(self):
        """Testing LocalDataQuerySet.get"""
        obj1 = Mock()
        queryset = LocalDataQuerySet([obj1])

        self.assertEqual(queryset.get(), obj1)

    def test_get_with_filters(self):
        """Testing LocalDataQuerySet.get with filters"""
        obj1 = Mock()
        obj1.a = 1

        obj2 = Mock()
        obj2.a = 2

        queryset = LocalDataQuerySet([obj1, obj2])

        self.assertEqual(queryset.get(a=1), obj1)

    def test_get_with_no_results(self):
        """Testing LocalDataQuerySet.get with no results"""
        obj1 = Mock()
        obj1.a = 1

        obj2 = Mock()
        obj2.a = 1

        queryset = LocalDataQuerySet([obj1, obj2])

        self.assertRaises(ObjectDoesNotExist, queryset.get, a=2)

    def test_get_with_multiple_results(self):
        """Testing LocalDataQuerySet.get with multiple results"""
        obj1 = Mock()
        obj2 = Mock()

        queryset = LocalDataQuerySet([obj1, obj2])

        self.assertRaises(MultipleObjectsReturned, queryset.get)

    def test_contains(self):
        """Testing LocalDataQuerySet.__contains__"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)

        self.assertIn(2, queryset)

    def test_getitem(self):
        """Testing LocalDataQuerySet.__getitem__"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)

        self.assertEqual(queryset[1], 2)

    def test_getslice(self):
        """Testing LocalDataQuerySet.__getitem__"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)

        self.assertEqual(queryset[1:3], [2, 3])

    def test_iter(self):
        """Testing LocalDataQuerySet.__iter__"""
        values = [1, 2]
        queryset = LocalDataQuerySet(values)
        gen = iter(queryset)

        self.assertEqual(gen.next(), 1)
        self.assertEqual(gen.next(), 2)

    def test_len(self):
        """Testing LocalDataQuerySet.__len__"""
        values = [1, 2, 3]
        queryset = LocalDataQuerySet(values)

        self.assertEqual(len(queryset), 3)
