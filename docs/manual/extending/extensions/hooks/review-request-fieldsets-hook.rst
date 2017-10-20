.. _review-request-fieldsets-hook:

==========================
ReviewRequestFieldSetsHook
==========================

:py:class:`reviewboard.extensions.hooks.ReviewRequestFieldSetsHook` allows
extensions to create grouped sets of fields on the review request page.
These are equivalent to the :guilabel:`Information` and :guilabel:`Reviewers`
sections.

See :ref:`extension-review-request-fields` for a thorough guide on adding new
fields.

A caller must subclass
:py:class:`reviewboard.reviews.fields.BaseReviewRequestFieldSet` and fill in
the required fields, :py:attr:`fieldset_id` and :py:attr:`label`. It may also
include a hard-coded list of default field classes in the
:py:attr:`field_classes` attribute.

A custom fieldset class can be added by instantiating the hook, passing in
a list of fieldset classes.

Fieldset IDs must be unique. It is best to choose a fieldset ID that contains
some sort of extension-specific information, such as the vendor or the
extension ID. Fieldset IDs are used when registering new fields (using
:ref:`review-request-fields-hook`) in order to specify where the field
should appear.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewRequestFieldSetsHook
    from reviewboard.reviews.fields import (BaseEditableField,
                                            BaseReviewRequestFieldSet)


    class MilestoneField(BaseEditableField):
        field_id = 'myvendor_milestone'
        label = 'Milestone'


    class SampleFieldSet(BaseReviewRequestFieldSet):
        fieldset_id = 'myvendor_my_fields'
        label = 'My Fields'
        field_classes = [MilestoneField]


    class SampleExtension(Extension):
        def initialize(self):
            ReviewRequestFieldSetsHook(self, [SampleFieldSet])
