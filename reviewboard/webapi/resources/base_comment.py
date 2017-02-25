from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.utils import six
from django.utils.formats import localize
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.reviews.models import BaseComment
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources


class BaseCommentResource(MarkdownFieldsMixin, WebAPIResource):
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
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The mode for the comment text field.',
        },
        'timestamp': {
            'type': six.text_type,
            'description': 'The date and time that the comment was made '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.user.UserResource',
            'description': 'The user who made the comment.',
        },
    }

    # Common field definitions for create/update requests
    _COMMON_REQUIRED_CREATE_FIELDS = {
        'text': {
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
        },
    }

    _COMMON_OPTIONAL_CREATE_FIELDS = {
        'force_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The content type for the comment text field. '
                           'The default is ``plain``.',
        },
    }

    _COMMON_OPTIONAL_UPDATE_FIELDS = {
        'force_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
        },
        'text': {
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The new content type for the comment text field. '
                           'The default is to leave the type unchanged.',
        },
    }

    # Field definitions for top-level comment create/update requests
    REQUIRED_CREATE_FIELDS = _COMMON_REQUIRED_CREATE_FIELDS

    OPTIONAL_CREATE_FIELDS = dict({
        'issue_opened': {
            'type': bool,
            'description': 'Whether the comment opens an issue.',
        },
    }, **_COMMON_OPTIONAL_CREATE_FIELDS)

    OPTIONAL_UPDATE_FIELDS = dict({
        'issue_opened': {
            'type': bool,
            'description': 'Whether or not the comment opens an issue.',
        },
        'issue_status': {
            'type': ('dropped', 'open', 'resolved'),
            'description': 'The status of an open issue.',
        },
    }, **_COMMON_OPTIONAL_UPDATE_FIELDS)

    # Field definitions for comment reply create/update requests
    REPLY_REQUIRED_CREATE_FIELDS = dict({
        'reply_to_id': {
            'type': int,
            'description': 'The ID of the comment being replied to.',
        },
    }, **_COMMON_REQUIRED_CREATE_FIELDS)

    REPLY_OPTIONAL_CREATE_FIELDS = _COMMON_OPTIONAL_CREATE_FIELDS
    REPLY_OPTIONAL_UPDATE_FIELDS = _COMMON_OPTIONAL_UPDATE_FIELDS

    def serialize_issue_status_field(self, obj, **kwargs):
        return BaseComment.issue_status_to_string(obj.issue_status)

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def create_comment(self, review, fields, text, issue_opened=False,
                       text_type=False, extra_fields={}, **kwargs):
        comment_kwargs = {
            'issue_opened': bool(issue_opened),
            'rich_text': text_type == self.TEXT_TYPE_MARKDOWN,
            'text': text.strip(),
        }

        for field in fields:
            comment_kwargs[field] = kwargs.get(field)

        new_comment = self.model(**comment_kwargs)
        self.import_extra_data(new_comment, new_comment.extra_data,
                               extra_fields)

        if issue_opened:
            new_comment.issue_status = BaseComment.OPEN
        else:
            new_comment.issue_status = None

        new_comment.save()

        return new_comment

    def update_comment(self, comment, update_fields=(), extra_fields={},
                       is_reply=False,
                       **kwargs):
        if not is_reply:
            # If we've updated the comment from having no issue opened,
            # to having an issue opened, we need to set the issue status
            # to OPEN.
            if not comment.issue_opened and kwargs.get('issue_opened', False):
                comment.issue_status = BaseComment.OPEN

            # If we've updated the comment from having an issue opened to
            # having no issue opened, set the issue status back to null.
            if comment.issue_opened and not kwargs.get('issue_opened', True):
                comment.issue_status = None

        for field in ('issue_opened',) + update_fields:
            value = kwargs.get(field, None)

            if value is not None:
                if isinstance(value, six.string_types):
                    value = value.strip()

                setattr(comment, field, value)

        self.set_text_fields(comment, 'text', **kwargs)

        if not is_reply:
            self.import_extra_data(comment, comment.extra_data, extra_fields)

        comment.save()

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

        comment._review_request = review_request

        # We can only update the status of the issue
        issue_status = \
            BaseComment.issue_string_to_status(kwargs.get('issue_status'))
        comment.issue_status = issue_status
        comment.save(update_fields=['issue_status'])

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
