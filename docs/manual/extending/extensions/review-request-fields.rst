.. _extension-review-request-fields:

============================
Adding Review Request Fields
============================

One of the most common uses for extensions is to add custom fields to review
requests. These fields act like any other field on a review request. They can
be edited, saved along with a draft, published, and their history can be shown
in the "Review request changed" boxes. Their data can be accessed through the
``extra_data`` fields of :ref:`webapi2.0-review-request-resource` and
:ref:`webapi2.0-review-request-draft-resource`.

Creating new review request fields involves a few steps:

* Creating a subclass of
  :py:class:`~reviewboard.reviews.fields.BaseReviewRequestField`. There are
  several different superclass types available which provide different types
  of fields.
* Optionally, creating a JavaScript subclass of
  :js:class:`RB.ReviewRequestFields.BaseFieldView`.
* Use :ref:`review-request-fields-hook` and
  :ref:`review-request-fieldsets-hook` in your extension initialization.


Creating a Field Subclass
=========================

Each field is first defined in Python using a subclass of
:py:class:`~reviewboard.reviews.fields.BaseReviewRequestField`. There are
several built-in types which provide more specific behavior:

* :py:class:`~reviewboard.reviews.fields.BaseEditableField` -
  A simple single-line text field.

* :py:class:`~reviewboard.reviews.fields.BaseTextAreaField` -
  A multi-line text field, with optional Markdown support.

* :py:class:`~reviewboard.reviews.fields.BaseCommaEditableField` -
  A single-line text field which allows selecting multiple comma-separated
  values.

* :py:class:`~reviewboard.reviews.fields.BaseCheckboxField` -
  A boolean-valued field which is displayed as a checkbox.

* :py:class:`~reviewboard.reviews.fields.BaseDropdownField` -
  A field which allows selecting one of several predefined options. This
  additionally requires defining the
  :py:attr:`~reviewboard.reviews.fields.BaseDropdownField.options` attribute, which is a
  list of 2-tuples containing a ``value`` and ``label``.

* :py:class:`~reviewboard.reviews.fields.BaseDateField` -
  A field which allows selecting a date.

At a minimum, your subclass will need to define two class attributes,
:py:attr:`~reviewboard.reviews.fields.BaseReviewRequestField.field_id` and
:py:attr:`~reviewboard.reviews.fields.BaseReviewRequestField.label`. Depending
on the type, there may be additional attributes which can be overridden to
manipulate the behavior.


Examples
--------

.. code-block:: python

    from reviewboard.reviews.fields import (BaseCommaEditableField,
                                            BaseCheckboxField,
                                            BaseDateField,
                                            BaseDropdownField,
                                            BaseEditableField,
                                            BaseTextAreaField)


    class MilestoneField(BaseEditableField):
        field_id = 'myvendor_milestone'
        label = 'Milestone'


    class NotesField(BaseTextAreaField):
        field_id = 'myvendor_notes'
        label = 'Notes'


    class TagsField(BaseCommaEditableField):
        field_id = 'myvendor_tags'
        label = 'Tags'


    class SecurityRelatedField(BaseCheckboxField):
        field_id = 'myvendor_security_related'
        label = 'Security Related'


    class PriorityField(BaseDropdownField):
        field_id = 'myvendor_priority'
        label = 'Priority'
        options = [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ]


    class DueDateField(BaseCommaEditableField):
        field_id = 'myvendor_due'
        label = 'Due Date'


Creating a JavaScript FieldView Subclass
========================================

Each Python field type has an associated JavaScript view which handles user
interaction and value serialization. If you subclass one of the builtin field
types, you do not need to create an override for these, but doing so can allow
you to implement more advanced UIs such as autocomplete or custom editor
widgets.


Example
-------

Suppose we wanted a field which used Selectize_ as its editor. First, we'd
define a JavaScript view that set up Selectize on the editor's field:

.. code-block:: javascript

    window.MyExtension = {};

    MyExtension.SelectizeFieldView =
        RB.ReviewRequestFields.TextFieldView.extend({

        /**
         * Render the view.
         */
        render() {
            RB.ReviewRequestFields.TextFieldView.prototype.render.call(this);

            this.inlineEditorView.$field.selectize();
        },
    });


We can then reference the new JavaScript view using the
:py:attr:`reviewboard.reviews.fields.BaseReviewRequestField.js_view_class`
attribute.


.. code-block:: python

    from reviewboard.reviews.fields import BaseEditableField


    class MilestoneField(BaseEditableField):
        field_id = 'myvendor_milestone'
        label = 'Milestone'
        js_view_class = 'MyExtension.SelectizeField'


Extension Hooks
===============

Review Board provides two hooks to add your custom fields.
:ref:`review-request-fields-hook` can be used to add fields to one of the
builtin sections. :ref:`review-request-fieldsets-hook` can add entirely new
sections. The documentation for each of these hooks shows example usage.


.. _Selectize: https://selectize.github.io/selectize.js/
