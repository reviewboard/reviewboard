from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.reviews.errors import PublishError
from reviewboard.reviews.models import Review
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import PUBLISH_ERROR
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource
from reviewboard.webapi.resources.user import UserResource


class ReviewReplyResource(BaseReviewResource):
    """Provides information on a reply to a review.

    A reply is much like a review, but is always tied to exactly one
    parent review. Every comment associated with a reply is also tied to
    a parent comment.
    """
    name = 'reply'
    name_plural = 'replies'
    policy_id = 'review_reply'
    fields = {
        'body_bottom': {
            'type': six.text_type,
            'description': 'The response to the review content below '
                           'the comments.',
            'supports_text_types': True,
        },
        'body_bottom_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           'body_bottom field.',
            'added_in': '2.0.12',
        },
        'body_top': {
            'type': six.text_type,
            'description': 'The response to the review content above '
                           'the comments.',
            'supports_text_types': True,
        },
        'body_top_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           'body_top field.',
            'added_in': '2.0.12',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the reply. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
        'id': {
            'type': int,
            'description': 'The numeric ID of the reply.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the reply is currently '
                           'visible to other users.',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'Formerly responsible for indicating the text '
                           'type for text fields. Replaced by '
                           'body_top_text_type and body_bottom_text_type '
                           'in 2.0.12.',
            'added_in': '2.0',
            'deprecated_in': '2.0.12',
        },
        'timestamp': {
            'type': six.text_type,
            'description': 'The date and time that the reply was posted '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': UserResource,
            'description': 'The user who wrote the reply.',
        },
    }

    item_child_resources = [
        resources.review_reply_diff_comment,
        resources.review_reply_screenshot_comment,
        resources.review_reply_file_attachment_comment,
    ]

    list_child_resources = [
        resources.review_reply_draft,
    ]

    uri_object_key = 'reply_id'
    model_parent_key = 'base_reply_to'

    mimetype_list_resource_name = 'review-replies'
    mimetype_item_resource_name = 'review-reply'

    CREATE_UPDATE_OPTIONAL_FIELDS = {
        'body_top': {
            'type': six.text_type,
            'description': 'The response to the review content above '
                           'the comments.',
            'supports_text_types': True,
        },
        'body_top_text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the body_top '
                           'field.',
            'added_in': '2.0.12',
        },
        'body_bottom': {
            'type': six.text_type,
            'description': 'The response to the review content below '
                           'the comments.',
            'supports_text_types': True,
        },
        'body_bottom_text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the body_bottom '
                           'field.',
            'added_in': '2.0.12',
        },
        'force_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
            'added_in': '2.0.9',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not to make the reply public. '
                           'If a reply is public, it cannot be made '
                           'private again.',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The mode for the body_top and body_bottom '
                           'text fields.\n'
                           '\n'
                           'This is deprecated. Please use '
                           'body_top_text_type and '
                           'body_bottom_text_type instead.',
            'added_in': '2.0',
            'deprecated_in': '2.0.12',
        },
        'trivial': {
            'type': bool,
            'description': 'If true, the review does not send '
                           'an email.',
            'added_in': '2.5',
        },
    }

    def get_base_reply_to_field(self, review_id, *args, **kwargs):
        return {
            'base_reply_to': Review.objects.get(pk=review_id),
        }

    def serialize_body_top_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_body_bottom_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=CREATE_UPDATE_OPTIONAL_FIELDS,
        allow_unknown=True
    )
    def create(self, request, *args, **kwargs):
        """Creates a reply to a review.

        The new reply will start off as private. Only the author of the
        reply (the user who is logged in and issuing this API call) will
        be able to see and interact with the reply.

        Initial data for the reply can be provided by passing data for
        any number of the fields. If nothing is provided, the reply will
        start off as blank.

        If the user submitting this reply already has a pending draft reply
        on this review, then this will update the existing draft and
        return :http:`303`. Otherwise, this will create a new draft and
        return :http:`201`. Either way, this request will return without
        a payload and with a ``Location`` header pointing to the location of
        the new draft reply.

        Extra data can be stored on the reply for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can
        be any valid strings. Passing a blank ``value`` will remove the key.
        The ``extra_data.`` prefix is required.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        reply, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            base_reply_to=review)

        if is_new:
            status_code = 201  # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303  # See Other

        result = self._update_reply(request, reply, *args, **kwargs)

        if not isinstance(result, tuple) or result[0] != 200:
            return result
        else:
            return status_code, result[1], {
                'Location': self.get_href(reply, request, *args, **kwargs),
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=CREATE_UPDATE_OPTIONAL_FIELDS,
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply.

        This updates the fields of a draft reply. Published replies cannot
        be updated.

        Only the owner of a reply can make changes. One or more fields can
        be updated at once.

        The only special field is ``public``, which, if set to true, will
        publish the reply. The reply will then be made publicly visible. Once
        public, the reply cannot be modified or made private again.

        Extra data can be stored on the reply for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can
        be any valid strings. Passing a blank ``value`` will remove the key.
        The ``extra_data.`` prefix is required.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            resources.review.get_object(request, *args, **kwargs)
            reply = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self._update_reply(request, reply, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(BaseReviewResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of all public replies on a review."""
        pass

    @webapi_check_local_site
    @augment_method_from(BaseReviewResource)
    def get(self, *args, **kwargs):
        """Returns information on a particular reply.

        If the reply is not public, then the client's logged in user
        must either be the owner of the reply. Otherwise, an error will
        be returned.
        """
        pass

    def _update_reply(self, request, reply, public=None, trivial=False,
                      extra_fields={}, *args, **kwargs):
        """Common function to update fields on a draft reply."""
        if not self.has_modify_permissions(request, reply):
            # Can't modify published replies or those not belonging
            # to the user.
            return self.get_no_access_error(request)

        for field in ('body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                if value == '':
                    reply_to = None
                else:
                    reply_to = reply.base_reply_to

                setattr(reply, '%s_reply_to' % field, reply_to)

        self.set_text_fields(reply, 'body_top', **kwargs)
        self.set_text_fields(reply, 'body_bottom', **kwargs)

        self.import_extra_data(reply, reply.extra_data, extra_fields)

        if public:
            try:
                reply.publish(user=request.user, trivial=trivial)
            except PublishError as e:
                return PUBLISH_ERROR.with_message(six.text_type(e))

        else:
            reply.save()

        return 200, {
            self.item_result_key: reply,
        }, {
            'Last-Modified': self.get_last_modified(request, reply),
        }


review_reply_resource = ReviewReplyResource()
