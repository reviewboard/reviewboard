from __future__ import unicode_literals

from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.fields import (ChoiceFieldType,
                                   DateTimeFieldType,
                                   DictFieldType,
                                   IntFieldType,
                                   StringFieldType)

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.fields import get_review_request_field
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources


class ChangeResource(MarkdownFieldsMixin, WebAPIResource):
    """Provides information on a change made to a public review request.

    A change includes, optionally, text entered by the user describing the
    change, and also includes a list of fields that were changed on the
    review request.

    The list of fields changed are in ``fields_changed``. The keys are the
    names of the fields, and the values are details on that particular
    change to the field.

    """
    added_in = '1.6'

    model = ChangeDescription
    name = 'change'
    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the change description.',
        },
        'fields_changed': {
            'type': DictFieldType,
            'description': """
                The fields that were changed. Each key is the name of a
                changed field, and each value is a dictionary of details on
                that change.

                For ``summary``, ``description``, ``testing_done`` and
                ``branch`` fields, the following detail keys will be
                available:

                * ``old``: The old value of the field.
                * ``new``: The new value of the field.

                For ``diff`` fields:

                * ``added``: The diff that was added.

                For ``bugs_closed`` fields:

                * ``old``: A list of old bugs.
                * ``new``: A list of new bugs.
                * ``removed``: A list of bugs that were removed, if any.
                * ``added``: A list of bugs that were added, if any.

                For ``file_attachments``, ``screenshots``, ``target_people``
                and ``target_groups`` fields:

                * ``old``: A list of old items.
                * ``new``: A list of new items.
                * ``removed``: A list of items that were removed, if any.
                * ``added``: A list of items that were added, if any.

                For ``screenshot_captions`` and ``file_captions`` fields:

                * ``old``: The old caption.
                * ``new``: The new caption.
                * ``screenshot``: The screenshot that was updated.
            """,
        },
        'text': {
            'type': StringFieldType,
            'description': 'The description of the change written by the '
                           'submitter.',
            'supports_text_types': True,
        },
        'text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The mode for the text field.',
            'added_in': '2.0',
        },
        'timestamp': {
            'type': DateTimeFieldType,
            'description': 'The date and time that the change was made.',
        },
    }
    uri_object_key = 'change_id'
    model_parent_key = 'review_request'
    allowed_methods = ('GET',)
    mimetype_list_resource_name = 'review-request-changes'
    mimetype_item_resource_name = 'review-request-change'

    def serialize_fields_changed_field(self, obj, **kwargs):
        review_request = obj.review_request.get()
        fields_changed = {}

        for field_name, data in six.iteritems(obj.fields_changed):
            field_cls = get_review_request_field(field_name)

            if field_cls:
                field = field_cls(review_request)

                fields_changed[field.field_id] = \
                    field.serialize_change_entry(obj)

        return fields_changed

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.review_request.get().is_accessible_by(request.user)

    def get_queryset(self, request, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        return review_request.changedescs.filter(public=True)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of changes made on a review request."""
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns the information on a change to a review request."""
        pass


change_resource = ChangeResource()
