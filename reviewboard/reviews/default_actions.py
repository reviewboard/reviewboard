from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from reviewboard.reviews.actions import (BaseReviewRequestAction,
                                         BaseReviewRequestMenuAction)
from reviewboard.reviews.features import general_comments_feature
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.urls import diffviewer_url_names


class CloseMenuAction(BaseReviewRequestMenuAction):
    """A menu action for closing the corresponding review request."""

    action_id = 'close-review-request-action'
    label = _('Close')

    def should_render(self, context):
        review_request = context['review_request']

        return (review_request.status == ReviewRequest.PENDING_REVIEW and
                (context['request'].user.pk == review_request.submitter_id or
                 (context['perms']['reviews']['can_change_status'] and
                  review_request.public)))


class SubmitAction(BaseReviewRequestAction):
    """An action for submitting the review request."""

    action_id = 'submit-review-request-action'
    label = _('Submitted')

    def should_render(self, context):
        return context['review_request'].public


class DiscardAction(BaseReviewRequestAction):
    """An action for discarding the review request."""

    action_id = 'discard-review-request-action'
    label = _('Discarded')


class DeleteAction(BaseReviewRequestAction):
    """An action for permanently deleting the review request."""

    action_id = 'delete-review-request-action'
    label = _('Delete Permanently')

    def should_render(self, context):
        return context['perms']['reviews']['delete_reviewrequest']


class UpdateMenuAction(BaseReviewRequestMenuAction):
    """A menu action for updating the corresponding review request."""

    action_id = 'update-review-request-action'
    label = _('Update')

    def should_render(self, context):
        review_request = context['review_request']

        return (review_request.status == ReviewRequest.PENDING_REVIEW and
                (context['request'].user.pk == review_request.submitter_id or
                 context['perms']['reviews']['can_edit_reviewrequest']))


class UploadDiffAction(BaseReviewRequestAction):
    """An action for updating/uploading a diff for the review request."""

    action_id = 'upload-diff-action'

    def get_label(self, context):
        """Return this action's label.

        The label will change depending on whether or not the corresponding
        review request already has a diff.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            unicode: The label that displays this action to the user.
        """
        review_request = context['review_request']
        draft = review_request.get_draft(context['request'].user)

        if (draft and draft.diffset) or review_request.get_diffsets():
            return _('Update Diff')

        return _('Upload Diff')

    def should_render(self, context):
        """Return whether or not this action should render.

        If the corresponding review request has a repository, then an upload
        diff form exists, so we should render this UploadDiffAction.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template
                just before this action is to be rendered.

        Returns:
            bool: Determines if this action should render.
        """
        return context['review_request'].repository_id is not None


class UploadFileAction(BaseReviewRequestAction):
    """An action for uploading a file for the review request."""

    action_id = 'upload-file-action'
    label = _('Add File')


class DownloadDiffAction(BaseReviewRequestAction):
    """An action for downloading a diff from the review request."""

    action_id = 'download-diff-action'
    label = _('Download Diff')

    def get_url(self, context):
        """Return this action's URL.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            unicode: The URL to invoke if this action is clicked.
        """
        match = context['request'].resolver_match

        # We want to use a relative URL in the diff viewer as we will not be
        # re-rendering the page when switching between revisions.
        if match.url_name in diffviewer_url_names:
            return 'raw/'

        return local_site_reverse('raw-diff', context['request'], kwargs={
            'review_request_id': context['review_request'].display_id,
        })

    def get_hidden(self, context):
        """Return whether this action should be initially hidden to the user.

        Args:
            context (django.template.Context):
                The collection of key-value pairs from the template.

        Returns:
            bool: Whether this action should be initially hidden to the user.
        """
        match = context['request'].resolver_match

        if match.url_name in diffviewer_url_names:
            return match.url_name == 'view-interdiff'

        return super(DownloadDiffAction, self).get_hidden(context)

    def should_render(self, context):
        """Return whether or not this action should render.

        Args:
            context (django.template.Context):
                The collection of key-value pairs available in the template
                just before this action is to be rendered.

        Returns:
            bool: Determines if this action should render.
        """
        review_request = context['review_request']
        request = context['request']
        match = request.resolver_match

        # If we're on a diff viewer page, then this DownloadDiffAction should
        # initially be rendered, but possibly hidden.
        if match.url_name in diffviewer_url_names:
            return True

        return review_request.repository_id is not None


class EditReviewAction(BaseReviewRequestAction):
    """An action for editing a review intended for the review request."""

    action_id = 'review-action'
    label = _('Review')

    def should_render(self, context):
        return context['request'].user.is_authenticated()


class AddGeneralCommentAction(BaseReviewRequestAction):
    """An action for adding a new general comment to a review."""

    action_id = 'general-comment-action'
    label = _('Add General Comment')

    def should_render(self, context):
        request = context['request']
        return (request.user.is_authenticated() and
                general_comments_feature.is_enabled(request=request))


class ShipItAction(BaseReviewRequestAction):
    """An action for quickly approving the review request without comments."""

    action_id = 'ship-it-action'
    label = _('Ship It!')

    def should_render(self, context):
        return context['request'].user.is_authenticated()


def get_default_actions():
    """Return a copy of all the default actions.

    Returns:
        list of BaseReviewRequestAction: A copy of all the default actions.
    """
    return [
        CloseMenuAction([
            SubmitAction(),
            DiscardAction(),
            DeleteAction(),
        ]),
        UpdateMenuAction([
            UploadDiffAction(),
            UploadFileAction(),
        ]),
        DownloadDiffAction(),
        EditReviewAction(),
        AddGeneralCommentAction(),
        ShipItAction(),
    ]
