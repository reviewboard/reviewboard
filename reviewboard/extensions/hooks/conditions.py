"""Hooks for working with condition choices.

See :ref:`review-request-condition-choices-hook` for instructions.

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

    These choices match against the user performing an action. They are
    evaluated with ``condition_set.matches(user=user)``, and may be
    evaluated often. Choices must cache any computed match state (such
    as a set of group IDs) in ``value_state_cache`` or per-request
    state, rather than querying on every evaluation.

    Version Added:
        9.0
    """

    registry = user_condition_choices
