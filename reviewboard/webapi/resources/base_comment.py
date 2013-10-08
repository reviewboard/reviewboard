from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils.formats import localize
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.reviews.models import BaseComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.resources import resources


class BaseCommentResource(WebAPIResource):
    """Base class for comment resources.

    Provides common fields and functionality for all comment resources.
    """
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the comment.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the comment. This depends '
                           'on what is being commented on, and may be '
                           'used in conjunction with an extension.',
        },
        'issue_opened': {
            'type': bool,
            'description': 'Whether or not a comment opens an issue.',
        },
        'issue_status': {
            'type': ('dropped', 'open', 'resolved'),
            'description': 'The status of an issue.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the comment is part of a public '
                           'review.',
        },
        'text': {
            'type': str,
            'description': 'The comment text.',
        },
        'timestamp': {
            'type': str,
            'description': 'The date and time that the comment was made '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.user.UserResource',
            'description': 'The user who made the comment.',
        },
    }
    last_modified_field = 'timestamp'

    def has_delete_permissions(self, request, comment, *args, **kwargs):
        review = comment.review.get()
        return not review.public and review.user == request.user

    def update_issue_status(self, request, comment_resource, *args, **kwargs):
        """Updates the issue status for a comment.

        Handles all of the logic for updating an issue status.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            comment = comment_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Check permissions to change the issue status
        if not comment.can_change_issue_status(request.user):
            return self._no_access_error(request.user)

        # We can only update the status of an issue if an issue has been
        # opened
        if not comment.issue_opened:
            raise PermissionDenied

        # We can only update the status of the issue
        issue_status = \
            BaseComment.issue_string_to_status(kwargs.get('issue_status'))
        comment.issue_status = issue_status
        comment.save()

        last_activity_time, updated_object = review_request.get_last_activity()
        comment.timestamp = localize(comment.timestamp)

        return 200, {
            comment_resource.item_result_key: comment,
            'last_activity_time': last_activity_time.isoformat(),
        }

    def should_update_issue_status(self, comment, issue_status=None,
                                   issue_opened=None, **kwargs):
        """Returns True if the comment should have its issue status updated.

        Determines if a comment should have its issue status updated based
        on the current state of the comment, the review, and the arguments
        passed in the request.
        """
        if not issue_status:
            return False

        issue_status = BaseComment.issue_string_to_status(issue_status)

        return (comment.review.get().public and
                (comment.issue_opened or issue_opened) and
                issue_status != comment.issue_status)

    def serialize_issue_status_field(self, obj, **kwargs):
        return BaseComment.issue_status_to_string(obj.issue_status)
