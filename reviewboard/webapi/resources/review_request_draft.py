from __future__ import unicode_literals

import logging
import re

from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import ManyToManyField, Q
from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)
from djblets.webapi.fields import (BooleanFieldType,
                                   ChoiceFieldType,
                                   DateTimeFieldType,
                                   DictFieldType,
                                   IntFieldType,
                                   ResourceFieldType,
                                   ResourceListFieldType,
                                   StringFieldType)

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.hostingsvcs.errors import HostingServiceError
from reviewboard.reviews.builtin_fields import BuiltinFieldMixin
from reviewboard.reviews.errors import NotModifiedError, PublishError
from reviewboard.reviews.fields import (get_review_request_fields,
                                        get_review_request_field)
from reviewboard.reviews.models import Group, ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.errors import (InvalidChangeNumberError,
                                         SCMError)
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import (COMMIT_ID_ALREADY_EXISTS,
                                       INVALID_CHANGE_NUMBER,
                                       NOTHING_TO_PUBLISH,
                                       PUBLISH_ERROR,
                                       REPO_INFO_ERROR)
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources


logger = logging.getLogger(__name__)


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
            'type': IntFieldType,
            'description': 'The numeric ID of the draft.',
        },
        'review_request': {
            'type': ResourceFieldType,
            'resource': 'reviewboard.webapi.resources.review_request.'
                        'ReviewRequestResource',
            'description': 'The review request that owns this draft.',
        },
        'last_updated': {
            'type': DateTimeFieldType,
            'description': 'The date and time that the draft was last '
                           'updated.',
        },
        'branch': {
            'type': StringFieldType,
            'description': 'The branch name.',
        },
        'bugs_closed': {
            'type': StringFieldType,
            'description': 'The new list of bugs closed or referenced by this '
                           'change.',
        },
        'depends_on': {
            'type': ResourceListFieldType,
            'resource': 'reviewboard.webapi.resources.review_request.'
                        'ReviewRequestResource',
            'description': 'The list of review requests that this '
                           'review request depends on.',
            'added_in': '1.7.8',
        },
        'changedescription': {
            'type': StringFieldType,
            'description': 'A custom description of what changes are being '
                           'made in this update. It often will be used to '
                           'describe the changes in the diff.',
            'supports_text_types': True,
        },
        'changedescription_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``changedescription`` field.',
            'added_in': '2.0.12',
        },
        'commit_id': {
            'type': StringFieldType,
            'description': 'The updated ID of the commit this review request '
                           'is based upon.',
            'added_in': '2.0',
        },
        'description': {
            'type': StringFieldType,
            'description': 'The new review request description.',
            'supports_text_types': True,
        },
        'description_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``description`` field.',
            'added_in': '2.0.12',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra data as part of the draft. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
        'public': {
            'type': BooleanFieldType,
            'description': 'Whether or not the draft is public. '
                           'This will always be false up until the time '
                           'it is first made public. At that point, the '
                           'draft is deleted.',
        },
        'submitter': {
            'type': StringFieldType,
            'description': 'The user who submitted the review request.',
        },
        'summary': {
            'type': StringFieldType,
            'description': 'The new review request summary.',
        },
        'target_groups': {
            'type': StringFieldType,
            'description': 'A comma-separated list of review groups '
                           'that will be on the reviewer list.',
        },
        'target_people': {
            'type': StringFieldType,
            'description': 'A comma-separated list of users that will '
                           'be on a reviewer list.',
        },
        'testing_done': {
            'type': StringFieldType,
            'description': 'The new testing done text.',
            'supports_text_types': True,
        },
        'testing_done_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``testing_done`` field.',
            'added_in': '2.0.12',
        },
        'text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
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
            'type': StringFieldType,
            'description': 'The new branch name.',
        },
        'bugs_closed': {
            'type': StringFieldType,
            'description': 'A comma-separated list of bug IDs.',
        },
        'commit_id': {
            'type': StringFieldType,
            'description': 'The updated ID of the commit this review request '
                           'is based upon.',
            'added_in': '2.0',
        },
        'depends_on': {
            'type': StringFieldType,
            'description': 'The new list of dependencies of this review '
                           'request.',
            'added_in': '1.7.8',
        },
        'changedescription': {
            'type': StringFieldType,
            'description': 'The change description for this update.',
            'supports_text_types': True,
        },
        'changedescription_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``changedescription`` '
                           'field.',
            'added_in': '2.0.12',
        },
        'description': {
            'type': StringFieldType,
            'description': 'The new review request description.',
            'supports_text_types': True,
        },
        'description_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``description`` '
                           'field.',
            'added_in': '2.0.12',
        },
        'force_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The text type, if any, to force for returned '
                           'text fields. The contents will be converted '
                           'to the requested type in the payload, but '
                           'will not be saved as that type.',
            'added_in': '2.0.9',
        },
        'public': {
            'type': BooleanFieldType,
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
            'type': StringFieldType,
            'description': 'The user who submitted the review request.',
            'added_in': '3.0',
        },
        'summary': {
            'type': StringFieldType,
            'description': 'The new review request summary.',
        },
        'target_groups': {
            'type': StringFieldType,
            'description': 'A comma-separated list of review groups '
                           'that will be on the reviewer list.',
        },
        'target_people': {
            'type': StringFieldType,
            'description': 'A comma-separated list of users that will '
                           'be on a reviewer list.',
        },
        'testing_done': {
            'type': StringFieldType,
            'description': 'The new testing done text.',
            'supports_text_types': True,
        },
        'testing_done_text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
            'description': 'The text type used for the ``testing_done`` '
                           'field.',
            'added_in': '2.0.12',
        },
        'text_type': {
            'type': ChoiceFieldType,
            'choices': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
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
            'type': BooleanFieldType,
            'description': 'Determines if the review request publish '
                           'will not send an email.',
            'added_in': '2.5',
        },
        'update_from_commit_id': {
            'type': BooleanFieldType,
            'description': 'If true, and if ``commit_id`` is provided, '
                           'the review request information and (when '
                           'supported) the diff will be updated based '
                           'on the commit ID.',
            'added_in': '2.0',
        },
    }

    VALUE_LIST_RE = re.compile(r'[, ]+')

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
                            NOT_LOGGED_IN, PERMISSION_DENIED, PUBLISH_ERROR,
                            REPO_INFO_ERROR)
    @webapi_request_fields(
        optional=CREATE_UPDATE_OPTIONAL_FIELDS,
        allow_unknown=True
    )
    def update(self,
               request,
               local_site_name=None,
               branch=None,
               bugs_closed=None,
               changedescription=None,
               commit_id=None,
               depends_on=None,
               submitter=None,
               summary=None,
               target_groups=None,
               target_people=None,
               update_from_commit_id=False,
               trivial=None,
               publish_as_owner=False,
               extra_fields={},
               *args,
               **kwargs):
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

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        draft = review_request.get_draft()

        # Before we update anything, sanitize the commit ID, see if it
        # changed, and make sure that the the new value isn't owned by
        # another review request or draft.
        if commit_id == '':
            commit_id = None

        if (commit_id and
            commit_id != review_request.commit_id and
            (draft is None or commit_id != draft.commit_id)):
            # The commit ID has changed, so now we check for other usages of
            # this ID.
            repository = review_request.repository

            existing_review_request_ids = (
                ReviewRequest.objects
                .filter(commit_id=commit_id,
                        repository=repository)
                .values_list('pk', flat=True)
            )

            if (existing_review_request_ids and
                review_request.pk not in existing_review_request_ids):
                # Another review request is using this ID. Error out.
                return COMMIT_ID_ALREADY_EXISTS

            existing_draft_ids = (
                ReviewRequestDraft.objects
                .filter(commit_id=commit_id,
                        review_request__repository=repository)
                .values_list('pk', flat=True)
            )

            if (existing_draft_ids and
                (draft is None or draft.pk not in existing_draft_ids)):
                # Another review request draft is using this ID. Error out.
                return COMMIT_ID_ALREADY_EXISTS

        # Now that we've completed our initial accessibility and conflict
        # checks, we can start checking for changes to individual fields.
        #
        # We'll keep track of state pertaining to the fields we want to
        # set/save, and any errors we hit. For setting/saving, these's two
        # types of things we're tracking: The new field values (which will be
        # applied to the objects or Many-To-Many relations) and a list of
        # field names to set when calling `save(update_fields=...)`. The
        # former implies the latter. The latter only needs to be directly
        # set if the fields are modified directly by another function.
        new_draft_values = {}
        new_changedesc_values = {}
        draft_update_fields = set()
        changedesc_update_fields = set()
        invalid_fields = {}

        if draft is None:
            draft = ReviewRequestDraft.create(review_request=review_request)

        # Check for a new value for branch.
        if branch is not None:
            new_draft_values['branch'] = branch

        # Check for a new value for bugs_closed:
        if bugs_closed is not None:
            new_draft_values['bugs_closed'] = \
                ','.join(self._parse_bug_list(bugs_closed))

        # Check for a new value for changedescription.
        if changedescription is not None and draft.changedesc_id is None:
            invalid_fields['changedescription'] = [
                'Change descriptions cannot be used for drafts of '
                'new review requests'
            ]

        # Check for a new value for commit_id.
        if commit_id is not None:
            new_draft_values['commit_id'] = commit_id

            if update_from_commit_id:
                try:
                    draft_update_fields.update(
                        draft.update_from_commit_id(commit_id))
                except InvalidChangeNumberError:
                    return INVALID_CHANGE_NUMBER
                except HostingServiceError as e:
                    return REPO_INFO_ERROR.with_message(six.text_type(e))
                except SCMError as e:
                    return REPO_INFO_ERROR.with_message(six.text_type(e))

        # Check for a new value for depends_on.
        if depends_on is not None:
            found_deps, missing_dep_ids = self._find_depends_on(
                dep_ids=self._parse_value_list(depends_on),
                request=request)

            if missing_dep_ids:
                invalid_fields['depends_on'] = missing_dep_ids
            else:
                new_draft_values['depends_on'] = found_deps

        # Check for a new value for submitter.
        if submitter is not None:
            # While we only allow for one submitter, we'll try to parse a
            # possible list of values. This allows us to provide a suitable
            # error message if users try to set more than one submitter
            # (which people do try, in practice).
            found_users, missing_usernames = self._find_users(
                usernames=self._parse_value_list(submitter),
                request=request)

            if len(found_users) + len(missing_usernames) > 1:
                invalid_fields['submitter'] = [
                    'Only one user can be set as the owner of a review '
                    'request'
                ]
            elif missing_usernames:
                assert len(missing_usernames) == 1
                invalid_fields['submitter'] = missing_usernames
            elif found_users:
                assert len(found_users) == 1
                new_draft_values['owner'] = found_users[0]
            else:
                invalid_fields['submitter'] = [
                    'The owner of a review request cannot be blank'
                ]

        # Check for a new value for summary.
        if summary is not None:
            if '\n' in summary:
                invalid_fields['summary'] = [
                    "The summary can't contain a newline"
                ]
            else:
                new_draft_values['summary'] = summary

        # Check for a new value for target_groups.
        if target_groups is not None:
            found_groups, missing_group_names = self._find_review_groups(
                group_names=self._parse_value_list(target_groups),
                request=request)

            if missing_group_names:
                invalid_fields['target_groups'] = missing_group_names
            else:
                new_draft_values['target_groups'] = found_groups

        # Check for a new value for target_people.
        if target_people is not None:
            found_users, missing_usernames = self._find_users(
                usernames=self._parse_value_list(target_people),
                request=request)

            if missing_usernames:
                invalid_fields['target_people'] = missing_usernames
            else:
                new_draft_values['target_people'] = found_users

        # See if we've caught any invalid values. If so, we can error out
        # immediately before we update anything else.
        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
                self.item_result_key: draft,
            }

        # Start applying any rich text processing to any text fields on the
        # ChangeDescription and draft. We'll track any fields that get set
        # for later saving.
        #
        # NOTE: If any text fields or text type fields are ever made
        #       parameters of this method, then their values will need to be
        #       passed directly to set_text_fields() calls below.
        if draft.changedesc_id:
            changedesc_update_fields.update(
                self.set_text_fields(obj=draft.changedesc,
                                     text_field='changedescription',
                                     text_model_field='text',
                                     rich_text_field_name='rich_text',
                                     changedescription=changedescription,
                                     **kwargs))

        for text_field in ('description', 'testing_done'):
            draft_update_fields.update(self.set_text_fields(
                obj=draft,
                text_field=text_field,
                **kwargs))

        # Go through the list of Markdown-enabled custom fields and apply
        # any rich text processing. These will go in extra_data, so we'll
        # want to make sure that's tracked for saving.
        for field_cls in get_review_request_fields():
            if (not issubclass(field_cls, BuiltinFieldMixin) and
                getattr(field_cls, 'enable_markdown', False)):
                modified_fields = self.set_extra_data_text_fields(
                    obj=draft,
                    text_field=field_cls.field_id,
                    extra_fields=extra_fields,
                    **kwargs)

                if modified_fields:
                    draft_update_fields.add('extra_data')

        # See if the caller has set or patched extra_data values. For
        # compatibility, we're going to do this after processing the rich
        # text fields ine extra_data above.
        try:
            if self.import_extra_data(draft, draft.extra_data, extra_fields):
                # Track extra_data for saving.
                draft_update_fields.add('extra_data')
        except ImportExtraDataError as e:
            return e.error_payload

        # Everything checks out. We can now begin the process of applying any
        # field changes and then save objects.
        #
        # We'll start by making an initial pass on the objects we need to
        # either care about. This optimistically lets us avoid a lookup on the
        # ChangeDescription, if it's not being modified.
        to_apply = []

        if draft_update_fields or new_draft_values:
            # If there's any changes made at all to the draft, make sure we
            # allow last_updated to be computed and saved.
            if draft_update_fields or new_draft_values:
                draft_update_fields.add('last_updated')

            to_apply.append((draft, draft_update_fields, new_draft_values))

        if changedesc_update_fields or new_changedesc_values:
            to_apply.append((draft.changedesc, changedesc_update_fields,
                             new_changedesc_values))

        for obj, update_fields, new_values in to_apply:
            new_m2m_values = {}

            # We may have a mixture of field values and Many-To-Many
            # relation values, which we want to set only after the object
            # is saved. Start by setting any field values, and store the
            # M2M values for after.
            for key, value in six.iteritems(new_values):
                field = obj._meta.get_field(key)

                if isinstance(field, ManyToManyField):
                    # Save this until after the object is saved.
                    new_m2m_values[key] = value
                else:
                    # We can set this one now, and mark it for saving.
                    setattr(obj, key, value)
                    update_fields.add(key)

            if update_fields:
                obj.save(update_fields=sorted(update_fields))

            # Now we can set any values on M2M fields.
            #
            # Each entry will have zero or more values. We'll be
            # setting to the list of values, which will fully replace
            # the stored entries in the database.
            for key, values in six.iteritems(new_m2m_values):
                setattr(obj, key, values)

        # Next, check if the draft is set to be published.
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
        # Make sure this exists.
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

    def get_links(self, child_resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Return the links for the resource.

        This method will filter out the draft diffcommit resource when the DVCS
        feature is disabled.

        Args:
            child_resources (list of djblets.webapi.resources.base.
                             WebAPIResource):
                The child resources for which links will be serialized.

            review_request_id (unicode):
                A string represenation of the ID of the review request for
                which links are being returned.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            A dictionary of the links for the resource.
        """
        if (obj is not None and
            not dvcs_feature.is_enabled() and
            resources.draft_diffcommit in child_resources):
            child_resources = list(child_resources)
            child_resources.remove(resources.draft_diffcommit)

        return super(ReviewRequestDraftResource, self).get_links(
            child_resources, obj=obj, request=request, *args, **kwargs)

    def _parse_value_list(self, data):
        """Parse a list of values from a string.

        This will parse a comma-separated list of values into a list of
        strings. All items will be stripped, and any empty values will be
        removed.

        Args:
            data (unicode):
                The data to parse.

        Returns:
            list of unicode:
            The parsed list of strings.
        """
        return [
            value
            for value in [
                value.strip()
                for value in self.VALUE_LIST_RE.split(data)
            ]
            if value
        ]

    def _parse_bug_list(self, bug_ids):
        """Parse a list of bug IDs.

        This will remove any excess whitespace before or after the bug
        IDs, and remove any leading ``#`` characters.

        Args:
            bug_ids (unicode):
                The comma-separated list of bug IDs to parse.

        Returns:
            list of unicode:
            The parsed list of bug IDs.
        """
        return [
            # RB stores bug numbers as numbers, but many people have the
            # habit of prepending #, so filter it out:
            bug.lstrip('#')
            for bug in self._parse_value_list(bug_ids)
        ]

    def _find_depends_on(self, dep_ids, request):
        """Return any found and missing review request dependencies.

        This will look up :py:class:`ReviewRequests
        <reviewboard.reviews.models.review_request.ReviewRequest>` that are
        dependencies with the given list of IDs.

        Args:
            dep_ids (list of unicode):
                The list of review request IDs to look up.

            request (django.http.HttpRequest):
                The HTTP request from the client.

        Return:
            tuple:
            A tuple containing:

            1. A list of :py:class:`~reviewboard.reviews.models.
               review_request.ReviewRequest` instances for any IDs that
               were found.

            2. A list of IDs that could not be found.
        """
        if not dep_ids:
            return [], []

        query_ids = []

        # Filter out anything that isn't an integer.
        for dep_id in dep_ids:
            try:
                query_ids.append(int(dep_id))
            except ValueError:
                pass

        local_site = request.local_site

        if local_site:
            review_requests = ReviewRequest.objects.filter(
                local_site=local_site,
                local_id__in=query_ids)
        else:
            review_requests = ReviewRequest.objects.filter(pk__in=query_ids)

        review_requests = list(review_requests)
        missing_dep_ids = []

        if len(review_requests) != len(dep_ids):
            # Some review requests couldn't be found. Find out which.
            found_dep_ids = set(
                review_request.display_id
                for review_request in review_requests
            )

            missing_dep_ids = [
                dep_id
                for dep_id in dep_ids
                if dep_id not in found_dep_ids
            ]

        return review_requests, missing_dep_ids

    def _find_review_groups(self, group_names, request):
        """Return any found and missing review groups based on a list of names.

        This will look up :py:class:`Groups
        <reviewboard.site.models.group.Group>` from the database based on the
        list of group names.

        Args:
            group_names (list of unicode):
                The list of group names to look up.

            request (django.http.HttpRequest):
                The HTTP request from the client.

        Return:
            tuple:
            A tuple containing:

            1. A list of :py:class:`~reviewboard.site.models.group.Group`
               instances for any group names that were found.

            2. A list of group names that could not be found.
        """
        if not group_names:
            return [], []

        # Build a query that will find each group with a case-insensitive
        # search.
        q = Q()

        for group_name in group_names:
            q |= Q(name__iexact=group_name)

        groups = (
            Group.objects
            .filter(local_site=request.local_site)
            .filter(q)
        )
        missing_group_names = []

        if len(group_names) != len(groups):
            # Some groups couldn't be found. Find out which.
            found_group_names = set(
                group.name
                for group in groups
            )

            missing_group_names = [
                group_name
                for group_name in group_names
                if group_name not in found_group_names
            ]

        return groups, missing_group_names

    def _find_users(self, usernames, request):
        """Return any found and missing users based on a list of usernames.

        This will look up :py:meth:`Users <django.contrib.auth.models.User>`
        from the database based on the list of usernames. If the request is
        not performed on a :term:`Local Site`, then this will then attempt
        to look up any missing users from the authentication backends,
        creating them as necessary.

        Args:
            usernames (list of unicode):
                The list of usernames to look up.

            request (django.http.HttpRequest):
                The HTTP request from the client.

        Return:
            tuple:
            A tuple containing:

            1. A list of :py:class:`~django.contrib.auth.models.User`
               instances for any usernames that were found.

            2. A list of usernames that could not be found.
        """
        if not usernames:
            return [], []

        local_site = request.local_site

        if local_site:
            users = local_site.users.filter(username__in=usernames)
        else:
            users = User.objects.filter(username__in=usernames)

        users = list(users)
        missing_usernames = []

        if len(users) != len(usernames):
            # Some users couldn't be found. Find out which.
            found_usernames = set(
                user.username
                for user in users
            )

            if not local_site:
                # See if any of these users exist in an auth backend.
                # We don't do this for Local Sites, since we don't want to
                # risk creating users in sites where they don't belong.
                for username in usernames:
                    if username in found_usernames:
                        continue

                    for backend in auth.get_backends():
                        try:
                            user = backend.get_or_create_user(username,
                                                              request)

                            if user is not None:
                                users.append(user)
                                found_usernames.add(username)
                        except NotImplementedError:
                            pass
                        except Exception as e:
                            logger.exception(
                                'Error when calling get_or_create_user for '
                                'auth backend %r: %s',
                                backend, e)

            if len(users) != len(usernames):
                missing_usernames = [
                    username
                    for username in usernames
                    if username not in found_usernames
                ]

        return users, missing_usernames


review_request_draft_resource = ReviewRequestDraftResource()
