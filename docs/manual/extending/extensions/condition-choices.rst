.. _extension-review-request-conditions:

=====================================
Customizing Review Request Conditions
=====================================

Conditions allow administrators to define rules for when most
:ref:`integrations <integrations>` are used. For example, a Slack integration
can be set up to only post when a review request targets a specific
repository, or when the owner is a member of a certain group.

Review Board provides a set of built-in choices to select from when
configuring conditions. For example, a review request's repository, review
groups, branches, :ref:`user roles <user-roles>`, and more.

Extensions can add their own available choices. This can be used along with
:ref:`custom review request fields <extension-review-request-fields>`, custom
extension-stored or API-stored data in :py:attr:`ReviewRequest.extra_data
<reviewboard.reviews.models.ReviewRequest.extra_data>`, or with logic you
define in your extension.

There are three key things to know about building conditions:

1. **Condition choices are created** by subclassing one of the base
   classes from :py:mod:`djblets.conditions.choices` and mixing in
   :py:class:`reviewboard.reviews.conditions.
   ReviewRequestConditionChoiceMixin`.

2. **Condition choices declare operators** (such as :guilabel:`Is`,
   :guilabel:`Contains`, :guilabel:`Is one of`, or :guilabel:`Starts with`)
   by setting the
   :py:attr:`~djblets.conditions.choices.BaseConditionChoice.operators`
   attribute.

3. **Condition choices are then registered** by passing their *classes* (not
   instances) to :py:class:`~reviewboard.extensions.hooks
   .ReviewRequestConditionChoicesHook`.


Choosing a Base Class
=====================

Djblets_, Review Board's companion library for writing extensions, provides
several ready-made base classes you can choose from. Each has a built-in set
of standard operators.

These are:

* :py:class:`djblets.conditions.choices.BaseConditionBooleanChoice`

  Used for boolean (true/false) values. This provides:

  * :guilabel:`Is` (with a :guilabel:`True` / :guilabel:`False` selector)

* :py:class:`djblets.conditions.choices.BaseConditionIntegerChoice`

  Used for integer values. This provides:

  * :guilabel:`Is` / :guilabel:`Is not`
  * :guilabel:`Greater than` / :guilabel:`Less than`

* :py:class:`djblets.conditions.choices.BaseConditionStringChoice`

  Used for text/string values. This provides the operators:

  * :guilabel:`Is` / :guilabel:`Is not`
  * :guilabel:`Contains` / :guilabel:`Does not contain`
  * :guilabel:`Starts with` / :guilabel:`Ends with`
  * :guilabel:`Matches regex` / :guilabel:`Does not match regex`

* :py:class:`djblets.conditions.choices.BaseConditionModelChoice`

  Used to select an optional single database object from a list. This
  provides:

  * :guilabel:`Is unset`
  * :guilabel:`Is` / :guilabel:`Is not`

* :py:class:`djblets.conditions.choices.BaseConditionRequiredModelChoice`

  Used to select a required single database object from a list. This
  provides:

  * :guilabel:`Is` / :guilabel:`Is not`

* :py:class:`djblets.conditions.choices.BaseConditionModelMultipleChoice`

  Used to select one or more database options from a list.

  * :guilabel:`Any` / :guilabel:`None`
  * :guilabel:`Is one of` / :guilabel:`Is not one of`

* :py:class:`djblets.conditions.choices.BaseConditionChoice`

  A base class for defining entirely-new condition choices.

  Subclasses are required to set
  :py:attr:`~djblets.conditions.choices.BaseConditionChoice.operators` and
  :py:attr:`~djblets.conditions.choices.BaseConditionChoice.
  default_value_field`.


Creating a Choice
=================

To create a condition choice:

1. Subclass one of the base classes above and mix in
   :py:class:`reviewboard.reviews.conditions.ReviewRequestConditionChoiceMixin`.

2. Define the required attributes:

   * :py:attr:`~djblets.conditions.choices.BaseConditionChoice.choice_id`

     A unique string identifier for the choice.

     You should use a vendor or extension prefix to avoid conflicts with
     Review Board's built-in choices or other extensions.

     Allowed characters: ``A-Z``, ``a-z``, ``0-9``, ``-``, and ``_``.

   * :py:attr:`~djblets.conditions.choices.BaseConditionChoice.name`

     The human-readable name shown in the condition selector. This should be
     short and descriptive.

