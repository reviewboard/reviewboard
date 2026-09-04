"""Hooks for working with condition choices.

See :ref:`review-request-condition-choices-hook` and
:ref:`user-condition-choices-hook` for instructions.

Version Added:
    8.0
"""

from __future__ import annotations

from djblets.conditions.choices import BaseConditionChoice
from djblets.extensions.hooks import (BaseRegistryMultiItemHook,
                                      ExtensionHookPoint)

from reviewboard.accounts.conditions import user_condition_choices
from reviewboard.reviews.conditions import review_request_condition_choices


class ReviewRequestConditionChoicesHook(
    BaseRegistryMultiItemHook[type[BaseConditionChoice]],
    metaclass=ExtensionHookPoint,
):
    """Hook to add custom condition choices for review requests.

    See :ref:`review-request-condition-choices-hook` for instructions.

    Version Added:
        8.0
    """

    registry = review_request_condition_choices


class UserConditionChoicesHook(
    BaseRegistryMultiItemHook[type[BaseConditionChoice]],
    metaclass=ExtensionHookPoint,
):
    """Hook to add custom condition choices for acting users.

    See :ref:`user-condition-choices-hook` for instructions.

    Version Added:
        9.0
    """

    registry = user_condition_choices
