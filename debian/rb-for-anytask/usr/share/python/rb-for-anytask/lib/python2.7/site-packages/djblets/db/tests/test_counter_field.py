from __future__ import unicode_literals

from django.db import models
from django.db.models import F

from djblets.db.fields import CounterField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class CounterFieldTestModel(models.Model):
    counter = CounterField(initializer=lambda o: 5)


class CounterFieldInitializerModel(models.Model):
    counter = CounterField(initializer=lambda o: 42)


class CounterFieldInitializerFModel(models.Model):
    INIT_EXPR = F('my_int') + 1

    my_int = models.IntegerField(default=42)

    counter = CounterField(
        initializer=lambda o: CounterFieldInitializerFModel.INIT_EXPR)


class CounterFieldNoInitializerModel(models.Model):
    counter = CounterField()


class CounterFieldTests(TestModelsLoaderMixin, TestCase):
    """Tests for djblets.db.fields.CounterField."""
    tests_app = 'djblets.db.tests'

    def test_no_initializer(self):
        """Testing CounterField without an initializer"""
        model = CounterFieldNoInitializerModel.objects.create()
        self.assertIsNone(model.counter)

    def test_initializer_function(self):
        """Testing CounterField with an initializer function"""
        model = CounterFieldInitializerModel.objects.create()
        self.assertEqual(model.counter, 42)

    def test_initializer_f_existing_instance(self):
        """Testing CounterField with an initializer F() expression
        on existing model instance
        """
        model = CounterFieldInitializerFModel.objects.create()
        model.counter = None
        model.save()

        model = CounterFieldInitializerFModel.objects.get(pk=model.pk)
        self.assertEqual(model.counter, 43)

    def test_initializer_f_new_instance(self):
        """Testing CounterField with an initializer F() expression
        on new model instance
        """
        model = CounterFieldInitializerFModel.objects.create()
        self.assertEqual(model.counter, 0)

    def test_increment(self):
        """Testing CounterField.increment"""
        self._test_increment(expected_value=6, expected_expr=F('counter') + 1)

    def test_increment_by(self):
        """Testing CounterField.increment with increment_by"""
        self._test_increment(expected_value=8, expected_expr=F('counter') + 3,
                             increment_by=3)

    def test_increment_no_reload(self):
        """Testing CounterField.increment with reload_object=False"""
        self._test_increment(expected_value=5, expected_expr=F('counter') + 1,
                             reload_object=False)

    def test_decrement(self):
        """Testing CounterField.decrement"""
        self._test_decrement(expected_value=4, expected_expr=F('counter') - 1)

    def test_decrement_by(self):
        """Testing CounterField.decrement with decrement_by"""
        self._test_decrement(expected_value=2, expected_expr=F('counter') - 3,
                             decrement_by=3)

    def test_decrement_no_reload(self):
        """Testing CounterField.decrement with reload_object=False"""
        self._test_decrement(expected_value=5, expected_expr=F('counter') - 1,
                             reload_object=False)

    def test_reload(self):
        """Testing CounterField.reload"""
        model = CounterFieldTestModel.objects.create()

        model.counter = None
        model.reload_counter()
        self.assertEqual(model.counter, 5)

    def _test_increment(self, expected_value, expected_expr, **kwargs):
        self._test_update_value(expected_value, expected_expr,
                                'increment_counter', **kwargs)

    def _test_decrement(self, expected_value, expected_expr, **kwargs):
        self._test_update_value(expected_value, expected_expr,
                                'decrement_counter', **kwargs)

    def _test_update_value(self, expected_value, expected_expr, func_name,
                           **kwargs):
        model = CounterFieldTestModel.objects.create()

        getattr(model, func_name)(**kwargs)

        self.assertEqual(model.counter, expected_value)
