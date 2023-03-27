"""Hooks for adding new review request fields."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.reviews.fields import (get_review_request_fieldset,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)


class ReviewRequestFieldSetsHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for creating fieldsets on the side of the review request page.

    A fieldset contains one or more fields, and is mainly used to separate
    groups of fields from each other.

    This takes a list of fieldset classes as parameters, which it will
    later instantiate as necessary. Each fieldset can be pre-populated with
    one or more custom field classes.
    """

    def initialize(self, fieldsets):
        """Initialize the hook.

        This will register each of the provided fieldsets for review
        requests.

        Args:
            fieldsets (list of type):
                The list of fieldset classes to register. Each must be a
                subclass of
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`.

        Raises:
            djblets.registries.errors.ItemLookupError:
                A fieldset was already registered matching an ID from this
                list.
        """
        self.fieldsets = fieldsets

        for fieldset in fieldsets:
            register_review_request_fieldset(fieldset)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the fieldsets from the review requests.
        """
        for fieldset in self.fieldsets:
            unregister_review_request_fieldset(fieldset)


class ReviewRequestFieldsHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for creating fields on the review request page.

    This is used to create custom fields on a review request page for
    requesting and storing data. A field can be editable, or it can be only
    for display purposes. See the classes in
    :py:mod:`reviewboard.reviews.fields` for more information and
    documentation.

    This hook takes the ID of a registered fieldset where the provided
    field classes should be added. Review Board supplies three built-in
    fieldset IDs:

    ``main``:
        The fieldset with Description and Testing Done.

    ``info``:
        The "Information" fieldset on the side.

    ``reviewers``:
        The "Reviewers" fieldset on the side.

    Any registered fieldset ID can be provided, whether from this extension
    or another.

    Field classes can only be added to a single fieldset.
    """

    def initialize(self, fieldset_id, fields):
        """Initialize the hook.

        This will register each of the provided field classes into the
        fieldset with the given ID.

        Args:
            fieldset_id (unicode):
                The ID of the
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`
                to register.

            fields (list of type):
                The list of fields to register into the fieldset. Each must be
                a subclass of
                :py:class:`~reviewboard.reviews.fields.BaseReviewRequestField`.
        """
        self.fieldset_id = fieldset_id
        self.fields = fields

        fieldset = get_review_request_fieldset(fieldset_id)
        assert fieldset is not None

        for field_cls in fields:
            fieldset.add_field(field_cls)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the field classes from the fieldset.
        """
        fieldset = get_review_request_fieldset(self.fieldset_id)
        assert fieldset is not None

        for field_cls in self.fields:
            fieldset.remove_field(field_cls)
