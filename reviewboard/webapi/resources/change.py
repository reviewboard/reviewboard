from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.util.decorators import augment_method_from

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Group, Screenshot
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class ChangeResource(WebAPIResource):
    """Provides information on a change made to a public review request.

    A change includes, optionally, text entered by the user describing the
    change, and also includes a list of fields that were changed on the
    review request.

    If the ``rich_text`` field is set to true, then the provided ``text``
    field shoud be interpreted by the client as Markdown text.

    The list of fields changed are in ``fields_changed``. The keys are the
    names of the fields, and the values are details on that particular
    change to the field.

    For ``summary``, ``description``, ``testing_done`` and ``branch`` fields,
    the following detail keys will be available:

    * ``old``: The old value of the field.
    * ``new``: The new value of the field.

    For ``diff`` fields:

    * ``added``: The diff that was added.

    For ``bugs_closed`` fields:

    * ``old``: A list of old bugs.
    * ``new``: A list of new bugs.
    * ``removed``: A list of bugs that were removed, if any.
    * ``added``: A list of bugs that were added, if any.

    For ``file_attachments``, ``screenshots``, ``target_people`` and
    ``target_groups`` fields:

    * ``old``: A list of old items.
    * ``new``: A list of new items.
    * ``removed``: A list of items that were removed, if any.
    * ``added``: A list of items that were added, if any.

    For ``screenshot_captions`` and ``file_captions`` fields:

    * ``old``: The old caption.
    * ``new``: The new caption.
    * ``screenshot``: The screenshot that was updated.
    """
    model = ChangeDescription
    name = 'change'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the change description.',
        },
        'fields_changed': {
            'type': dict,
            'description': 'The fields that were changed.',
        },
        'rich_text': {
            'type': bool,
            'description': 'Whether or not the text is in rich-text '
                           '(Markdown) format.',
        },
        'text': {
            'type': six.text_type,
            'description': 'The description of the change written by the '
                           'submitter.'
        },
        'timestamp': {
            'type': six.text_type,
            'description': 'The date and time that the change was made '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
    }
    uri_object_key = 'change_id'
    model_parent_key = 'review_request'
    last_modified_field = 'timestamp'
    allowed_methods = ('GET',)
    mimetype_list_resource_name = 'review-request-changes'
    mimetype_item_resource_name = 'review-request-change'

    _changed_fields_to_models = {
        'screenshots': Screenshot,
        'target_people': User,
        'target_groups': Group,
    }

    def serialize_fields_changed_field(self, obj, **kwargs):
        def get_object_cached(model, pk, obj_cache={}):
            if model not in obj_cache:
                obj_cache[model] = {}

            if pk not in obj_cache[model]:
                obj_cache[model][pk] = model.objects.get(pk=pk)

            return obj_cache[model][pk]

        fields_changed = obj.fields_changed.copy()

        for field, data in six.iteritems(fields_changed):
            if field in ('screenshot_captions', 'file_captions'):
                fields_changed[field] = [
                    {
                        'old': data[pk]['old'][0],
                        'new': data[pk]['new'][0],
                        'screenshot': get_object_cached(Screenshot, pk),
                    }
                    for pk, values in six.iteritems(data)
                ]
            elif field == 'diff':
                data['added'] = get_object_cached(DiffSet, data['added'][0][2])
            elif field == 'bugs_closed':
                for key in ('new', 'old', 'added', 'removed'):
                    if key in data:
                        data[key] = [bug[0] for bug in data[key]]
            elif field in ('summary', 'description', 'testing_done', 'branch',
                           'status'):
                if 'old' in data:
                    data['old'] = data['old'][0]

                if 'new' in data:
                    data['new'] = data['new'][0]
            elif field in self._changed_fields_to_models:
                model = self._changed_fields_to_models[field]

                for key in ('new', 'old', 'added', 'removed'):
                    if key in data:
                        data[key] = [
                            get_object_cached(model, item[2])
                            for item in data[key]
                        ]
            else:
                # Just ignore everything else. We don't want to have people
                # depend on some sort of data that we later need to change the
                # format of.
                pass

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
