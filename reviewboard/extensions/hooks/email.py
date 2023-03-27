"""Extension hooks for customizing email notifications."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.notifications.email import (register_email_hook,
                                             unregister_email_hook)
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)


class EmailHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for changing the recipients of e-mails.

    Extensions can use this hook to change the contents of the To and CC fields
    of e-mails. This should be subclassed in an extension to provide the
    desired behaviour. This class is a base class for more specialized
    extension hooks. If modifying only one type of e-mail's fields is desired,
    one of the following classes should be subclassed instead.

    * :py:class:`ReviewPublishedEmailHook`
    * :py:class:`ReviewReplyPublishedEmailHook`
    * :py:class:`ReviewRequestPublishedEmailHook`
    * :py:class:`ReviewRequestClosedEmailHook`

    However, if more specialized behaviour is desired, this class can be
    subclassed.
    """

    def initialize(self, signals):
        """Initialize the hook.

        Args:
            signals (list):
                A list of :py:class:`Signals <django.dispatch.Signal>` that,
                when triggered, will cause e-mails to be sent. Valid signals
                are:

                * :py:data:`~reviewboard.reviews.signals.review_request_published`
                * :py:data:`~reviewboard.reviews.signals.review_request_closed`
                * :py:data:`~reviewboard.reviews.signals.review_published`
                * :py:data:`~reviewboard.reviews.signals.reply_published`
        """
        self.signals = signals

        for signal in signals:
            register_email_hook(signal, self)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the e-mail handlers.
        """
        for signal in self.signals:
            unregister_email_hook(signal, self)

    def get_to_field(self, to_field, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            kwargs (dict):
                Additional keyword arguments that will be passed based on the
                type of e-mail being sent.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            cc_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail.

            kwargs (dict):
                Additional keyword arguments that will be passed based on the
                type of e-mail being sent.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewPublishedEmailHook, self).initialize(
            signals=[review_published])

    def get_to_field(self, to_field, review, user, review_request,
                     to_owner_only, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            review (reviewboard.reviews.models.Review):
                The review that was published.

            user (django.contrib.auth.models.User):
                The user who published the review.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            to_owner_only (bool):
                Whether or not the review was marked as being targeted at only
                the submitter.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review, user, review_request,
                     to_owner_only, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            cc_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail.

            review (reviewboard.reviews.models.Review):
                The review that was published.

            user (django.contrib.auth.models.User):
                The user who published the review.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            to_owner_only (bool):
                Whether or not the review was marked as being targeted at only
                the submitter.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewReplyPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review reply publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewReplyPublishedEmailHook, self).initialize(
            signals=[reply_published])

    def get_to_field(self, to_field, reply, user, review_request, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            reply (reviewboard.reviews.models.Review):
                The review reply that was published.

            user (django.contrib.auth.models.User):
                The user who published the review reply.

            review (reviewboard.reviews.model.Review):
                The review the reply is in reply to.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, reply, user, review_request, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive a carbon copy of the e-mail

            reply (reviewboard.reviews.models.Review):
                The review reply that was published.

            user (django.contrib.auth.models.User):
                The user who published the reply.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was reviewed.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestClosedEmailHook(EmailHook):
    """A hook for changing the recipients of review request closing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook."""
        super(ReviewRequestClosedEmailHook, self).initialize(
            signals=[review_request_closed])

    def get_to_field(self, to_field, review_request, user, close_type,
                     **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>`
                that will receive the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who closed the review request.

            close_type (unicode):
                How the review request was closed. This is one of
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED`
                or
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user, close_type,
                     **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive a carbon copy of the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who closed the review request.

            close_type (unicode):
                How the review request was closed. This is one of
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED`
                or
                :py:attr:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field


class ReviewRequestPublishedEmailHook(EmailHook):
    """A hook for changing the recipients of review request publishing e-mails.

    This hook must be subclassed. The caller is expected to override
    :py:meth:`get_to_field` and/or :py:meth:`get_cc_field`.
    """

    def initialize(self):
        """Initialize the hook. """
        super(ReviewRequestPublishedEmailHook, self).initialize(
            signals=[review_request_published])

    def get_to_field(self, to_field, review_request, user, **kwargs):
        """Return the To field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who published the review request.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired To field.
        """
        return to_field

    def get_cc_field(self, cc_field, review_request, user, **kwargs):
        """Return the CC field for the e-mail.

        Args:
            to_field (set):
                A set of :py:class:`Users <django.contrib.auth.models.User>`
                and :py:class:`Groups <reviewboard.reviews.models.Group>` that
                will receive a carbon copy of the e-mail.

            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that was published.

            user (django.contrib.auth.models.User):
                The user who published the review request.

            **kwargs (dict):
                Additional keyword arguments, since the signature may change in
                the future.

        Returns:
            set: The desired CC field.
        """
        return cc_field