3. Define the required method:

   * :py:meth:`~djblets.conditions.choices.BaseConditionChoice.
     get_match_value`

     Returns the value that will be matched against, using the user's
     selected operator.

     This would return any data your extension stores or computes that would
     determine if the condition choice applies.

     This will receive the review request as its first argument, and must
     take ``**kwargs`` as the last argument.

     We'll talk about this more in a minute.


Here's an example condition choice that matches a milestone stored by your
extension.

.. code-block:: python

   from djblets.conditions.choices import BaseConditionStringChoice
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest


   class MilestoneChoice(ReviewRequestConditionChoiceMixin,
                         BaseConditionStringChoice):
       choice_id = 'myvendor_my-milestone'
       name = 'Milestone'

       def get_match_value(
           self,
           review_request: ReviewRequest,
           **kwargs,
       ) -> str:
           return review_request.extra_data.get('myvendor_milestone', '')


Model Choices
-------------

:py:class:`~djblets.conditions.choices.BaseConditionModelChoice`,
:py:class:`~djblets.conditions.choices.BaseConditionRequiredModelChoice`,
and :py:class:`~djblets.conditions.choices.BaseConditionModelMultipleChoice`
all work off of the database, using Django database models.

These take a
:py:attr:`~djblets.conditions.choices.ModelQueryChoiceMixin.queryset`
attribute that populates the entries to show and match against.

