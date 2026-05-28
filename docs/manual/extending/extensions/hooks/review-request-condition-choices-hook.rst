.. _review-request-condition-choices-hook:

=================================
ReviewRequestConditionChoicesHook
=================================

.. versionadded:: 8.0

:py:class:`~reviewboard.extensions.hooks.ReviewRequestConditionChoicesHook`
registers custom condition choices for review requests, which appear when
administrators configure :ref:`integrations`.

For a complete guide to writing condition choices, see
:ref:`extension-review-request-conditions`.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from djblets.conditions.choices import (BaseConditionIntegerChoice,
                                            BaseConditionStringChoice)
    from djblets.conditions.operators import (ConditionOperators,
                                              IsNotOneOfOperator,
                                              IsOneOfOperator,
                                              UnsetOperator)
    from djblets.conditions.values import ConditionValueMultipleChoiceField
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestConditionChoicesHook
    from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin

    if TYPE_CHECKING:
        from reviewboard.reviews.models import ReviewRequest


    class MyCategoryChoice(ReviewRequestConditionChoiceMixin,
                           BaseConditionStringChoice):
        choice_id = 'sample-extension_my-category'
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

        def get_match_value(
            self,
            review_request: ReviewRequest,
            **kwargs,
        ) -> str:
            return review_request.extra_data.get('my_category')


    class MyTaskIDChoice(ReviewRequestConditionChoiceMixin,
                         BaseConditionIntegerChoice):
        choice_id = 'sample-extension_my-task-id'
        name = 'Task ID'

        def get_match_value(
            self,
            review_request: ReviewRequest,
            **kwargs,
        ) -> int:
            return review_request.extra_data.get('my_task_id')


    class SampleExtension(Extension):
        def initialize(self) -> None:
            ReviewRequestConditionChoicesHook(self, [
                MyCategoryChoice,
                MyTaskIDChoice,
            ])
