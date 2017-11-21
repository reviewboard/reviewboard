"""Feature definitions for reviews."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from djblets.features import Feature, FeatureLevel


class ClassBasedActionsFeature(Feature):
    """A feature for class-based actions.

    With this enabled, extensions may use the new class-based action classes
    instead of the old-style dict actions.
    """

    feature_id = 'reviews.class_based_actions'
    name = _('Class-Based Actions')
    level = FeatureLevel.UNAVAILABLE
    summary = _('Allow using class-based actions with extension hooks.')


class GeneralCommentsFeature(Feature):
    """A feature for general comments.

    General comments allow comments to be created directly on a review request
    without accompanying file attachment or diff. These can be used to raise
    issues with the review request itself, such as its summary or description,
    or general implementation issues.
    """

    feature_id = 'reviews.general_comments'
    name = _('General Comments')
    level = FeatureLevel.STABLE
    summary = _('Allow comments on review requests without an associated file '
                'attachment or diff.')


class IssueVerificationFeature(Feature):
    """A feature for issue verification.

    Issue verification allows reviewers to mark that an issue requires
    verification before closing. In this case, the author of the change will be
    able to mark the issue as "Fixed", but then the original author of the
    comment will need to verify it before the issue is closed.
    """

    feature_id = 'reviews.issue_verification'
    name = _('Issue Verification')
    level = FeatureLevel.STABLE
    summary = _('Allow comment authors to require that issues be verified by '
                'them before being closed')


class StatusUpdatesFeature(Feature):
    """A feature for status updates.

    A status update is a way for third-party tools to provide feedback on a
    review request. In the past, this was done just as a normal review. Status
    updates allow those tools (via some integration like Review Bot) to mark
    their state (such as pending, success, failure, or error) and then
    associate that with a review.
    """

    feature_id = 'reviews.status_updates'
    name = _('Status Updates')
    level = FeatureLevel.STABLE
    summary = _('A way for external tools to do checks on a review request '
                'and report the results of those checks.')


class_based_actions_feature = ClassBasedActionsFeature()
general_comments_feature = GeneralCommentsFeature()
issue_verification_feature = IssueVerificationFeature()
status_updates_feature = StatusUpdatesFeature()
