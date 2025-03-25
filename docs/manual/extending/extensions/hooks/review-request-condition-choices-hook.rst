.. _review-request-condition-choices-hook:

=================================
ReviewRequestConditionChoicesHook
=================================

.. versionadded:: 7.1

When configuring :ref:`integrations`, administrators can choose the conditions in
which an integration will apply. For example, a Slack integration can be
configured to post review request updates to a channel only when the review
request is assigned to certain teams.

By default, Review Board provides a number of conditions to choose from, but
extensions can add custom choices using
:py:class:`~reviewboard.extensions.hooks.conditions.
ReviewRequestConditionChoicesHook`.

This is particularly useful in combination with :ref:`custom fields
<review-request-fields-hook>` or when storing custom data in review requests
:ref:`via the API <webapi2.0-extra-data>` or extensions.


Creating Choices
================

When creating a custom choice, you'll want to subclass one of the following
base classes:

* :py:class:`djblets.conditions.choices.BaseConditionChoice`:

  The top-most base class used for condition choices. This is the right base
  class when you need specialized logic and none of the other base classes
  are appropriate.

* :py:class:`djblets.conditions.choices.BaseConditionBooleanChoice`:

  Base class for boolean choices. This provides the following operators:

  * ``[Choice] Is [True/False]``

* :py:class:`djblets.conditions.choices.BaseConditionIntegerChoice`:

  Base class for integer choices. This provides the following operators:

  * ``[Choice] Is [Integer]``
  * ``[Choice] Is Not [Integer]``
  * ``[Choice] Greater Than [Integer]``
  * ``[Choice] Less Than [Integer]``

* :py:class:`djblets.conditions.choices.BaseConditionStringChoice`:

  Base class for string (text) choices. This provides the following operators:

  * ``[Choice] Is [String]``
  * ``[Choice] Is Not [String]``
  * ``[Choice] Contains [String]``
  * ``[Choice] Does Not Contain [String]``
  * ``[Choice] Starts With [String]``
  * ``[Choice] Ends With [String]``
  * ``[Choice] Matches Regex [String]``
  * ``[Choice] Does Not Match Regex [String]``

* :py:class:`djblets.conditions.choices.BaseConditionModelChoice`:

  Base class for choices that query the database, allowing users to select
  a single database entry from a list to match. This provides the following
  operators:

  * ``[Choice] Is Unset``
  * ``[Choice] Is [Database Entry]``
  * ``[Choice] Is Not [Database Entry]``

* :py:class:`djblets.conditions.choices.BaseConditionModelMultipleChoice`:

  Base class for choices that query the database, allowing users to select
  multiple database entries from a list to match. This provides the following
  operators:

  * ``[Choice] Is Any``
  * ``[Choice] Is None``
  * ``[Choice] Is One Of [One or More Database Entries]``
  * ``[Choice] Is Not One Of [One or More Database Entries]``


You will also want to mix in
:py:class:`reviewboard.reviews.conditions.ReviewRequestConditionChoiceMixin`.

For each choice, you will need to define the following:

* :py:attr:`~djblets.conditions.choices.BaseConditionChoice.choice_id`:

  A unique ID for the choice. It's recommended to prefix this with your
  vendor or extension ID, so that you don't conflict with other choices.

  Allowed characters are ``A-Z``, ``a-z``, ``0-9``, ``-``, and ``_``.

* :py:attr:`~djblets.conditions.choices.BaseConditionChoice.name`:

  The localizable display name for the choice.

* :py:meth:`~djblets.conditions.choices.BaseConditionChoice.get_match_value`:

  This method must take in the review request as an argument and return the
  value the condition choice represents.

You can also override:

* :py:attr:`~djblets.conditions.choices.BaseConditionChoice.operators`:

  An explicit list of operators to use for your choice. Useful if you want
  to limit the list of operators, add custom operators, or define custom
  labels for operators.

* :py:attr:`~djblets.conditions.choices.BaseConditionChoice.default_value_field`:

  An instance or function returning an instance of a
  :py:class:`~djblets.conditions.values.BaseConditionValueField` from
  :py:mod:`djblets.conditions.values`.

  These wrap a form field for providing a value to match against. You can
  use these to craft custom fields.

  In particular, you may want to use
  :py:class:`djblets.conditions.values.ConditionValueMultipleChoiceField` to
  provide an explicit set of values.


Example
=======

The following extension will match conditions against in-house
``my_category`` and ``my_task_id`` extra data set on a review request via
an extension or an API, or provided by a custom field.


.. code-block:: python

    from django.utils.translation import gettext_lazy as _
    from djblets.conditions.choices import (BaseConditionIntegerChoice,
                                            BaseConditionStringChoice
    from djblets.conditions.operators import (ConditionOperators,
                                              IsNotOneOfOperator,
                                              IsOneOfOperator,
                                              UnsetOperator)
    from djblets.conditions.values import ConditionValueMultipleChoiceField
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestConditionChoicesHook
    from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin


    class MyCategoryChoice(ReviewRequestConditionChoiceMixin,
                           BaseConditionStringChoice):
        choice_id = 'sample-extension_my-category'
        name = _('Category')

        operators = ConditionOperators([
            UnsetOperator,
            IsOneOfOperator,
            IsNotOneOfOperator,
        ])

        default_value_field = ConditionValueMultipleChoiceField[str](choices=[
            ('architecture', _('Architecture')),
            ('bug', _('Bug')),
            ('docs', _('Documentation')),
            ('feature', _('Feature')),
            ('security', _('Security')),
        ])

        def get_match_value(self, review_request, **kwargs):
            # This would return a string.
            return review_request.extra_data.get('my_category')


    class MyTaskIDChoice(ReviewRequestConditionChoiceMixin,
                         BaseConditionIntegerChoice):
        choice_id = 'sample-extension_my-task-id'
        name = _('Task ID')

        def get_match_value(self, review_request, **kwargs):
            # This would return an integer.
            return review_request.extra_data.get('my_task_id')


    class SampleExtension(Extension):
        def initialize(self):
            ReviewRequestConditionChoicesHook(self, [
                MyCategoryChoice,
                MyTaskIDChoice,
            ])
