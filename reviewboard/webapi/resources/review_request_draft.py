from __future__ import unicode_literals

import logging
import re

from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import (ObjectDoesNotExist,
                                    PermissionDenied)
from django.db.models import Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.reviews.builtin_fields import BuiltinFieldMixin
from reviewboard.reviews.errors import NotModifiedError, PublishError
from reviewboard.reviews.fields import (get_review_request_fields,
                                        get_review_request_field)
from reviewboard.reviews.models import Group, ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.errors import InvalidChangeNumberError
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import (COMMIT_ID_ALREADY_EXISTS,
                                       INVALID_CHANGE_NUMBER,
                                       NOTHING_TO_PUBLISH, PUBLISH_ERROR)
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
    """
    model = ReviewRequestDraft
    name = 'draft'
    policy_id = 'review_request_draft'
    singleton = True
    model_parent_key = 'review_request'
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
                           '(in ``YYYY-MM-DD HH:MM:SS`` format).',
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
            'added_in': '1.7.8',
        },
        'changedescription': {
            'type': six.text_type,
            'description': 'A custom description of what changes are being '
                           'made in this update. It often will be used to '
                           'describe the changes in the diff.',
            'supports_text_types': True,
        },
        'changedescription_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``changedescription`` field.',
            'added_in': '2.0.12',
        },
        'commit_id': {
            'type': six.text_type,
            'description': 'The updated ID of the commit this review request '
                           'is based upon.',
            'added_in': '2.0',
        },
        'description': {
            'type': six.text_type,
            'description': 'The new review request description.',
            'supports_text_types': True,
        },
        'description_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``description`` field.',
            'added_in': '2.0.12',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the draft. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the draft is public. '
                           'This will always be false up until the time '
                           'it is first made public. At that point, the '
                           'draft is deleted.',
        },
        'submitter': {
            'type': six.text_type,
            'description': 'The user who submitted the review request.',
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
            'supports_text_types': True,
        },
        'testing_done_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``testing_done`` field.',
            'added_in': '2.0.12',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'Formerly responsible for indicating the text '
                           'type for text fields. Replaced by '
                           '``changedescription_text_type``, '
                           '``description_text_type``, and '
                           '``testing_done_text_type`` in 2.0.12.',
            'added_in': '2.0',
            'deprecated_in': '2.0.12',
        },
    }

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    item_child_resources = [
        resources.draft_diff,
        resources.draft_screenshot,
        resources.draft_file_attachment,
    ]

    CREATE_UPDATE_OPTIONAL_FIELDS = {
        'branch': {
            'type': six.text_type,
            'description': 'The new branch name.',
        },
        'bugs_closed': {
            'type': six.text_type,
            'description': 'A comma-separated list of bug IDs.',
        },
        'commit_id': {
            'type': six.text_type,
            'description': 'The updated ID of the commit this review request '
                           'is based upon.',
            'added_in': '2.0',
        },
        'depends_on': {
            'type': six.text_type,
            'description': 'The new list of dependencies of this review '
                           'request.',
            'added_in': '1.7.8',
        },
        'changedescription': {
            'type': six.text_type,
            'description': 'The change description for this update.',
            'supports_text_types': True,
        },
        'changedescription_text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``changedescription`` '
                           'field.',
            'added_in': '2.0.12',
        },
        'description': {
            'type': six.text_type,
            'description': 'The new review request description.',
            'supports_text_types': True,
        },
        'description_text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``description`` '
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
            'description': 'Whether or not to make the review public. '
                           'If a review is public, it cannot be made '
                           'private again.',
        },
        'publish_as_owner': {
            'type': bool,
            'description': 'Publish on behalf of the owner of the review '
                           'request. If setting ``submitter``, this will '
                           'publish on behalf of the previous owner.',
            'added_in': '3.0.6',
        },
        'submitter': {
            'type': six.text_type,
            'description': 'The user who submitted the review request.',
            'added_in': '3.0',
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
            'supports_text_types': True,
        },
        'testing_done_text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``testing_done`` '
                           'field.',
            'added_in': '2.0.12',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The mode for the ``changedescription``, '
                           '``description``, and ``testing_done`` fields.\n'
                           '\n'
                           'This is deprecated. Please use '
                           '``changedescription_text_type``, '
                           '``description_text_type``, and '
                           '``testing_done_text_type`` instead.',
            'added_in': '2.0',
            'deprecated_in': '2.0.12',
        },
        'trivial': {
            'type': bool,
            'description': 'Determines if the review request publish '
                           'will not send an email.',
            'added_in': '2.5',
        },
        'update_from_commit_id': {
            'type': bool,
            'description': 'If true, and if ``commit_id`` is provided, '
                           'the review request information and (when '
                           'supported) the diff will be updated based '
                           'on the commit ID.',
            'added_in': '2.0',
        },
    }

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

    def get_is_changedescription_rich_text(self, obj):
        return obj.changedesc_id is not None and obj.changedesc.rich_text

    def serialize_bugs_closed_field(self, obj, **kwargs):
        return obj.get_bug_list()

    def serialize_changedescription_field(self, obj, **kwargs):
        if obj.changedesc:
            return obj.changedesc.text
        else:
            return ''

    def serialize_changedescription_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_description_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_status_field(self, obj, **kwargs):
        return ReviewRequest.status_to_string(obj.status)

    def serialize_public_field(self, obj, **kwargs):
        return False

    def serialize_testing_done_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def get_extra_data_field_supports_markdown(self, review_request, key):
        field_cls = get_review_request_field(key)

        return field_cls and getattr(field_cls, 'enable_markdown', False)

    def has_access_permissions(self, request, draft, *args, **kwargs):
        return draft.is_accessible_by(request.user)

    def has_modify_permissions(self, request, draft, *args, **kwargs):
        return draft.is_mutable_by(request.user)

    def has_delete_permissions(self, request, draft, *args, **kwargs):
        return draft.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(COMMIT_ID_ALREADY_EXISTS, DOES_NOT_EXIST,
                            INVALID_CHANGE_NUMBER, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED, PUBLISH_ERROR)
    @webapi_request_fields(
        optional=CREATE_UPDATE_OPTIONAL_FIELDS,
        allow_unknown=True
    )
    def create(self, *args, **kwargs):
        """Creates a draft of a review request.

        If a draft already exists, this will just reuse the existing draft.

        See the documentation on updating a draft for all the details.
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
    @webapi_response_errors(COMMIT_ID_ALREADY_EXISTS, DOES_NOT_EXIST,
                            INVALID_CHANGE_NUMBER, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED, PUBLISH_ERROR)
    @webapi_request_fields(
        optional=CREATE_UPDATE_OPTIONAL_FIELDS,
        allow_unknown=True
    )
    def update(self, request, always_save=False, local_site_name=None,
               update_from_commit_id=False, trivial=None,
               publish_as_owner=False, extra_fields={}, *args, **kwargs):
        """Updates a draft of a review request.

        This will update the draft with the newly provided data.

        Most of the fields correspond to fields in the review request, but
        there is one special one, ``public``. When ``public`` is set to true,
        the draft will be published, moving the new content to the
        review request itself, making it public, and sending out a notification
        (such as an e-mail) if configured on the server. The current draft will
        then be deleted.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review_request = resources.review_request.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        if kwargs.get('commit_id') == '':
            kwargs['commit_id'] = None

        commit_id = kwargs.get('commit_id', None)

        try:
            draft = self.prepare_draft(request, review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        if (commit_id and commit_id != review_request.commit_id and
            commit_id != draft.commit_id):
            # Check to make sure the new commit ID isn't being used already
            # in another review request or draft.
            repository = review_request.repository

            existing_review_request = ReviewRequest.objects.filter(
                commit_id=commit_id,
                repository=repository)

            if (existing_review_request and
                existing_review_request != review_request):
                return COMMIT_ID_ALREADY_EXISTS

            existing_draft = ReviewRequestDraft.objects.filter(
                commit_id=commit_id,
                review_request__repository=repository)

            if existing_draft and existing_draft != draft:
                return COMMIT_ID_ALREADY_EXISTS

        modified_objects = []
        invalid_fields = {}

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

        if commit_id and update_from_commit_id:
            try:
                draft.update_from_commit_id(commit_id)
            except InvalidChangeNumberError:
                return INVALID_CHANGE_NUMBER

        if draft.changedesc_id:
            changedesc = draft.changedesc
            modified_objects.append(draft.changedesc)

            self.set_text_fields(changedesc, 'changedescription',
                                 text_model_field='text',
                                 rich_text_field_name='rich_text',
                                 **kwargs)

        self.set_text_fields(draft, 'description', **kwargs)
        self.set_text_fields(draft, 'testing_done', **kwargs)

        for field_cls in get_review_request_fields():
            if (not issubclass(field_cls, BuiltinFieldMixin) and
                getattr(field_cls, 'enable_markdown', False)):
                self.set_extra_data_text_fields(draft, field_cls.field_id,
                                                extra_fields, **kwargs)

        try:
            self.import_extra_data(draft, draft.extra_data, extra_fields)
        except ImportExtraDataError as e:
            return e.error_payload

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
            if not review_request.public and not draft.changedesc_id:
                # This is a new review request. Publish this on behalf of the
                # owner of the review request, rather than the current user,
                # regardless of the original publish_as_owner in the request.
                # This allows a review request previously created with
                # submit-as= to be published by that user instead of the
                # logged in user.
                publish_as_owner = True

            if publish_as_owner:
                publish_user = review_request.owner
            else:
                # Default to posting as the logged in user.
                publish_user = request.user

            try:
                review_request.publish(user=publish_user, trivial=trivial)
            except NotModifiedError:
                return NOTHING_TO_PUBLISH
            except PublishError as e:
                return PUBLISH_ERROR.with_message(six.text_type(e))

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
            return self.get_no_access_error(request)

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
                            Q(name__iexact=value) &
                            Q(local_site=local_site))
                    elif field_name == "target_people":
                        obj = self._find_user(username=value,
                                              local_site=local_site,
                                              request=request)
                        if obj is None:
                            raise ObjectDoesNotExist
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
        elif field_name == 'submitter':
            submitter = data.rstrip(', ')
            local_site = self._get_local_site(local_site_name)

            try:
                obj = self._find_user(username=submitter,
                                      local_site=local_site,
                                      request=request)

                if obj is None:
                    raise ObjectDoesNotExist

                draft.owner = obj
            except Exception:
                invalid_entries.append(submitter)
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
                except Exception as e:
                    logging.error('Error when calling get_or_create_user for '
                                  'auth backend %r: %s',
                                  backend, e, exc_info=1)

        return None


review_request_draft_resource = ReviewRequestDraftResource()
