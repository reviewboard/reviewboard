"""Hooks for working with condition choices.

See :ref:`review-request-condition-choices-hook` for instructions.

Version Added:
    8.0
"""

from __future__ import annotations

from typing import Type

from djblets.conditions.choices import BaseConditionChoice
from djblets.extensions.hooks import (BaseRegistryMultiItemHook,
                                      ExtensionHookPoint)

from reviewboard.reviews.conditions import review_request_condition_choices


class ReviewRequestConditionChoicesHook(
    BaseRegistryMultiItemHook[Type[BaseConditionChoice]],
    metaclass=ExtensionHookPoint,
):
    """Hook to add custom condition choices for review requests.

    See :ref:`review-request-condition-choices-hook` for instructions.

    Version Added:
        8.0
    """

    registry = review_request_condition_choices
