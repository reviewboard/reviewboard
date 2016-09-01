from __future__ import unicode_literals

import logging

from djblets.conditions import ConditionSet
from djblets.forms.fields import ConditionsField
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.integrations.forms import IntegrationConfigForm
from reviewboard.integrations.models import IntegrationConfig
from reviewboard.reviews.conditions import ReviewRequestConditionChoices
from reviewboard.testing.testcase import TestCase


class MyConfigForm(IntegrationConfigForm):
    my_conditions = ConditionsField(
        choices=ReviewRequestConditionChoices)


class IntegrationConfigTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.integrations.models.IntegrationConfig."""

    def test_load_conditions(self):
        """Testing IntegrationConfig.load_conditions"""
        config = IntegrationConfig()
        config.settings['my_conditions'] = {
            'mode': 'all',
            'conditions': [
                {
                    'choice': 'branch',
                    'op': 'is',
                    'value': 'master',
                },
                {
                    'choice': 'summary',
                    'op': 'contains',
                    'value': '[WIP]',
                },
            ],
        }

        condition_set = config.load_conditions(MyConfigForm,
                                               conditions_key='my_conditions')

        self.assertEqual(condition_set.mode, ConditionSet.MODE_ALL)

        conditions = condition_set.conditions
        self.assertEqual(len(conditions), 2)

        condition = conditions[0]
        self.assertEqual(condition.choice.choice_id, 'branch')
        self.assertEqual(condition.operator.operator_id, 'is')
        self.assertEqual(condition.value, 'master')

        condition = conditions[1]
        self.assertEqual(condition.choice.choice_id, 'summary')
        self.assertEqual(condition.operator.operator_id, 'contains')
        self.assertEqual(condition.value, '[WIP]')

    def test_load_conditions_with_empty(self):
        """Testing IntegrationConfig.load_conditions with empty or missing
        data
        """
        config = IntegrationConfig()
        config.settings['conditions'] = None

        self.assertIsNone(config.load_conditions(MyConfigForm))

    def test_load_conditions_with_bad_data(self):
        """Testing IntegrationConfig.load_conditions with bad data"""
        config = IntegrationConfig()
        config.settings['conditions'] = 'dfsafas'

        self.spy_on(logging.debug)
        self.spy_on(logging.exception)

        self.assertIsNone(config.load_conditions(MyConfigForm))
        self.assertTrue(logging.debug.spy.called)
        self.assertTrue(logging.exception.spy.called)

    @add_fixtures(['test_users'])
    def test_match_conditions(self):
        """Testing IntegrationConfig.match_conditions"""
        config = IntegrationConfig()
        config.settings['my_conditions'] = {
            'mode': 'all',
            'conditions': [
                {
                    'choice': 'branch',
                    'op': 'is',
                    'value': 'master',
                },
                {
                    'choice': 'summary',
                    'op': 'contains',
                    'value': '[WIP]',
                },
            ],
        }

        review_request = self.create_review_request(
            branch='master',
            summary='[WIP] This is a test.')

        self.assertTrue(config.match_conditions(
            MyConfigForm,
            conditions_key='my_conditions',
            review_request=review_request))

        review_request = self.create_review_request(
            branch='master',
            summary='This is a test.')

        self.assertFalse(config.match_conditions(
            MyConfigForm,
            conditions_key='my_conditions',
            review_request=review_request))

    @add_fixtures(['test_users'])
    def test_match_conditions_sandbox(self):
        """Testing IntegrationConfig.match_conditions with exceptions
        sandboxed
        """
        config = IntegrationConfig()
        config.settings['my_conditions'] = {
            'mode': 'all',
            'conditions': [
                {
                    'choice': 'branch',
                    'op': 'is',
                    'value': 'master',
                },
                {
                    'choice': 'summary',
                    'op': 'contains',
                    'value': '[WIP]',
                },
            ],
        }

        self.create_review_request(
            branch='master',
            summary='[WIP] This is a test.')

        self.spy_on(logging.exception)

        self.assertFalse(config.match_conditions(
            MyConfigForm,
            conditions_key='my_conditions',
            review_request='test'))

        self.assertTrue(logging.exception.spy.called)