You'll usually only use this if your extension is providing :ref:`its own
database models <extension-models>` that have a relation back to the
:py:class:`~reviewboard.reviews.models.ReviewRequest` model.

For example:

.. code-block:: python

   from django.db.models import QuerySet
   from djblets.conditions.choices import BaseConditionModelMultipleChoice
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest

   from myextension.models import Project


   class ProjectsChoice(ReviewRequestConditionChoiceMixin,
                        BaseConditionModelMultipleChoice):
       choice_id = 'myvendor_projects'
       name = 'Projects'
       queryset = Project.objects.all()

       def get_match_value(
           self,
           review_request: ReviewRequest,
           **kwargs,
       ) -> QuerySet[Project]:
           # Return all entries associated with this review request.
           return review_request.myvendor_projects.all()


Caching Match Values
--------------------

Computing a match value may be expensive. For example, you might query the
database, or you might look something up in an external system. In these
cases, you'll want to cache the computed match value.

Caching avoids performing these lookups or computations multiple times in
the event where the user has configured your condition choice multiple times
in the same set of rules.

:py:meth:`~djblets.conditions.choices.BaseConditionChoice.get_match_value`
takes a ``value_state_cache`` keyword argument, which is a dictionary shared
across all conditions the user has chosen. Any state you compute can (and
should!) be stored there.

We'll update our example from above to build in some caching:

.. code-block:: python

   from collections.abc import Sequence

   from djblets.conditions.choices import BaseConditionModelMultipleChoice
   from djblets.conditions.values import ValueStateCache
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest

   from myextension.models import Project


   class ProjectsChoice(ReviewRequestConditionChoiceMixin,
                        BaseConditionModelMultipleChoice):
       choice_id = 'myvendor_projects'
       name = 'Projects'
       queryset = Project.objects.all()

       def get_match_value(
           self,
           review_request: ReviewRequest,
           value_state_cache: ValueStateCache,
           **kwargs,
       ) -> Sequence[Project]:
           try:
               projects = value_state_cache['myvendor_projects']
           except KeyError:
               projects = list(review_request.myvendor_projects.all())
               value_state_cache['myvendor_projects'] = projects

           return projects


Matching Against a List of Values
---------------------------------

Some choices represent a list of values (such as the files changed in a
diff). You may want to give users the ability to match against *any* item
in the list, instead of trying to match the entire list itself.

In the diff files example, you may want the user to be able to choose
:guilabel:`Changed file path -> Starts with -> "docs/"`, and if any of the
files start with ``docs/``, it would be a match.

To do this, simply mix
:py:class:`~djblets.conditions.choices.ConditionChoiceMatchListItemsMixin`
into your class.

For example:

.. code-block:: python

   from collections.abc import Sequence

   from djblets.conditions.choices import (BaseConditionStringChoice,
                                           ConditionChoiceMatchListItemsMixin)
   from djblets.conditions.values import ValueStateCache
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest


   class ChangedFileChoice(ConditionChoiceMatchListItemsMixin,
                           ReviewRequestConditionChoiceMixin,
                           BaseConditionStringChoice):
       choice_id = 'myvendor_changed-file'
       name = 'Changed file path'

       def get_match_value(
           self,
           review_request: ReviewRequest,
           value_state_cache: ValueStateCache,
           **kwargs,
       ) -> Sequence[str]:
           try:
               files = value_state_cache['myvendor_changed_files']
           except KeyError:
               diffset = review_request.get_latest_diffset()
               files: list[str] = []

               if diffset is not None:
                   files = list(diffset.files.values_list('dest_file',
                                                          flat=True))

               value_state_cache['myvendor_changed_files'] = files

           return files

This is best used with
:py:class:`~djblets.conditions.operators.ContainsOperator` and
:py:class:`~djblets.conditions.operators.DoesNotContainOperator`.

If you want to require that *every* item in the list matches, instead of just
*any* item, you can set :py:attr:`~djblets.conditions.choices.ConditionChoiceMatchListItemsMixin.require_match_all_items` to ``True`` on the class:

.. code-block:: python

   ...

   class ChangedFileChoice(ConditionChoiceMatchListItemsMixin,
                           ReviewRequestConditionChoiceMixin,
                           BaseConditionStringChoice):
       require_match_all_items = True

       ...


Customizing Operators
=====================

Every condition choice needs operators.

Operators define how a match value is compared against a user's provided
value.

As we saw above, there are base classes for condition choices that provide
a default list of operators. You can use these as-is, or you can customize
the list.

For example, if we wanted to use
:py:class:`~djblets.conditions.choices.BaseConditionStringChoice` but limit
our operators to :guilabel:`Is one of` and :guilabel:`Is not one of`, we could
do:

.. code-block:: python

   from djblets.conditions.choices import BaseConditionStringChoice
   from djblets.conditions.operators import (ConditionOperators,
                                             IsNotOneOfOperator,
                                             IsOneOfOperator)
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin


   class MilestoneChoice(ReviewRequestConditionChoiceMixin,
                         BaseConditionStringChoice):
       ...

       operators = ConditionOperators([
           IsOneOfOperator,
           IsNotOneOfOperator,
       ])


Built-in operators
------------------

There are many built-in operators you can use. Most have a twin operator
that matches the opposite values, so we'll group them that way:

* Check whether there's a match value:

  * :py:class:`~djblets.conditions.operators.AnyOperator`
    (:guilabel:`Has a value`)

  * :py:class:`~djblets.conditions.operators.UnsetOperator`
    (:guilabel:`Is unset`)

* Check whether a value equals the match value:

  * :py:class:`~djblets.conditions.operators.IsOperator`
    (:guilabel:`Is`)

  * :py:class:`~djblets.conditions.operators.IsNotOperator`
    (:guilabel:`Is not`)

* Check whether a match value is found in a set of user-provided values:

  * :py:class:`~djblets.conditions.operators.IsOneOfOperator`
    (:guilabel:`Is one of`)

  * :py:class:`~djblets.conditions.operators.IsNotOneOfOperator`
    (:guilabel:`Is not one of`)

* Check whether the user-provided value is found in a set of match values:

  * :py:class:`~djblets.conditions.operators.ContainsOperator`
    (:guilabel:`Contains`)

  * :py:class:`~djblets.conditions.operators.DoesNotContainOperator`
    (:guilabel:`Does not contain`)

* Check whether the match value contains any of the user-provided values:

  * :py:class:`~djblets.conditions.operators.ContainsAnyOperator`
    (:guilabel:`Any of`)

  * :py:class:`~djblets.conditions.operators.DoesNotContainAnyOperator`
    (:guilabel:`Not any of`)

* Checks whether the match value starts with a user-provided prefix:

  * :py:class:`~djblets.conditions.operators.StartsWithOperator`
    (:guilabel:`Starts with`)

* Checks whether the match value ends with a user-provided suffix:

  * :py:class:`~djblets.conditions.operators.EndsWithOperator`
    (:guilabel:`Ends with`)

* Checks whether the match value is greater than a user-provided value:

  * :py:class:`~djblets.conditions.operators.GreaterThanOperator`
    (:guilabel:`Greater than`)

* Checks whether the match value is less than a user-provided value:

  * :py:class:`~djblets.conditions.operators.LessThanOperator`
    (:guilabel:`Less than`)

* Checks whether the user-provided Python Regex (Regular Expression) pattern
  matches the match value:

  * :py:class:`~djblets.conditions.operators.MatchesRegexOperator`
    (:guilabel:`Matches regex`)

  * :py:class:`~djblets.conditions.operators.DoesNotMatchRegexOperator`
    (:guilabel:`Does not match regex`)


Renaming an Operator
--------------------

Sometimes the default label for an operator isn't quite right for your
condition choice. You may want to give it a different name.

You can easily do this with
:py:meth:`~djblets.conditions.operators.BaseConditionOperator.with_overrides`:

.. code-block:: python

    from djblets.conditions.operators import AnyOperator, UnsetOperator

    ...

    operators = ConditionOperators([
        AnyOperator.with_overrides(name='Has any projects'),
        UnsetOperator.with_overrides(name='Has no projects'),
    ])


Writing a Custom Operator
--------------------------

The built-in operators may not be right for your condition choice. You may
want to create your own operator.

To write a custom operator:

1. Subclass :py:class:`djblets.conditions.operators.BaseConditionOperator`.

2. Define the required attributes:

   * :py:attr:`~djblets.conditions.operators.BaseConditionOperator.operator_id`

     A unique string identifier for the operator.

     You should use a vendor or extension prefix to avoid conflicts with
     Review Board's built-in operators or other extensions.

     Allowed characters: ``A-Z``, ``a-z``, ``0-9``, ``-``, and ``_``.

   * :py:attr:`~djblets.conditions.operators.BaseConditionOperator.name`

     The human-readable name shown in the operator selector. This should be
     short and descriptive.

   * :py:attr:`~djblets.conditions.operators.BaseConditionOperator.value_field`

     The field type the user will use to provide a value.

     This can be explicitly set to ``None`` if the operator doesn't take a
     value. If it's omitted from the class, the choice's default value field
     will be used.

3. Define the required method:

   * :py:meth:`~djblets.conditions.operators.BaseConditionOperator.matches`

     Returns whether the operator matches the choice-provided match value
     against the user-provided condition value (if one is available).


For example:

.. code-block:: python

   from djblets.conditions.choices import BaseConditionStringChoice
   from djblets.conditions.operators import (BaseConditionOperator,
                                             ConditionOperators)
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest


   # This operator doesn't take a provided value. It just matches
   # against the string "urgent".
   class IsUrgentOperator(BaseConditionOperator):
       operator_id = 'myvendor_is-urgent'
       name = 'Is urgent'
       value_field = None  # No user-provided value is needed.

       def matches(
           self,
           match_value: str,
           **kwargs,
       ) -> bool:
           return match_value == 'urgent'


   # This operator takes a text field meant to include a priority level
   # that would append to "priority". For example, a user-provided value
   # of "1" would match "priority1".
   #
   # This doesn't set `value_field`, so it uses the default for the
   # choice.
   class IsPriorityLevelOperator(BaseConditionOperator):
       operator_id = 'myvendor_priority-level'
       name = 'Priority level'

       def matches(
           self,
           match_value: str,
           condition_value: str,
           **kwargs,
       ) -> bool:
           return match_value == f'priority{condition_value}'


   class PriorityChoice(ReviewRequestConditionChoiceMixin,
                        BaseConditionStringChoice):
       choice_id = 'myvendor_my-priority'
       name = 'Priority'

       operators = ConditionOperators([
           IsUrgentOperator,
           IsPriorityLevelOperator,
       ])

       def get_match_value(
           self,
           review_request: ReviewRequest,
           **kwargs,
       ) -> str:
           return review_request.extra_data.get('myvendor_priority', '')


Customizing the Value Field
===========================

We talked about an operator's value field. Operators may set a custom field,
disable a field, or fall back on the choice's value field.

If you're subclassing one of the built-in condition choice classes, like
:py:class:`~djblets.conditions.choices.BaseConditionIntegerChoice`, a suitable
default value field will be supplied for you.

If you want to customize the field used, you can override
:py:attr:`~djblets.conditions.choices.BaseConditionChoice.default_value_field`.

In most cases, you'll want to use one of the pre-built field types:

* :py:class:`~djblets.conditions.values.ConditionValueBooleanField`

  A drop-down with "True" and "False" entries.

* :py:class:`~djblets.conditions.values.ConditionValueCharField`

  Single-line text input.

* :py:class:`~djblets.conditions.values.ConditionValueIntegerField`

  A field that validates as an integer.

* :py:class:`~djblets.conditions.values.ConditionValueRegexField`

  A text input that validates and compiles as a Python Regex (Regular
  Expression), used for pattern matching.

* :py:class:`~djblets.conditions.values.ConditionValueModelField`

  A field for selecting a specific database model entry.

* :py:class:`~djblets.conditions.values.ConditionValueMultipleModelField`

  A field for selecting zero or more database model entries.

* :py:class:`~djblets.conditions.values.ConditionValueMultipleChoiceField`

  A multiple choice of values (as we'll see next).

We'll look at a couple of these.


Restricting to a Fixed Set of Values
-------------------------------------

A good reason to set your own field is to limit the options available to
the user. You can use
:py:class:`~djblets.conditions.values.ConditionValueMultipleChoiceField` to
provide a fixed list of options to choose from.

Each option in the list is a Python tuple in the form of ``(value, label)``.
It also takes a :ref:`generic type <python:generics>` (the ``[str]`` after
the name in the code sample below), which specifies the type of value found in
the list.

This is best used with
:py:class:`~djblets.conditions.operators.IsOneOfOperator` and
:py:class:`~djblets.conditions.operators.IsNotOneOfOperator`.

For example:

.. code-block:: python

   from djblets.conditions.choices import BaseConditionStringChoice
   from djblets.conditions.operators import (ConditionOperators,
                                             IsNotOneOfOperator,
                                             IsOneOfOperator)
   from djblets.conditions.values import ConditionValueMultipleChoiceField
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin


   class CategoryChoice(ReviewRequestConditionChoiceMixin,
                        BaseConditionStringChoice):
       choice_id = 'myvendor_category'
       name = 'Category'

       operators = ConditionOperators([
           IsOneOfOperator,
           IsNotOneOfOperator,
       ])

       default_value_field = ConditionValueMultipleChoiceField[str](choices=[
           ('architecture', 'Architecture'),
           ('bug', 'Bug'),
           ('docs', 'Documentation'),
           ('feature', 'Feature'),
           ('security', 'Security'),
           ('whimsy', 'Whimsy'),
       ])

       ...


Using a Django Form Field
--------------------------

Another reason to override the field type is to use a specific (or a custom)
:doc:`Django form field <django:ref/forms/fields>`. You'll wrap this with
:py:class:`~djblets.conditions.values.ConditionValueFormField`.

You can use this to customize the attributes going into the form or the
validation behavior. Any Django form field can be provided.

For example:

.. code-block:: python

   from django import forms
   from djblets.conditions.choices import BaseConditionIntegerChoice
   from djblets.conditions.values import ConditionValueFormField
   from reviewboard.reviews.conditions import ReviewRequestConditionChoiceMixin
   from reviewboard.reviews.models import ReviewRequest


   class ScoreChoice(ReviewRequestConditionChoiceMixin,
                     BaseConditionIntegerChoice):
       choice_id = 'myvendor_score'
       name = 'Review Score'

       default_value_field = ConditionValueFormField(forms.IntegerField(
           min_value=0,
           max_value=100,
       ))

       def get_match_value(
           self,
           review_request: ReviewRequest,
           **kwargs,
       ) -> int:
           return review_request.extra_data.get('myvendor_score', 0)


Registering Choices
===================

In order for your condition choice to appear as an option for users, you'll
need to register it. This is done by passing one or more condition choice
classes (not instances) to a :ref:`review-request-condition-choices-hook`:

.. code-block:: python

   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import ReviewRequestConditionChoicesHook


   class MyExtension(Extension):
       def initialize(self) -> None:
           ReviewRequestConditionChoicesHook(self, [
               MyCategoryChoice,
               MyTaskIDChoice,
           ])

Your choices will immediately appear in the condition selector when
administrators configure any integration.
