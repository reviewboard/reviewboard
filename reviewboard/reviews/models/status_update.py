"""Definitions for the StatusUpdate model."""

from __future__ import unicode_literals

import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.models.review import Review
from reviewboard.reviews.models.review_request import ReviewRequest


class StatusUpdate(models.Model):
    """A status update from a third-party service or extension.

    This status model allows external services (such as continuous integration
    services, Review Bot, etc.) to provide an update on their status. An
    example of this would be a CI tool which does experimental builds of
    changes. While the build is running, that tool would set its status to
    pending, and when it was done, would set it to one of the done states,
    and potentially associate it with a review containing issues.
    """

    #: The pending state.
    PENDING = 'P'

    #: The completed successfully state.
    DONE_SUCCESS = 'S'

    #: The completed with reported failures state.
    DONE_FAILURE = 'F'

    #: The error state.
    ERROR = 'E'

    #: Timeout state.
    TIMEOUT = 'T'

    STATUSES = (
        (PENDING, _('Pending')),
        (DONE_SUCCESS, _('Done (Success)')),
        (DONE_FAILURE, _('Done (Failure)')),
        (ERROR, _('Error')),
        (TIMEOUT, _('Timed Out')),
    )

    #: An identifier for the service posting this status update.
    #:
    #: This ID is self-assigned, and just needs to be unique to that service.
    #: Possible values can be an extension ID, webhook URL, or a script name.
    service_id = models.CharField(_('Service ID'), max_length=255)

    #: The user who created this status update.
    user = models.ForeignKey(
        User,
        related_name='status_updates',
        verbose_name=_('User'),
        blank=True,
        null=True)

    #: The timestamp of the status update.
    timestamp = models.DateTimeField(_('Timestamp'), auto_now=True)

    #: A user-visible short summary of the status update.
    #:
    #: This is typically the name of the integration or tool that was run.
    summary = models.CharField(_('Summary'), max_length=255)

    #: A user-visible description on the status update.
    #:
    #: This is shown in the UI adjacent to the summary. Typical results might
    #: be things like "running." or "failed.". This should include punctuation.
    description = models.CharField(_('Description'), max_length=255,
                                   blank=True)

    #: An optional link.
    #:
    #: This is used in case the tool has some external page, such as a build
    #: results page on a CI system.
    url = models.URLField(_('Link URL'), max_length=255, blank=True)

    #: Text for the link. If ``url`` is empty, this will not be used.
    url_text = models.CharField(_('Link text'), max_length=64, blank=True)

    #: The current state of this status update.
    #:
    #: This should be set to :py:attr:`PENDING` while the service is
    #: processing the update, and then to either :py:attr:`DONE_SUCCESS` or
    #: :py:attr:`DONE_FAILURE` once complete. If the service encountered some
    #: error which prevented completion, this should be set to
    #: :py:attr:`ERROR`.
    state = models.CharField(_('State'), max_length=1, choices=STATUSES)

    #: The review request that this status update is for.
    review_request = models.ForeignKey(
        ReviewRequest,
        related_name='status_updates',
        verbose_name=_('Review Request'))

    #: The change to the review request that this status update is for.
    #:
    #: If this is ``None``, this status update refers to the review request as
    #: a whole (for example, the initial diff that was posted).
    change_description = models.ForeignKey(
        ChangeDescription,
        related_name='status_updates',
        verbose_name=_('Change Description'),
        null=True,
        blank=True)

    #: An optional review created for this status update.
    #:
    #: This allows the third-party service to create comments and open issues.
    review = models.OneToOneField(
        Review,
        related_name='status_update',
        verbose_name=_('Review'),
        null=True,
        blank=True)

    #: Any extra data that the service wants to store for this status update.
    extra_data = JSONField(null=True)

    #: An (optional) timeout, in seconds. If this is non-None and the state has
    #: been ``PENDING`` for longer than this period (computed from the
    #: :py:attr:`timestamp` field), :py:attr:`effective_state` will be
    #: ``TIMEOUT``.
    timeout = models.IntegerField(null=True, blank=True)

    @staticmethod
    def state_to_string(state):
        """Return a string representation of a status update state.

        Args:
            state (unicode):
                A single-character string representing the state.

        Returns:
            unicode:
            A longer string representation of the state suitable for use in
            the API.
        """
        if state == StatusUpdate.PENDING:
            return 'pending'
        elif state == StatusUpdate.DONE_SUCCESS:
            return 'done-success'
        elif state == StatusUpdate.DONE_FAILURE:
            return 'done-failure'
        elif state == StatusUpdate.ERROR:
            return 'error'
        elif state == StatusUpdate.TIMEOUT:
            return 'timed-out'
        else:
            raise ValueError('Invalid state "%s"' % state)

    @staticmethod
    def string_to_state(state):
        """Return a status update state from an API string.

        Args:
            state (unicode):
                A string from the API representing the state.

        Returns:
            unicode:
            A single-character string representing the state, suitable for
            storage in the ``state`` field.
        """
        if state == 'pending':
            return StatusUpdate.PENDING
        elif state == 'done-success':
            return StatusUpdate.DONE_SUCCESS
        elif state == 'done-failure':
            return StatusUpdate.DONE_FAILURE
        elif state == 'error':
            return StatusUpdate.ERROR
        elif state == 'timed-out':
            return StatusUpdate.TIMEOUT
        else:
            raise ValueError('Invalid state string "%s"' % state)

    def is_mutable_by(self, user):
        """Return whether the user can modify this status update.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            True if the user can modify this status update.
        """
        return (self.user == user or
                user.has_perm('reviews.can_edit_status',
                              self.review_request.local_site))

    @property
    def effective_state(self):
        """The state of the status update, taking into account timeouts."""
        if self.state == self.PENDING and self.timeout is not None:
            timeout = self.timestamp + datetime.timedelta(seconds=self.timeout)

            if timezone.now() > timeout:
                return self.TIMEOUT

        return self.state

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_statusupdate'
        ordering = ['timestamp']
        get_latest_by = 'timestamp'
        verbose_name = _('Status Update')
        verbose_name_plural = _('Status Updates')
