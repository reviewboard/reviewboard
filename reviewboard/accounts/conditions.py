"""Condition choices and operators for acting users.

These condition choices match against the user performing an action,
rather than data on a review request. They are used for access control,
such as deciding whether a user may interact with a configured bug
tracker.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from djblets.conditions.choices import (
    BaseConditionBooleanChoice,
    BaseConditionChoice,
    BaseConditionModelMultipleChoice,
    ConditionChoices,
)
from djblets.conditions.operators import (
    AnyOperator,
    ConditionOperators,
    ContainsAnyOperator,
    DoesNotContainAnyOperator,
    IsNotOneOfOperator,
    IsOneOfOperator,
    UnsetOperator,
)

from reviewboard.reviews.models import Group
from reviewboard.site.conditions import LocalSiteModelChoiceMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from djblets.conditions.values import ValueStateCache


class UserConditionChoiceMixin:
    """Mixin for condition choices that operate off an acting user.

    Choices using this mixin are evaluated with
    ``condition_set.matches(user=user)``.

    Version Added:
        9.0
    """

    value_kwarg = 'user'


class UserInGroupChoice(UserConditionChoiceMixin,
                        LocalSiteModelChoiceMixin,
                        BaseConditionModelMultipleChoice):
    """A condition choice for matching the user's review groups.

    This matches the review groups the acting user is a member of.

    Version Added:
        9.0
    """

    queryset = Group.objects.all()
    choice_id = 'user-in-group'
    name = _("User's review groups")

    operators = ConditionOperators([
        AnyOperator.with_overrides(name=_('Any review groups')),
        UnsetOperator.with_overrides(name=_('No review groups')),
        ContainsAnyOperator,
        DoesNotContainAnyOperator,
    ])

    def get_match_value(
        self,
        user: User,
        value_state_cache: ValueStateCache,
        **kwargs,
    ) -> Sequence[Group]:
        """Return the user's review groups used for matching.

        The computed group list is cached in ``value_state_cache``, so
        repeated evaluations against the same user do not re-query.

        Args:
            user (django.contrib.auth.models.User):
                The acting user.

            value_state_cache (dict):
                A cache shared across condition evaluations.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            list of reviewboard.reviews.models.group.Group:
            The review groups the user belongs to.
        """
        try:
            result = value_state_cache['user_review_groups']
        except KeyError:
            result = list(user.review_groups.all())
            value_state_cache['user_review_groups'] = result

        return result


class UserIsSuperuserChoice(UserConditionChoiceMixin,
                            BaseConditionBooleanChoice):
    """A condition choice for matching whether the user is a superuser.

    Version Added:
        9.0
    """

    choice_id = 'user-is-superuser'
    name = _('User is superuser')

    def get_match_value(
        self,
        user: User,
        **kwargs,
    ) -> bool:
        """Return whether the user is a superuser.

        Args:
            user (django.contrib.auth.models.User):
                The acting user.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if the user is a superuser.
        """
        return user.is_superuser


class UserIsOneOfChoice(UserConditionChoiceMixin,
                        LocalSiteModelChoiceMixin,
                        BaseConditionModelMultipleChoice):
    """A condition choice for matching against a list of users.

    Version Added:
        9.0
    """

    queryset = User.objects.all()
    choice_id = 'user-is-one-of'
    name = _('User')

    operators = ConditionOperators([
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    def get_match_value(
        self,
        user: User,
        **kwargs,
    ) -> User:
        """Return the user used for matching.

        Args:
            user (django.contrib.auth.models.User):
                The acting user.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            django.contrib.auth.models.User:
            The acting user.
        """
        return user


class UserConditionChoices(ConditionChoices):
    """A standard set of acting-user condition choices.

    These match against the user performing an action. Extensions can
    register additional choices through
    :py:class:`~reviewboard.extensions.hooks.UserConditionChoicesHook`.

    Version Added:
        9.0
    """

    choice_classes: ClassVar[list[type[BaseConditionChoice]]] = [
        UserInGroupChoice,
        UserIsSuperuserChoice,
        UserIsOneOfChoice,
    ]


#: All condition choices available for acting users.
#:
#: This can be used in condition fields or to register new conditions.
#:
#: Version Added:
#:     9.0
user_condition_choices = UserConditionChoices()
