"""Tests for reviewboard.extensions.hooks.ReviewRequestConditionChoicesHook.

Version Added:
    7.1
"""

from __future__ import annotations

from djblets.conditions.choices import (BaseConditionIntegerChoice,
                                        BaseConditionStringChoice)
from djblets.conditions.operators import (ConditionOperators,
                                          IsNotOneOfOperator,
                                          IsOneOfOperator,
                                          UnsetOperator)
from djblets.conditions.values import ConditionValueMultipleChoiceField
from reviewboard.extensions.hooks import ReviewRequestConditionChoicesHook
from reviewboard.reviews.conditions import (ReviewRequestConditionChoiceMixin,
                                            review_request_condition_choices)
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase


class _MyCategoryChoice(ReviewRequestConditionChoiceMixin,
                        BaseConditionStringChoice):
    choice_id = 'my-category'
    name = 'Category'

    operators = ConditionOperators([
        UnsetOperator,
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    default_value_field = ConditionValueMultipleChoiceField[str](choices=[
       ('architecture', 'Architecture'),
       ('bug', 'Bug'),
       ('docs', 'Documentation'),
       ('feature', 'Feature'),
       ('security', 'Security'),
    ])

    def get_match_value(self, review_request, **kwargs):
        return review_request.extra_data.get('my_category')


class _MyTaskIDChoice(ReviewRequestConditionChoiceMixin,
                      BaseConditionIntegerChoice):
    choice_id = 'my-task-id'
    name = 'Task ID'

    def get_match_value(self, review_request, **kwargs):
        # This would return an integer.
        return review_request.extra_data.get('my_task_id')


class ReviewRequestConditionChoicesHookTests(BaseExtensionHookTestCase):
    """Tests for ReviewRequestConditionChoicesHook."""

    def test_register(self) -> None:
        """Testing ReviewRequestConditionChoicesHook initializing"""
        ReviewRequestConditionChoicesHook(self.extension, [
            _MyCategoryChoice,
            _MyTaskIDChoice,
        ])

        self.assertIn(_MyCategoryChoice, review_request_condition_choices)
        self.assertIn(_MyTaskIDChoice, review_request_condition_choices)

    def test_unregister(self) -> None:
        """Testing ReviewRequestConditionChoicesHook uninitializing"""
        hook = ReviewRequestConditionChoicesHook(self.extension, [
            _MyCategoryChoice,
            _MyTaskIDChoice,
        ])
        hook.disable_hook()

        self.assertNotIn(_MyCategoryChoice, review_request_condition_choices)
        self.assertNotIn(_MyTaskIDChoice, review_request_condition_choices)
