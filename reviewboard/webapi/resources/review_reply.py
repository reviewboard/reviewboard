from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.compat import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.reviews.markdown_utils import markdown_set_field_escaped
from reviewboard.reviews.models import Review
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource
from reviewboard.webapi.resources.user import UserResource


class ReviewReplyResource(BaseReviewResource):
    """Provides information on a reply to a review.

    A reply is much like a review, but is always tied to exactly one
    parent review. Every comment associated with a reply is also tied to
    a parent comment.

    If the ``rich_text`` field is set to true, then ``body_top`` and
    ``body_bottom`` should be interpreted by the client as Markdown text.
    """
    name = 'reply'
    name_plural = 'replies'
    fields = {
        'body_bottom': {
            'type': six.text_type,
            'description': 'The response to the review content below '
                           'the comments.',
        },
        'body_top': {
            'type': six.text_type,
            'description': 'The response to the review content above '
                           'the comments.',
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
        'rich_text': {
            'type': bool,
            'description': 'Whether or not the review body_top and '
                           'body_bottom fields are in rich-text (Markdown) '
                           'format.',
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

    def get_base_reply_to_field(self, review_id, *args, **kwargs):
        return {
            'base_reply_to': Review.objects.get(pk=review_id),
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'body_top': {
                'type': six.text_type,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': six.text_type,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
            },
            'rich_text': {
                'type': bool,
                'description': 'Whether the body_top and body_bottom text '
                               'is in rich-text (Markdown) format. '
                               'The default is false.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a reply to a review.

        The new reply will start off as private. Only the author of the
        reply (the user who is logged in and issuing this API call) will
        be able to see and interact with the reply.

        Initial data for the reply can be provided by passing data for
        any number of the fields. If nothing is provided, the reply will
        start off as blank.

        If ``rich_text`` is provided and changed to true, then the ``body_top``
        and ``body_bottom`` are expected to be in valid Markdown format.

        If the user submitting this reply already has a pending draft reply
        on this review, then this will update the existing draft and
        return :http:`303`. Otherwise, this will create a new draft and
        return :http:`201`. Either way, this request will return without
        a payload and with a ``Location`` header pointing to the location of
        the new draft reply.
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
        optional={
            'body_top': {
                'type': six.text_type,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': six.text_type,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
            },
            'rich_text': {
                'type': bool,
                'description': 'Whether the body_top and body_bottom text '
                               'is in rich-text (Markdown) format. '
                               'The default is false.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply.

        This updates the fields of a draft reply. Published replies cannot
        be updated.

        Only the owner of a reply can make changes. One or more fields can
        be updated at once.

        If ``rich_text`` is provided and changed to true, then the ``body_top``
        and ``body_bottom`` fields will be set to be interpreted as Markdown.
        When setting to true and not specifying one or both of those fields,
        the existing text will be escaped so as not to be unintentionally
        interpreted as Markdown.

        If ``rich_text`` is changed to false, and one or both of those fields
        are not provided, the existing text will be unescaped.

        The only special field is ``public``, which, if set to true, will
        publish the reply. The reply will then be made publicly visible. Once
        public, the reply cannot be modified or made private again.
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

    def _update_reply(self, request, reply, public=None, *args, **kwargs):
        """Common function to update fields on a draft reply."""
        if not self.has_modify_permissions(request, reply):
            # Can't modify published replies or those not belonging
            # to the user.
            return self._no_access_error(request.user)

        old_rich_text = reply.rich_text

        for field in ('body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(reply, field, value.strip())

                if value == '':
                    reply_to = None
                else:
                    reply_to = reply.base_reply_to

                setattr(reply, '%s_reply_to' % field, reply_to)

        if 'rich_text' in kwargs:
            reply.rich_text = kwargs['rich_text']

        self.normalize_markdown_fields(reply, ['body_top', 'body_bottom'],
                                       old_rich_text, **kwargs)

        if public:
            reply.publish(user=request.user)
        else:
            reply.save()

        return 200, {
            self.item_result_key: reply,
        }, {
            'Last-Modified': self.get_last_modified(request, reply),
        }


review_reply_resource = ReviewReplyResource()
