.. _user-condition-choices-hook:

========================
UserConditionChoicesHook
========================

.. versionadded:: 9.0

:py:class:`~reviewboard.extensions.hooks.UserConditionChoicesHook` registers
custom condition choices that match against the *acting user*. This is the
user performing an action, such as the logged-in user viewing a page or
making an API request.

These choices are used for access control. For example, administrators can
limit which users are able to see and use a bug tracker configuration. Your
extension can add choices based on its own data, such as a user's department.

For a complete guide to writing condition choices, see
:ref:`extension-review-request-conditions`. User condition choices work the
same way, with two differences:

1. Choices mix in
   :py:class:`reviewboard.accounts.conditions.UserConditionChoiceMixin`
   instead of
   :py:class:`~reviewboard.reviews.conditions.ReviewRequestConditionChoiceMixin`.

2. :py:meth:`~djblets.conditions.choices.BaseConditionChoice.get_match_value`
   receives a ``user`` argument (a :py:class:`~django.contrib.auth.models.User`)
   instead of a ``review_request`` argument.


Caching Match Values
====================

User conditions may be evaluated many times per request, so
:py:meth:`~djblets.conditions.choices.BaseConditionChoice.get_match_value`
must be cheap to call. If your choice needs to compute or query something
(such as a list of groups), cache the result in the ``value_state_cache``
argument. This cache is shared across every condition evaluated in the same
:py:class:`~djblets.conditions.conditions.ConditionSet`, so the work is
only done once.

The built-in :py:class:`~reviewboard.accounts.conditions.UserInGroupChoice`
uses this to avoid re-querying the user's review groups for each condition.


Example
=======

.. code-block:: python

    from typing import TYPE_CHECKING

    from djblets.conditions.choices import (BaseConditionModelMultipleChoice,
                                            BaseConditionStringChoice)
    from djblets.conditions.operators import (ConditionOperators,
                                              ContainsAnyOperator,
                                              DoesNotContainAnyOperator,
                                              IsNotOneOfOperator,
                                              IsOneOfOperator,
                                              UnsetOperator)
    from djblets.conditions.values import ConditionValueMultipleChoiceField
    from reviewboard.accounts.conditions import UserConditionChoiceMixin
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import UserConditionChoicesHook

    from myextension.models import Department

    if TYPE_CHECKING:
        from collections.abc import Sequence

        from django.contrib.auth.models import User
        from djblets.conditions.values import ValueStateCache


    class MyDepartmentChoice(UserConditionChoiceMixin,
                             BaseConditionModelMultipleChoice):
        queryset = Department.objects.all()
        choice_id = 'sample-extension_my-department'
        name = 'Departments'

        operators = ConditionOperators([
            ContainsAnyOperator,
            DoesNotContainAnyOperator,
        ])

        def get_match_value(
            self,
            user: User,
            value_state_cache: ValueStateCache,
            **kwargs,
        ) -> Sequence[Department]:
            try:
                departments = value_state_cache['my_departments']
            except KeyError:
                departments = list(user.departments.all())
                value_state_cache['my_departments'] = departments

            return departments


    class SampleExtension(Extension):
        def initialize(self) -> None:
            UserConditionChoicesHook(self, [
                MyDepartmentChoice,
            ])
