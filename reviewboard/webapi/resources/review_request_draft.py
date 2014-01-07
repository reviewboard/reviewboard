from __future__ import unicode_literals

import re

from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.reviews.markdown_utils import markdown_set_field_escaped
from reviewboard.reviews.models import Group, ReviewRequest, ReviewRequestDraft
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.encoder import status_to_string
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources


class ReviewRequestDraftResource(MarkdownFieldsMixin, WebAPIResource):
    """An editable draft of a review request.

    This resource is used to actually modify a review request. Anything made
    in this draft can be published in order to become part of the public
    review request, or it can be discarded.

    Any POST or PUTs on this draft will cause the draft to be created
    automatically. An initial POST is not required.

    There is only ever a maximum of one draft per review request.

    In order to access this resource, the user must either own the review
    request, or it must have the ``reviews.can_edit_reviewrequest`` permission
    set.

    If the ``text_type`` field is set to ``markdown``, then the
    ``changedescription``, ``description`` and ``testing_done`` fields
    should be interpreted by the client as Markdown text.

    The returned text in the payload can be provided in a different format
    by passing ``?force-text-type=`` in the request. This accepts all the
    possible values listed in the ``text_type`` field below.
    """
    model = ReviewRequestDraft
    name = 'draft'
    singleton = True
    model_parent_key = 'review_request'
    last_modified_field = 'last_updated'
    mimetype_item_resource_name = 'review-request-draft'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the draft.',
            'mutable': False,
        },
        'review_request': {
            'type': 'reviewboard.webapi.resources.review_request.'
                    'ReviewRequestResource',
            'description': 'The review request that owns this draft.',
            'mutable': False,
        },
        'last_updated': {
            'type': six.text_type,
            'description': 'The date and time that the draft was last updated '
                           '(in YYYY-MM-DD HH:MM:SS format).',
            'mutable': False,
        },
        'branch': {
            'type': six.text_type,
            'description': 'The branch name.',
        },
        'bugs_closed': {
            'type': six.text_type,
            'description': 'The new list of bugs closed or referenced by this '
                           'change.',
        },
        'depends_on': {
            'type': ['reviewboard.webapi.resources.review_request.'
                     'ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request depends on.',
        },
        'changedescription': {
            'type': six.text_type,
            'description': 'A custom description of what changes are being '
                           'made in this update. It often will be used to '
                           'describe the changes in the diff.',
        },
        'description': {
            'type': six.text_type,
            'description': 'The new review request description.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the draft. '
                           'This can be set by the API or extensions.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the draft is public. '
                           'This will always be false up until the time '
                           'it is first made public. At that point, the '
                           'draft is deleted.',
        },
        'summary': {
            'type': six.text_type,
            'description': 'The new review request summary.',
        },
        'target_groups': {
            'type': six.text_type,
            'description': 'A comma-separated list of review groups '
                           'that will be on the reviewer list.',
        },
        'target_people': {
            'type': six.text_type,
            'description': 'A comma-separated list of users that will '
                           'be on a reviewer list.',
        },
        'testing_done': {
            'type': six.text_type,
            'description': 'The new testing done text.',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The mode for the review request description '
                           'and testing_done fields.',
        },
    }

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    item_child_resources = [
        resources.draft_diff,
        resources.draft_screenshot,
        resources.draft_file_attachment,
    ]

    @classmethod
    def prepare_draft(self, request, review_request):
        """Creates a draft, if the user has permission to."""
        if not review_request.is_mutable_by(request.user):
            raise PermissionDenied

        return ReviewRequestDraft.create(review_request)

    def get_queryset(self, request, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)
        return self.model.objects.filter(review_request=review_request)

    def serialize_bugs_closed_field(self, obj, **kwargs):
        return obj.get_bug_list()

    def serialize_changedescription_field(self, obj, **kwargs):
        if obj.changedesc:
            return self.normalize_text(obj, obj.changedesc.text, **kwargs)
        else:
            return ''

    def serialize_status_field(self, obj, **kwargs):
        return status_to_string(obj.status)

    def serialize_public_field(self, obj, **kwargs):
        return False

    def serialize_description_field(self, obj, **kwargs):
        return self.normalize_text(obj, obj.description, **kwargs)

    def serialize_testing_done_field(self, obj, **kwargs):
        return self.normalize_text(obj, obj.testing_done, **kwargs)

    def has_access_permissions(self, request, draft, *args, **kwargs):
        return draft.is_accessible_by(request.user)

    def has_modify_permissions(self, request, draft, *args, **kwargs):
        return draft.is_mutable_by(request.user)

    def has_delete_permissions(self, request, draft, *args, **kwargs):
        return draft.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        optional={
            'branch': {
                'type': six.text_type,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': six.text_type,
                'description': 'A comma-separated list of bug IDs.',
            },
            'depends_on': {
                'type': six.text_type,
                'description': 'The new list of dependencies of this review '
                               'request.',
            },
            'changedescription': {
                'type': six.text_type,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': six.text_type,
                'description': 'The new review request description.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
            'summary': {
                'type': six.text_type,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': six.text_type,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': six.text_type,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': six.text_type,
                'description': 'The new testing done text.',
            },
            'text_type': {
                'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
                'description': 'The mode for the review request description '
                               'and testing_done fields. the default is '
                               '"plain".',
            },
        },
        allow_unknown=True
    )
    def create(self, *args, **kwargs):
        """Creates a draft of a review request.

        If a draft already exists, this will just reuse the existing draft.

        All fields from the review request will be copied over to the draft,
        unless overridden in the request.

        If ``text_type`` is provided and set to ``markdown``, then the
        ``changedescription``, ``description`` and ``testing_done`` fields
        will be set to be interpreted as Markdown. Otherwise, it will be
        interpreted as plain text.

        Extra data can be stored on the review request for later lookup by
        passing ``extra_data.key_name=value``. The ``key_name`` and ``value``
        can be any valid strings. Passing a blank ``value`` will remove the
        key.  The ``extra_data.`` prefix is required.
        """
        # A draft is a singleton. Creating and updating it are the same
        # operations in practice.
        result = self.update(*args, **kwargs)

        if isinstance(result, tuple):
            if result[0] == 200:
                return (201,) + result[1:]

        return result

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        optional={
            'branch': {
                'type': six.text_type,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': six.text_type,
                'description': 'A comma-separated list of bug IDs.',
            },
            'depends_on': {
                'type': six.text_type,
                'description': 'The new list of dependencies of this review '
                               'request.',
            },
            'changedescription': {
                'type': six.text_type,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': six.text_type,
                'description': 'The new review request description.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the changes public. '
                               'The new changes will be applied to the '
                               'review request, and the old draft will be '
                               'deleted.',
            },
            'summary': {
                'type': six.text_type,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': six.text_type,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': six.text_type,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': six.text_type,
                'description': 'The new testing done text.',
            },
            'text_type': {
                'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
                'description': 'The mode for the review request description '
                               'and testing_done fields. the default is '
                               'to leave the mode unchanged.',
            },
        },
        allow_unknown=True
    )
    def update(self, request, always_save=False, local_site_name=None,
               extra_fields={}, *args, **kwargs):
        """Updates a draft of a review request.

        This will update the draft with the newly provided data.

        Most of the fields correspond to fields in the review request, but
        there is one special one, ``public``. When ``public`` is set to true,
        the draft will be published, moving the new content to the
        review request itself, making it public, and sending out a notification
        (such as an e-mail) if configured on the server. The current draft will
        then be deleted.

        If ``text_type`` is provided and changed from the original value,
        then the ``changedescription``, ``description`` and ``testing_done``
        fields will be set to be interpreted according to the new type.

        When setting to ``markdown`` and not specifying any new text, the
        existing text will be escaped so as not to be unintentionally
        interpreted as Markdown.

        When setting to ``plain``, and new text is not provided, the existing
        text will be unescaped.

        Extra data can be stored on the review request for later lookup by
        passing ``extra_data.key_name=value``. The ``key_name`` and ``value``
        can be any valid strings. Passing a blank ``value`` will remove the
        key. The ``extra_data.`` prefix is required.
        """
        try:
            review_request = resources.review_request.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = self.prepare_draft(request, review_request)
        except PermissionDenied:
            return self._no_access_error(request.user)

        modified_objects = []
        invalid_fields = {}

        old_rich_text = draft.rich_text
        old_changedesc_rich_text = (draft.changedesc_id is not None and
                                    draft.changedesc.rich_text)

        for field_name, field_info in six.iteritems(self.fields):
            if (field_info.get('mutable', True) and
                kwargs.get(field_name, None) is not None):
                field_result, field_modified_objects, invalid = \
                    self._set_draft_field_data(draft, field_name,
                                               kwargs[field_name],
                                               local_site_name, request)

                if invalid:
                    invalid_fields[field_name] = invalid
                elif field_modified_objects:
                    modified_objects += field_modified_objects

        if draft.changedesc_id:
            changedesc = draft.changedesc
            modified_objects.append(draft.changedesc)

            if 'text_type' in kwargs:
                changedesc.rich_text = \
                    (kwargs['text_type'] == self.TEXT_TYPE_MARKDOWN)

            self.normalize_markdown_fields(changedesc, ['changedescription'],
                                           old_changedesc_rich_text,
                                           model_field_map={
                                               'changedescription': 'text',
                                           },
                                           **kwargs)

        self.normalize_markdown_fields(draft, ['description', 'testing_done'],
                                       old_rich_text, **kwargs)

        self._import_extra_data(draft.extra_data, extra_fields)

        if always_save or not invalid_fields:
            for obj in set(modified_objects):
                obj.save()

            draft.save()

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
                self.item_result_key: draft,
            }

        if request.POST.get('public', False):
            review_request.publish(user=request.user)

        return 200, {
            self.item_result_key: draft,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a draft of a review request.

        This is equivalent to pressing :guilabel:`Discard Draft` in the
        review request's page. It will simply erase all the contents of
        the draft.
        """
        # Make sure this exists. We don't want to use prepare_draft, or
        # we'll end up creating a new one.
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            draft = review_request.draft.get()
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, draft, *args, **kwargs):
            return self._no_access_error(request.user)

        draft.delete()

        return 204, {}

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, request, review_request_id, *args, **kwargs):
        """Returns the current draft of a review request."""
        pass

    def _set_draft_field_data(self, draft, field_name, data, local_site_name,
                              request):
        """Sets a field on a draft.

        This will update a draft's field based on the provided data.
        It handles transforming the data as necessary to put it into
        the field.

        if there is a problem with the data, then a validation error
        is returned.

        This returns a tuple of (data, modified_objects, invalid_entries).

        ``data`` is the transformed data.

        ``modified_objects`` is a list of objects (screenshots or change
        description) that were affected.

        ``invalid_entries`` is a list of validation errors.
        """
        modified_objects = []
        invalid_entries = []

        if field_name in ('target_groups', 'target_people', 'depends_on'):
            values = re.split(r"[, ]+", data)
            target = getattr(draft, field_name)
            target.clear()

            local_site = self._get_local_site(local_site_name)

            for value in values:
                # Prevent problems if the user leaves a trailing comma,
                # generating an empty value.
                if not value:
                    continue

                try:
                    if field_name == "target_groups":
                        obj = Group.objects.get(
                            (Q(name__iexact=value) |
                             Q(display_name__iexact=value)) &
                            Q(local_site=local_site))
                    elif field_name == "target_people":
                        obj = self._find_user(username=value,
                                              local_site=local_site,
                                              request=request)
                    elif field_name == "depends_on":
                        obj = ReviewRequest.objects.for_id(value, local_site)

                    target.add(obj)
                except:
                    invalid_entries.append(value)
        elif field_name == 'bugs_closed':
            data = list(self._sanitize_bug_ids(data))
            setattr(draft, field_name, ','.join(data))
        elif field_name == 'changedescription':
            if not draft.changedesc:
                invalid_entries.append('Change descriptions cannot be used '
                                       'for drafts of new review requests')
            else:
                draft.changedesc.text = data

                modified_objects.append(draft.changedesc)
        elif field_name == 'text_type':
            draft.rich_text = (data == self.TEXT_TYPE_MARKDOWN)
        else:
            if field_name == 'summary' and '\n' in data:
                invalid_entries.append('Summary cannot contain newlines')
            else:
                setattr(draft, field_name, data)

        return data, modified_objects, invalid_entries

    def _sanitize_bug_ids(self, entries):
        """Sanitizes bug IDs.

        This will remove any excess whitespace before or after the bug
        IDs, and remove any leading ``#`` characters.
        """
        for bug in entries.split(','):
            bug = bug.strip()

            if bug:
                # RB stores bug numbers as numbers, but many people have the
                # habit of prepending #, so filter it out:
                if bug[0] == '#':
                    bug = bug[1:]

                yield bug

    def _find_user(self, username, local_site, request):
        """Finds a User object matching ``username``.

        This will search all authentication backends, and may create the
        User object if the authentication backend knows that the user exists.
        """
        username = username.strip()

        if local_site:
            return local_site.users.get(username=username)

        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            for backend in auth.get_backends():
                try:
                    return backend.get_or_create_user(username, request)
                except:
                    pass

        return None


review_request_draft_resource = ReviewRequestDraftResource()
