.. _review-request-fields-hook:

=======================
ReviewRequestFieldsHook
=======================

:py:class:`reviewboard.extensions.hooks.ReviewRequestFieldsHook` allows
extensions to add new fields to a review request. These fields will act like
any other field on a review request. They can be edited, saved along with a
draft, published, and their history can be shown in the "Review request
changed" boxes. Their data can also be accessed through the
``extra_data`` fields of :ref:`webapi2.0-review-request-resource` and
:ref:`webapi2.0-review-request-draft-resource`.

There are many types of fields that can be created, and developers are
encouraged to look at the documentation in
:py:mod:`reviewboard.reviews.fields` for more information on these.

When registering one or more fields through the hook, a fieldset ID must be
specified. This can be a custom fieldset registered by the extension, or it
can be one of the built-in fieldsets:

* ``main`` -
  The main fieldset containing :guilabel:`Description` and
  :guilabel:`Testing Done`.

* ``info`` -
  The :guilabel:`Information` fieldset on the side.

* ``reviewers`` -
  The :guilabel:`Reviewers` fieldset on the side.

Field IDs must be unique, and a field cannot be added to more than one
fieldset. It is best to choose a field ID that contains some sort of
extension-specific information, such as the vendor or the extension ID.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestFieldsHook
    from reviewboard.reviews.fields import BaseEditableField, BaseTextAreaField


    class MilestoneField(BaseEditableField):
        field_id = 'myvendor_milestone'
        label = 'Milestone'


    class NotesField(BaseTextAreaField):
        field_id = 'myvendor_notes'
        label = 'Notes'


    class SampleExtension(Extension):
        def initialize(self):
            ReviewRequestFieldsHook(self, 'info', [MilestoneField])
            ReviewRequestFieldsHook(self, 'main', [NotesField])
