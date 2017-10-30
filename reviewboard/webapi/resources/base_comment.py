from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Q
from django.utils import six
from djblets.webapi.errors import DOES_NOT_EXIST, WebAPIError

from reviewboard.reviews.models import BaseComment
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources


class BaseCommentResource(MarkdownFieldsMixin, WebAPIResource):
    """Base class for comment resources.

    Provides common fields and functionality for all comment resources.
    """
    added_in = '1.6'

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
            'added_in': '2.0',
        },
        'issue_opened': {
            'type': bool,
            'description': 'Whether or not a comment opens an issue.',
        },
        'issue_status': {
            'type': tuple(BaseComment.ISSUE_STRING_TO_STATUS.keys()),
            'description': 'The status of an issue.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the comment is part of a public '
                           'review.',
            'added_in': '2.0',
        },
        'text': {
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
            'added_in': '2.0',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The mode for the comment text field.',
            'added_in': '2.0',
        },
        'timestamp': {
            'type': six.text_type,
            'description': 'The date and time that the comment was made '
                           '(in YYYY-MM-DD HH:MM:SS format).',
            'added_in': '2.0',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.user.UserResource',
            'description': 'The user who made the comment.',
            'added_in': '2.0',
        },
    }

    # Common field definitions for create/update requests
    _COMMON_REQUIRED_CREATE_FIELDS = {
        'text': {
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
            'added_in': '2.0',
        },
    }

    _COMMON_OPTIONAL_CREATE_FIELDS = {
        'force_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
            'added_in': '2.0.9',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The content type for the comment text field. '
                           'The default is ``plain``.',
            'added_in': '2.0',
        },
    }

    _COMMON_OPTIONAL_UPDATE_FIELDS = {
        'force_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
            'added_in': '2.0.9',
        },
        'text': {
            'type': six.text_type,
            'description': 'The comment text.',
            'supports_text_types': True,
            'added_in': '2.0',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The new content type for the comment text field. '
                           'The default is to leave the type unchanged.',
            'added_in': '2.0',
        },
    }

    # Field definitions for top-level comment create/update requests
    REQUIRED_CREATE_FIELDS = _COMMON_REQUIRED_CREATE_FIELDS

    OPTIONAL_CREATE_FIELDS = dict({
        'issue_opened': {
            'type': bool,
            'description': 'Whether the comment opens an issue.',
            'added_in': '2.0',
        },
    }, **_COMMON_OPTIONAL_CREATE_FIELDS)

    OPTIONAL_UPDATE_FIELDS = dict({
        'issue_opened': {
            'type': bool,
            'description': 'Whether or not the comment opens an issue.',
            'added_in': '2.0',
        },
        'issue_status': {
            'type': tuple(BaseComment.ISSUE_STRING_TO_STATUS.keys()),
            'description': 'The status of an open issue.',
            'added_in': '2.0',
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

    def create_comment(self,
                       review,
                       fields,
                       text,
                       comments_m2m,
                       issue_opened=False,
                       text_type=MarkdownFieldsMixin.TEXT_TYPE_PLAIN,
                       extra_fields={},
                       **kwargs):
        """Create a comment based on the requested data.

        This will construct a comment of the type represented by the resource,
        setting the issue states, text, extra_data, and any additional fields
        provided by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review owning the comment.

            fields (list of unicode):
                The model fields that can be set through the API.

            text (unicode):
                The comment text.

            comments_m2m (django.db.models.ManyToManyField):
                The review's comments relation, where the new comment will
                be added.

            issue_opened (bool, optional):
                Whether this comment opens an issue.

            text_type (unicode, optional):
                The text type for the comment. This defaults to plain text.

            extra_fields (dict, optional):
                Extra fields from the request not otherwise handled by the
                API resource. Any ``extra_data`` modifications from this will
                be applied to the comment.

            **kwargs (dict):
                Keyword arguments representing additional fields handled by
                the API resource. Any that are also listed in ``fields`` will
                be set on the model.

        Returns:
            tuple or djblets.webapi.errors.WebAPIError:
            Either a successful payload containing the comment, or an error
            payload.
        """
        comment_kwargs = {
            'issue_opened': bool(issue_opened),
            'rich_text': text_type == self.TEXT_TYPE_MARKDOWN,
            'text': text.strip(),
        }

        for field in fields:
            comment_kwargs[field] = kwargs.get(field)

        new_comment = self.model(**comment_kwargs)

        try:
            self.import_extra_data(new_comment, new_comment.extra_data,
                                   extra_fields)
        except ImportExtraDataError as e:
            return e.error_payload

        if issue_opened:
            new_comment.issue_status = BaseComment.OPEN
        else:
            new_comment.issue_status = None

        new_comment.save()
        comments_m2m.add(new_comment)

        return 201, {
            self.item_result_key: new_comment,
        }

    def create_or_update_comment_reply(self, request, comment, reply,
                                       comments_m2m, default_attrs={},
                                       *args, **kwargs):
        """Create a reply to a comment based on the requested data.

        If there's an existing reply to a comment, that one will be updated
        instead.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            comment (reviewboard.reviews.models.base_commet.BaseComment):
                The comment being replied to.

            reply (reviewboard.reviews.models.review.Review):
                The review reply owning the comment.

            comments_m2m (django.db.models.ManyToManyField):
                The reply's comments relation, where the new comment will
                be added.

            default_attrs (dict, optional):
                Default attributes to add to the new comment reply, if an
                existing one does not exist.

            *args (tuple):
                Positional arguments from the caller.

            **kwargs (dict):
                Keyword arguments from the caller.

        Returns:
            tuple or djblets.webapi.errors.WebAPIError:
            Either a successful payload containing the comment, or an error
            payload.
        """
        q = self._get_queryset(request, *args, **kwargs)
        q = q.filter(Q(reply_to=comment) & Q(review=reply))

        try:
            new_comment = q.get()

            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            is_new = False
        except self.model.DoesNotExist:
            new_comment = self.model(reply_to=comment, **default_attrs)
            is_new = True

        rsp = self.update_comment(request=request,
                                  review=reply,
                                  comment=new_comment,
                                  is_reply=True,
                                  **kwargs)

        if isinstance(rsp, WebAPIError):
            return rsp

        data = rsp[1]

        if is_new:
            comments_m2m.add(new_comment)
            reply.save()

            return 201, data
        else:
            return 303, data, {
                'Location': self.get_href(new_comment, request, *args,
                                          **kwargs)
            }

    def update_comment(self, request, review, comment, update_fields=(),
                       extra_fields={}, is_reply=False, **kwargs):
        """Update an existing comment based on the requested data.

        This will modify a comment, setting new fields requested by the caller.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            review (reviewboard.reviews.models.review.Review):
                The review owning the comment.

            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to update.

            update_fields (list of unicode, optional):
                The model fields that can be updated through the API.

            extra_fields (dict, optional):
                Extra fields from the request not otherwise handled by the
                API resource. Any ``extra_data`` modifications from this will
                be applied to the comment.

            is_reply (bool, optional):
                Whether this is a reply to another comment.

            **kwargs (dict):
                Keyword arguments representing additional fields handled by
                the API resource. Any that are also listed in ``fields`` will
                be set on the model.

        Returns:
            tuple or djblets.webapi.errors.WebAPIError:
            Either a successful payload containing the comment, or an error
            payload.
        """
        if is_reply:
            if not resources.review_reply.has_modify_permissions(request,
                                                                 review):
                return self.get_no_access_error(request)
        else:
            # Determine whether or not we're updating the issue status.
            if self.should_update_issue_status(comment, **kwargs):
                return self.update_issue_status(request, self, **kwargs)

            if not resources.review.has_modify_permissions(request, review):
                return self.get_no_access_error(request)

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
            try:
                self.import_extra_data(comment, comment.extra_data,
                                       extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

        comment.save()

        return 200, {
            self.item_result_key: comment,
        }

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
            return self.get_no_access_error(request)

        # We can only update the status of an issue if an issue has been
        # opened
        if not comment.issue_opened:
            raise PermissionDenied

        comment._review_request = review_request
        issue_status = \
            BaseComment.issue_string_to_status(kwargs.get('issue_status'))

        # If the issue requires verification, ensure that only people who are
        # authorized can close it.
        if (comment.require_verification and
            issue_status in (BaseComment.RESOLVED, BaseComment.DROPPED) and
            comment.issue_status in (BaseComment.OPEN,
                                     BaseComment.VERIFYING_RESOLVED,
                                     BaseComment.VERIFYING_DROPPED) and
            not comment.can_verify_issue_status(request.user)):
            return self.get_no_access_error(request)

        # We can only update the status of the issue
        comment.issue_status = issue_status
        comment.save(update_fields=['issue_status'])

        last_activity_time, updated_object = review_request.get_last_activity()

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
