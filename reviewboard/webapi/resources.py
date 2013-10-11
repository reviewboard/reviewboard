import logging
import os
import re
from time import time
from urllib import quote as urllib_quote

import dateutil.parser
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, \
                        HttpResponseNotModified
from django.template.defaultfilters import timesince
from django.utils.encoding import force_unicode
from django.utils.formats import localize
from django.utils.translation import ugettext as _
from djblets.extensions.base import RegisteredExtension
from djblets.extensions.resources import \
    ExtensionResource as DjbletsExtensionResource
from djblets.gravatars import get_gravatar_url
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import augment_method_from
from djblets.util.http import get_http_requested_mimetype, \
                              get_modified_since, \
                              set_last_modified, http_date
from djblets.webapi.core import WebAPIResponsePaginated, \
                                WebAPIResponse
from djblets.webapi.decorators import webapi_login_required, \
                                      webapi_response_errors, \
                                      webapi_request_fields
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_FORM_DATA, \
                                  NOT_LOGGED_IN, PERMISSION_DENIED
from djblets.webapi.resources import WebAPIResource as DjbletsWebAPIResource, \
                                     UserResource as DjbletsUserResource, \
                                     RootResource as DjbletsRootResource, \
                                     register_resource_for_model, \
                                     get_resource_for_object

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.accounts.models import Profile
from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.diffutils import get_diff_files, \
                                             get_original_file, \
                                             get_patched_file, \
                                             populate_diff_chunks
from reviewboard.diffviewer.errors import EmptyDiffError, DiffTooBigError
from reviewboard.extensions.base import get_extension_manager
from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.reviews.errors import PermissionError
from reviewboard.reviews.forms import DefaultReviewerForm, UploadDiffForm, \
                                      UploadScreenshotForm
from reviewboard.reviews.models import BaseComment, Comment, DefaultReviewer, \
                                       DiffSet, FileDiff, Group, Repository, \
                                       ReviewRequest, ReviewRequestDraft, \
                                       Review, ScreenshotComment, Screenshot, \
                                       FileAttachmentComment
from reviewboard.scmtools.errors import AuthenticationError, \
                                        ChangeNumberInUseError, \
                                        EmptyChangeSetError, \
                                        FileNotFoundError, \
                                        InvalidChangeNumberError, \
                                        SCMError, \
                                        RepositoryNotFoundError, \
                                        UnverifiedCertificateError
from reviewboard.scmtools.models import Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import SSHError, \
                                   BadHostKeyError, \
                                   UnknownHostKeyError
from reviewboard.webapi.decorators import webapi_check_login_required, \
                                          webapi_check_local_site
from reviewboard.webapi.encoder import status_to_string, string_to_status
from reviewboard.webapi.errors import BAD_HOST_KEY, \
                                      CHANGE_NUMBER_IN_USE, \
                                      DIFF_EMPTY, \
                                      DIFF_TOO_BIG, \
                                      EMPTY_CHANGESET, \
                                      FILE_RETRIEVAL_ERROR, \
                                      GROUP_ALREADY_EXISTS, \
                                      HOSTINGSVC_AUTH_ERROR, \
                                      INVALID_CHANGE_NUMBER, \
                                      INVALID_REPOSITORY, \
                                      INVALID_USER, \
                                      MISSING_REPOSITORY, \
                                      MISSING_USER_KEY, \
                                      REPO_AUTHENTICATION_ERROR, \
                                      REPO_FILE_NOT_FOUND, \
                                      REPO_INFO_ERROR, \
                                      REPO_NOT_IMPLEMENTED, \
                                      SERVER_CONFIG_ERROR, \
                                      UNVERIFIED_HOST_CERT, \
                                      UNVERIFIED_HOST_KEY


CUSTOM_MIMETYPE_BASE = 'application/vnd.reviewboard.org'


def _get_local_site(local_site_name):
    if local_site_name:
        return LocalSite.objects.get(name=local_site_name)
    else:
        return None


def _get_form_errors(form):
    fields = {}

    for field in form.errors:
        fields[field] = [force_unicode(e) for e in form.errors[field]]

    return fields


def _no_access_error(user):
    """Returns a WebAPIError indicating the user has no access.

    Which error this returns depends on whether or not the user is logged in.
    If logged in, this will return _no_access_error(request.user). Otherwise, it will
    return NOT_LOGGED_IN.
    """
    if user.is_authenticated():
        return PERMISSION_DENIED
    else:
        return NOT_LOGGED_IN


EXTRA_DATA_LEN = len('extra_data.')

def _import_extra_data(extra_data, fields):
    for key, value in fields.iteritems():
        if key.startswith('extra_data.'):
            key = key[EXTRA_DATA_LEN:]

            if value != '':
                extra_data[key] = value
            elif key in extra_data:
                del extra_data[key]


class WebAPIResource(DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

    mimetype_vendor = 'reviewboard.org'

    def has_access_permissions(self, *args, **kwargs):
        # By default, raise an exception if this is called. Specific resources
        # will have to explicitly override this and opt-in to access.
        raise NotImplementedError(
            '%s must provide a has_access_permissions method'
            % self.__class__.__name__)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def get(self, *args, **kwargs):
        """Returns the serialized object for the resource.

        This will require login if anonymous access isn't enabled on the
        site.
        """
        pass

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional=dict({
            'counts-only': {
                'type': bool,
                'description': 'If specified, a single ``count`` field is '
                               'returned with the number of results, instead '
                               'of the results themselves.',
            },
        }, **DjbletsWebAPIResource.get_list.optional_fields),
        required=DjbletsWebAPIResource.get_list.required_fields,
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Returns a list of objects.

        This will require login if anonymous access isn't enabled on the
        site.

        If ``?counts-only=1`` is passed on the URL, then this will return
        only a ``count`` field with the number of entries, instead of the
        serialized objects.
        """
        if self.model and request.GET.get('counts-only', False):
            return 200, {
                'count': self.get_queryset(request, is_list=True,
                                           *args, **kwargs).count()
            }
        else:
            return self._get_list_impl(request, *args, **kwargs)

    @webapi_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def delete(self, *args, **kwargs):
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Actual implementation to return the list of results.

        This by default calls the parent WebAPIResource.get_list, but this
        can be overridden by subclasses to provide a more custom
        implementation while still retaining the ?counts-only=1 functionality.
        """
        return super(WebAPIResource, self).get_list(request, *args, **kwargs)

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object.

        This is an override of djblets.webapi.resources.WebAPIResource.get_href,
        which takes into account our local_site_name namespacing in order to get
        the right prefix on URLs.
        """
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj))

        return request.build_absolute_uri(
            local_site_reverse(self._build_named_url(self.name),
                               request=request,
                               kwargs=href_kwargs))


class BaseCommentResource(WebAPIResource):
    """Base class for comment resources.

    Provides common fields and functionality for all comment resources.
    """
    fields = {
        'issue_opened': {
            'type': bool,
            'description': 'Whether or not a comment opens an issue.',
        },
        'issue_status': {
            'type': ('dropped', 'open', 'resolved'),
            'description': 'The status of an issue.',
        },
    }
    last_modified_field = 'timestamp'

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.is_mutable_by(request.user)

    def update_issue_status(self, request, comment_resource, *args, **kwargs):
        """Updates the issue status for a comment.

        Handles all of the logic for updating an issue status.
        """
        try:
            review_request = review_request_resource.get_object(request, *args,
                                                                **kwargs)
            comment = comment_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # We want to ensure that the user that is trying to modify the state
        # of an issue is the user who created the review request.
        if not review_request_resource.has_modify_permissions(request,
                                                              review_request):
            return _no_access_error(request.user)

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


base_comment_resource = BaseCommentResource()


class BaseDiffCommentResource(BaseCommentResource):
    """Base class for diff comment resources.

    Provides common fields and functionality for all diff comment resources.
    """
    model = Comment
    name = 'diff_comment'
    fields = dict({
        'id': {
            'type': int,
            'description': 'The numeric ID of the comment.',
        },
        'first_line': {
            'type': int,
            'description': 'The line number that the comment starts at.',
        },
        'num_lines': {
            'type': int,
            'description': 'The number of lines the comment spans.',
        },
        'text': {
            'type': str,
            'description': 'The comment text.',
        },
        'filediff': {
            'type': 'reviewboard.webapi.resources.FileDiffResource',
            'description': 'The per-file diff that the comment was made on.',
        },
        'interfilediff': {
            'type': 'reviewboard.webapi.resources.FileDiffResource',
            'description': "The second per-file diff in an interdiff that "
                           "the comment was made on. This will be ``null`` if "
                           "the comment wasn't made on an interdiff.",
        },
        'timestamp': {
            'type': str,
            'description': 'The date and time that the comment was made '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the comment is part of a public '
                           'review.',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.UserResource',
            'description': 'The user who made the comment.',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, review_request_id, review_id=None,
                     is_list=False, *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the specified review request
        which are either public or owned by the requesting user.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff-revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.
        """
        try:
            review_request = review_request_resource.get_object(
                request, review_request_id, *args, **kwargs)
        except ObjectDoesNotExist:
            raise self.model.DoesNotExist

        q = self.model.objects.filter(
            filediff__diffset__history__review_request=review_request,
            review__isnull=False)

        if is_list:
            if review_id:
                q = q.filter(review=review_id)

            if 'interdiff-revision' in request.GET:
                interdiff_revision = int(request.GET['interdiff-revision'])
                q = q.filter(
                    interfilediff__diffset__revision=interdiff_revision)

            if 'line' in request.GET:
                q = q.filter(first_line=int(request.GET['line']))

        order_by = kwargs.get('order-by', None)

        if order_by:
            q = q.order_by(*[
                field
                for field in order_by.split(',')
                if '__' not in field  # Don't allow joins
            ])

        return q

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    @webapi_request_fields(
        optional={
            'interdiff-revision': {
                'type': int,
                'description': 'The second revision in an interdiff revision '
                               'range. The comments will be limited to this '
                               'range.',
            },
            'line': {
                'type': int,
                'description': 'The line number that each comment must '
                               'start on.',
            },
            'order-by': {
                'type': str,
                'description': 'Comma-separated list of fields to order by',
            },
        },
        allow_unknown=True
    )
    @augment_method_from(BaseCommentResource)
    def get_list(self, request, review_id=None, *args, **kwargs):
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment."""
        pass


class DefaultReviewerResource(WebAPIResource):
    """Provides information on default reviewers for review requests.

    Review Board will apply any default reviewers that match the repository
    and any file path in an uploaded diff for new and updated review requests.
    A default reviewer entry can list multiple users and groups.

    This is useful when different groups own different parts of a codebase.
    Adding DefaultReviewer entries ensures that the right people will always
    see the review request and discussions.

    Default reviewers take a regular expression for the file path matching,
    making it flexible.

    As a tip, specifying ``.*`` for the regular expression would have this
    default reviewer applied to every review request on the matched
    repositories.
    """
    name = 'default_reviewer'
    model = DefaultReviewer
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the default reviewer.',
        },
        'name': {
            'type': str,
            'description': 'The descriptive name of the entry.',
        },
        'file_regex': {
            'type': str,
            'description': 'The regular expression that is used to match '
                           'files uploaded in a diff.',
        },
        'repositories': {
            'type': str,
            'description': 'A comma-separated list of repository IDs that '
                           'this default reviewer will match against.',
        },
        'users': {
            'type': str,
            'description': 'A comma-separated list of usernames that '
                           'this default reviewer applies to matched review '
                           'requests.',
        },
        'groups': {
            'type': str,
            'description': 'A comma-separated list of group names that '
                           'this default reviewer applies to matched review '
                           'requests.',
        },
    }
    uri_object_key = 'default_reviewer_id'
    autogenerate_etags = True

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def serialize_repositories_field(self, default_reviewer, **kwargs):
        return default_reviewer.repository.all()

    def serialize_users_field(self, default_reviewer, **kwargs):
        return default_reviewer.people.all()

    @webapi_check_login_required
    def get_queryset(self, request, is_list=False, local_site_name=None,
                     *args, **kwargs):
        """Returns a queryset for DefaultReviewer models.

        By default, this returns all default reviewers.

        If the queryset is being used for a list of default reviewer
        resources, then it can be further filtered by one or more of the
        arguments listed in get_list.
        """
        local_site = _get_local_site(local_site_name)
        queryset = self.model.objects.filter(local_site=local_site)

        if is_list:
            if 'repositories' in request.GET:
                for repo_id in request.GET.get('repositories').split(','):
                    try:
                        queryset = queryset.filter(repository=repo_id)
                    except ValueError:
                        pass

            if 'users' in request.GET:
                for username in request.GET.get('users').split(','):
                    queryset = queryset.filter(people__username=username)

            if 'groups' in request.GET:
                for name in request.GET.get('groups').split(','):
                    queryset = queryset.filter(groups__name=name)

        return queryset

    def has_access_permissions(self, request, default_reviewer,
                               *args, **kwargs):
        return default_reviewer.is_accessible_by(request.user)

    def has_modify_permissions(self, request, default_reviewer,
                               *args, **kwargs):
        return default_reviewer.is_mutable_by(request.user)

    def has_delete_permissions(self, request, default_reviewer,
                               *args, **kwargs):
        return default_reviewer.is_mutable_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of default reviewers on the server.

        By default, this lists all default reviewers. This list can be
        further filtered down by one or more of the following arguments
        in the URL:

          * ``repositories``
              - A comma-separated list of IDs of repositories that the default
                reviewer matches against. Only default reviewers that match
                every specified repository will be returned.

          * ``users``
              - A comma-separated list of usernames that the default reviewer
                applies. Only default reviewers that apply each of these users
                will be returned.

          * ``groups``
              - A comma-separated list of group names that the default reviewer
                applies. Only default reviewers that apply each of these groups
                will be returned.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular default reviewer."""
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'name': {
                'type': str,
                'description': 'The name of the default reviewer entry.',
            },
            'file_regex': {
                'type': str,
                'description': 'The regular expression used to match file '
                               'paths in newly uploaded diffs.',
            },
        },
        optional={
            'repositories': {
                'type': str,
                'description': 'A comma-separated list of repository IDs.',
            },
            'groups': {
                'type': str,
                'description': 'A comma-separated list of group names.',
            },
            'users': {
                'type': str,
                'description': 'A comma-separated list of usernames.',
            }
        },
    )
    def create(self, request, local_site_name=None, *args, **kwargs):
        """Creates a new default reviewer entry.

        Note that by default, a default reviewer will apply to review
        requests on all repositories, unless one or more repositories are
        provided in the default reviewer's list.
        """
        local_site = _get_local_site(local_site_name)

        if not self.model.objects.can_create(request.user, local_site):
            return _no_access_error(request.user)

        code, data = self._create_or_update(local_site, **kwargs)

        if code == 200:
            return 201, data
        else:
            return code, data

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'name': {
                'type': str,
                'description': 'The name of the default reviewer entry.',
            },
            'file_regex': {
                'type': str,
                'description': 'The regular expression used to match file '
                               'paths in newly uploaded diffs.',
            },
            'repositories': {
                'type': str,
                'description': 'A comma-separated list of repository IDs.',
            },
            'groups': {
                'type': str,
                'description': 'A comma-separated list of group names.',
            },
            'users': {
                'type': str,
                'description': 'A comma-separated list of usernames.',
            }
        },
    )
    def update(self, request, local_site_name=None, *args, **kwargs):
        """Updates an existing default reviewer entry.

        If the list of repositories is updated with a blank entry, then
        the default reviewer will apply to review requests on all repositories.
        """
        try:
            default_reviewer = self.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, default_reviewer):
            return _no_access_error(request.user)

        local_site = _get_local_site(local_site_name)

        return self._create_or_update(local_site, default_reviewer, **kwargs)

    def _create_or_update(self, local_site, default_reviewer=None, **kwargs):
        invalid_fields = {}
        form_data = {}

        if 'groups' in kwargs:
            group_names = kwargs['groups'].split(',')
            group_ids = [
                group['pk']
                for group in Group.objects.filter(
                    name__in=group_names, local_site=local_site).values('pk')
            ]

            if len(group_ids) != len(group_names):
                invalid_fields['groups'] = [
                    'One or more groups were not found'
                ]

            form_data['groups'] = group_ids

        if 'repositories' in kwargs:
            repo_ids = []

            try:
                repo_ids = [
                    int(repo_id)
                    for repo_id in kwargs['repositories'].split(',')
                ]
            except ValueError:
                invalid_fields['repositories'] = [
                    'One or more repository IDs were not in a valid format.'
                ]

            if repo_ids:
                found_count = Repository.objects.filter(
                    pk__in=repo_ids, local_site=local_site).count()

                if len(repo_ids) != found_count:
                    invalid_fields['repositories'] = [
                        'One or more repositories were not found'
                    ]

            form_data['repository'] = repo_ids

        if 'users' in kwargs:
            usernames = kwargs['users'].split(',')
            user_ids = [
                user['pk']
                for user in User.objects.filter(username__in=usernames)
                    .values('pk')
            ]

            if len(user_ids) != len(usernames):
                invalid_fields['users'] = [
                    'One or more users were not found'
                ]

            form_data['people'] = user_ids

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields
            }

        for field in ('name', 'file_regex'):
            if field in kwargs:
                form_data[field] = kwargs[field]

        if local_site:
            form_data['local_site'] = local_site.pk

        form = DefaultReviewerForm(form_data, instance=default_reviewer)

        if not form.is_valid():
            # The form uses "people" and "repository", but we expose these
            # as "users" and "repositories", so transmogrify the errors a bit.
            field_errors = _get_form_errors(form)

            if 'people' in field_errors:
                field_errors['users'] = field_errors.pop('people')

            if 'repository' in field_errors:
                field_errors['repositories'] = field_errors.pop('repository')

            return INVALID_FORM_DATA, {
                'fields': field_errors,
            }

        default_reviewer = form.save()

        return 200, {
            self.item_result_key: default_reviewer,
        }

    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the default reviewer entry.

        This will not remove any reviewers from any review requests.
        It will only prevent these default reviewer rules from being
        applied to any new review requests or updates.
        """
        pass


default_reviewer_resource = DefaultReviewerResource()


class ExtensionResource(WebAPIResource, DjbletsExtensionResource):
    """A resource for representing a Review Board Extension."""

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsExtensionResource)
    def get(self, *args, **kwargs):
        """For retrieving data about an ExtensionResource."""
        pass

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsExtensionResource)
    def get_list(self, request, *args, **kwargs):
        """For retrieving the list of available ExtensionResources."""
        pass

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsExtensionResource)
    def update(self, request, *args, **kwargs):
        pass

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Only staff have modify permissions for ExtensionResources. """
        return request.user and request.user.is_superuser


extension_resource = ExtensionResource(get_extension_manager())


class FileDiffCommentResource(BaseDiffCommentResource):
    """Provides information on comments made on a particular per-file diff.

    The list of comments cannot be modified from this resource. It's meant
    purely as a way to see existing comments that were made on a diff. These
    comments will span all public reviews.
    """
    allowed_methods = ('GET',)
    model_parent_key = 'filediff'
    uri_object_key = None

    mimetype_list_resource_name = 'file-diff-comments'
    mimetype_item_resource_name = 'file-diff-comment'

    def get_queryset(self, request, review_request_id, diff_revision,
                     filediff_id, *args, **kwargs):
        """Returns a queryset for Comment models.

        This filters the query for comments on the specified review request
        and made on the specified diff revision, which are either public or
        owned by the requesting user.

        If the queryset is being used for a list of comment resources,
        then this can be further filtered by passing ``?interdiff-revision=``
        on the URL to match the given interdiff revision, and
        ``?line=`` to match comments on the given line number.
        """
        q = super(FileDiffCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        return q.filter(filediff__diffset__revision=diff_revision,
                        filediff=filediff_id)

    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, request, diff_revision=None, *args, **kwargs):
        """Returns the list of comments on a file in a diff.

        This list can be filtered down by using the ``?line=`` and
        ``?interdiff-revision=``.

        To filter for comments that start on a particular line in the file,
        using ``?line=``.

        To filter for comments that span revisions of diffs, you can specify
        the second revision in the range using ``?interdiff-revision=``.
        """
        pass

filediff_comment_resource = FileDiffCommentResource()


class ReviewDiffCommentResource(BaseDiffCommentResource):
    """Provides information on diff comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    mimetype_list_resource_name = 'review-diff-comments'
    mimetype_item_resource_name = 'review-diff-comment'

    def get_queryset(self, request, review_request_id, review_id,
                     *args, **kwargs):
        q = super(ReviewDiffCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'filediff_id': {
                'type': int,
                'description': 'The ID of the file diff the comment is on.',
            },
            'first_line': {
                'type': int,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': int,
                'description': 'The number of lines the comment spans.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
        optional = {
            'interfilediff_id': {
                'type': int,
                'description': 'The ID of the second file diff in the '
                               'interdiff the comment is on.',
            },
            'issue_opened': {
                'type': bool,
                'description': 'Whether the comment opens an issue.',
            },
        },
    )
    def create(self, request, first_line, num_lines, text,
               filediff_id, issue_opened=False, interfilediff_id=None, *args,
               **kwargs):
        """Creates a new diff comment.

        This will create a new diff comment on this review. The review
        must be a draft review.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        filediff = None
        interfilediff = None
        invalid_fields = {}

        try:
            filediff = FileDiff.objects.get(
                pk=filediff_id,
                diffset__history__review_request=review_request)
        except ObjectDoesNotExist:
            invalid_fields['filediff_id'] = \
                ['This is not a valid filediff ID']

        if filediff and interfilediff_id:
            if interfilediff_id == filediff.id:
                invalid_fields['interfilediff_id'] = \
                    ['This cannot be the same as filediff_id']
            else:
                try:
                    interfilediff = FileDiff.objects.get(
                        pk=interfilediff_id,
                        diffset__history=filediff.diffset.history)
                except ObjectDoesNotExist:
                    invalid_fields['interfilediff_id'] = \
                        ['This is not a valid interfilediff ID']

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }

        new_comment = self.model(filediff=filediff,
                                 interfilediff=interfilediff,
                                 text=text,
                                 first_line=first_line,
                                 num_lines=num_lines,
                                 issue_opened=bool(issue_opened))

        if issue_opened:
            new_comment.issue_status = BaseComment.OPEN
        else:
            new_comment.issue_status = None

        new_comment.save()

        review.comments.add(new_comment)
        review.save()

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional = {
            'first_line': {
                'type': int,
                'description': 'The line number the comment starts at.',
            },
            'num_lines': {
                'type': int,
                'description': 'The number of lines the comment spans.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
            'issue_opened': {
                'type': bool,
                'description': 'Whether or not the comment opens an issue.',
            },
            'issue_status': {
                'type': ('dropped', 'open', 'resolved'),
                'description': 'The status of an open issue.',
            }
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a diff comment.

        This can update the text or line range of an existing comment.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            diff_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Determine whether or not we're updating the issue status.
        # If so, delegate to the base_comment_resource.
        if base_comment_resource.should_update_issue_status(diff_comment,
                                                            **kwargs):
            return base_comment_resource.update_issue_status(request, self,
                                                             *args, **kwargs)

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        # If we've updated the comment from having no issue opened,
        # to having an issue opened, we need to set the issue status
        # to OPEN.
        if not diff_comment.issue_opened and kwargs.get('issue_opened', False):
            diff_comment.issue_status = BaseComment.OPEN

        for field in ('text', 'first_line', 'num_lines', 'issue_opened'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(diff_comment, field, value)

        diff_comment.save()

        return 200, {
            self.item_result_key: diff_comment,
        }

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of comments made on a review.

        This list can be filtered down by using the ``?line=`` and
        ``?interdiff-revision=``.

        To filter for comments that start on a particular line in the file,
        using ``?line=``.

        To filter for comments that span revisions of diffs, you can specify
        the second revision in the range using ``?interdiff-revision=``.
        """
        pass

review_diff_comment_resource = ReviewDiffCommentResource()


class ReviewReplyDiffCommentResource(BaseDiffCommentResource):
    """Provides information on replies to diff comments made on a review reply.

    If the reply is a draft, then comments can be added, deleted, or
    changed on this list. However, if the reply is already published,
    then no changed can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'
    fields = dict({
        'reply_to': {
            'type': ReviewDiffCommentResource,
            'description': 'The comment being replied to.',
        },
    }, **BaseDiffCommentResource.fields)

    mimetype_list_resource_name = 'review-reply-diff-comments'
    mimetype_item_resource_name = 'review-reply-diff-comment'

    def get_queryset(self, request, review_request_id, review_id, reply_id,
                     *args, **kwargs):
        q = super(ReviewReplyDiffCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'reply_to_id': {
                'type': int,
                'description': 'The ID of the comment being replied to.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, reply_to_id, text, *args, **kwargs):
        """Creates a new reply to a diff comment on the parent review.

        This will create a new diff comment as part of this reply. The reply
        must be a draft reply.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        try:
            comment = \
                review_diff_comment_resource.get_object(request,
                                                        comment_id=reply_to_id,
                                                        *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid comment ID'],
                }
            }

        q = self.get_queryset(request, *args, **kwargs)
        q = q.filter(Q(reply_to=comment) & Q(review=reply))

        try:
            new_comment = q.get()

            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            is_new = False
        except self.model.DoesNotExist:
            new_comment = self.model(filediff=comment.filediff,
                                     interfilediff=comment.interfilediff,
                                     reply_to=comment,
                                     first_line=comment.first_line,
                                     num_lines=comment.num_lines)
            is_new = True

        new_comment.text = text
        new_comment.save()

        data = {
            self.item_result_key: new_comment,
        }

        if is_new:
            reply.comments.add(new_comment)
            reply.save()

            return 201, data
        else:
            return 303, data, {
                'Location': self.get_href(new_comment, request, *args, **kwargs)
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'text': {
                'type': str,
                'description': 'The new comment text.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply to a diff comment.

        This can only update the text in the comment. The comment being
        replied to cannot change.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
            diff_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        for field in ('text',):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(diff_comment, field, value)

        diff_comment.save()

        return 200, {
            self.item_result_key: diff_comment,
        }

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes a comment from a draft reply.

        This will remove the comment from the reply. This cannot be undone.

        Only comments on draft replies can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get(self, *args, **kwargs):
        """Returns information on a reply to a comment.

        Much of the information will be identical to that of the comment
        being replied to. For example, the range of lines. This is because
        the reply to the comment is meant to cover the exact same code that
        the original comment covers.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of replies to comments made on a review reply.

        This list can be filtered down by using the ``?line=`` and
        ``?interdiff-revision=``.

        To filter for comments that start on a particular line in the file,
        using ``?line=``.

        To filter for comments that span revisions of diffs, you can specify
        the second revision in the range using ``?interdiff-revision=``.
        """
        pass

review_reply_diff_comment_resource = ReviewReplyDiffCommentResource()


class OriginalFileResource(WebAPIResource):
    """Provides the unpatched file corresponding to a file diff."""
    name = 'original_file'
    singleton = True
    allowed_item_mimetypes = ['text/plain']

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the original unpatched file.

        The file is returned as :mimetype:`text/plain` and is the original
        file before applying a patch.
        """
        try:
            filediff = filediff_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if filediff.is_new:
            return DOES_NOT_EXIST

        try:
            orig_file = get_original_file(filediff, request=request)
        except Exception, e:
            logging.error("Error retrieving original file: %s", e, exc_info=1,
                          request=request)
            return FILE_RETRIEVAL_ERROR

        resp = HttpResponse(orig_file, mimetype='text/plain')
        filename = urllib_quote(filediff.source_file)
        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp

original_file_resource = OriginalFileResource()


class PatchedFileResource(WebAPIResource):
    """Provides the patched file corresponding to a file diff."""
    name = 'patched_file'
    singleton = True
    allowed_item_mimetypes = ['text/plain']

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the patched file.

        The file is returned as :mimetype:`text/plain` and is the result
        of applying the patch to the original file.
        """
        try:
            filediff = filediff_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if filediff.deleted:
            return DOES_NOT_EXIST

        try:
            orig_file = get_original_file(filediff, request=request)
        except Exception, e:
            logging.error("Error retrieving original file: %s", e, exc_info=1,
                          request=request)
            return FILE_RETRIEVAL_ERROR

        try:
            patched_file = get_patched_file(orig_file, filediff,
                                            request=request)
        except Exception, e:
            logging.error("Error retrieving patched file: %s", e, exc_info=1,
                          request=request)
            return FILE_RETRIEVAL_ERROR

        resp = HttpResponse(patched_file, mimetype='text/plain')
        filename = urllib_quote(filediff.dest_file)
        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp

patched_file_resource = PatchedFileResource()


class FileDiffResource(WebAPIResource):
    """Provides information on per-file diffs.

    Each of these contains a single, self-contained diff file that
    applies to exactly one file on a repository.
    """
    model = FileDiff
    name = 'file'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the file diff.',
        },
        'source_file': {
            'type': str,
            'description': 'The original name of the modified file in the '
                           'diff.',
        },
        'dest_file': {
            'type': str,
            'description': 'The new name of the patched file. This may be '
                           'the same as the existing file.',
        },
        'source_revision': {
            'type': str,
            'description': 'The revision of the file being modified. This '
                           'is a valid revision in the repository.',
        },
        'dest_detail': {
            'type': str,
            'description': 'Additional information of the destination file. '
                           'This is parsed from the diff, but is usually '
                           'not used for anything.',
        },
    }
    item_child_resources = [
        filediff_comment_resource,
        original_file_resource,
        patched_file_resource,
    ]

    uri_object_key = 'filediff_id'
    model_parent_key = 'diffset'

    DIFF_DATA_MIMETYPE_BASE = CUSTOM_MIMETYPE_BASE + '.diff.data'
    DIFF_DATA_MIMETYPE_JSON = DIFF_DATA_MIMETYPE_BASE + '+json'
    DIFF_DATA_MIMETYPE_XML = DIFF_DATA_MIMETYPE_BASE + '+xml'

    allowed_item_mimetypes = WebAPIResource.allowed_item_mimetypes + [
        'text/x-patch',
        DIFF_DATA_MIMETYPE_JSON,
        DIFF_DATA_MIMETYPE_XML,
    ]

    def get_last_modified(self, request, obj, *args, **kwargs):
        return obj.diffset.timestamp

    def get_queryset(self, request, review_request_id, diff_revision,
                     local_site_name=None, *args, **kwargs):
        if local_site_name:
            review_request = review_request_resource.get_object(
                request,
                review_request_id=review_request_id,
                diff_revision=diff_revision,
                local_site_name=local_site_name,
                *args,
                **kwargs)
            review_request_id = review_request.pk

        return self.model.objects.filter(
            diffset__history__review_request=review_request_id,
            diffset__revision=diff_revision)

    def has_access_permissions(self, request, filediff, *args, **kwargs):
        review_request = review_request_resource.get_object(
            request, *args, **kwargs)

        return review_request_resource.has_access_permissions(
            request, review_request, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of public per-file diffs on the review request.

        Each per-file diff has information about the diff. It does not
        provide the contents of the diff. For that, access the per-file diff's
        resource directly and use the correct mimetype.
        """
        pass

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Returns a dictionary of links coming off this resource.

        If the file represented by the FileDiffResource is new,
        the link to the OriginalFileResource will be removed.
        Alternatively, if the file is deleted, the link to the
        PatchedFileResource will be removed.
        """
        links = super(FileDiffResource, self).get_links(resources, obj,
                                                        request, *args,
                                                        **kwargs)

        # Only remove the links if we are returning them for
        # a specific filediff, and not a list of filediffs.
        if obj:
            if obj.is_new:
                del links[original_file_resource.name_plural]

            if obj.deleted:
                del links[patched_file_resource.name_plural]

        return links

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the information or contents on a per-file diff.

        The output varies by mimetype.

        If :mimetype:`application/json` or :mimetype:`application/xml` is
        used, then the fields for the diff are returned, like with any other
        resource.

        If :mimetype:`text/x-patch` is used, then the actual diff file itself
        is returned. This diff should be as it was when uploaded originally,
        for this file only, with potentially some extra SCM-specific headers
        stripped.

        If :mimetype:`application/vnd.reviewboard.org.diff.data+json` or
        :mimetype:`application/vnd.reviewboard.org.diff.data+xml` is used,
        then the raw diff data (lists of inserts, deletes, replaces, moves,
        header information, etc.) is returned in either JSON or XML. This
        contains nearly all of the information used to render the diff in
        the diff viewer, and can be useful for building a diff viewer that
        interfaces with Review Board.

        If ``?syntax-highlighting=1`` is passed, the rendered diff content
        for each line will contain HTML markup showing syntax highlighting.
        Otherwise, the content will be in plain text.

        The format of the diff data is a bit complex. The data is stored
        under a top-level ``diff_data`` element and contains the following
        information:

        .. list-table::
           :header-rows: 1
           :widths: 25 15 60

           * - Field
             - Type
             - Description

           * - **binary**
             - Boolean
             - Whether or not the file is a binary file. Binary files
               won't have any diff content to display.

           * - **chunks**
             - List of Dictionary
             - A list of chunks. These are used to render the diff. See below.

           * - **changed_chunk_indexes**
             - List of Integer
             - The list of chunks in the diff that have actual changes
               (inserts, deletes, or replaces).

           * - **new_file**
             - Boolean
             - Whether or not this is a newly added file, rather than an
               existing file in the repository.

           * - **num_changes**
             - Integer
             - The number of changes made in this file (chunks of adds,
               removes, or deletes).

        Each chunk contains the following fields:

        .. list-table::
           :header-rows: 1
           :widths: 25 15 60

           * - Field
             - Type
             - Description

           * - **change**
             - One of ``equal``, ``delete``, ``insert``, ``replace``
             - The type of change on this chunk. The type influences what
               sort of information is available for the chunk.

           * - **collapsable**
             - Boolean
             - Whether or not this chunk is collapseable. A collapseable chunk
               is one that is hidden by default in the diff viewer, but can
               be expanded. These will always be ``equal`` chunks, but not
               every ``equal`` chunk is necessarily collapseable (as they
               may be there to provide surrounding context for the changes).

           * - **index**
             - Integer
             - The index of the chunk. This is 0-based.

           * - **lines**
             - List of List
             - The list of rendered lines for a side-by-side diff. Each
               entry in the list is itself a list with 8 items:

               1. Row number of the line in the combined side-by-side diff.
               2. The line number of the line in the left-hand file, as an
                  integer (for ``replace``, ``delete``, and ``equal`` chunks)
                  or an empty string (for ``insert``).
               3. The text for the line in the left-hand file.
               4. The indexes within the text for the left-hand file that
                  have been replaced by text in the right-hand side. Each
                  index is a list of ``start, end`` positions, 0-based.
                  This is only available for ``replace`` lines. Otherwise the
                  list is empty.
               5. The line number of the line in the right-hand file, as an
                  integer (for ``replace``, ``insert`` and ``equal`` chunks)
                  or an empty string (for ``delete``).
               6. The text for the line in the right-hand file.
               7. The indexes within the text for the right-hand file that
                  are replacements for text in the left-hand file. Each
                  index is a list of ``start, end`` positions, 0-based.
                  This is only available for ``replace`` lines. Otherwise the
                  list is empty.
               8. A boolean that indicates if the line contains only
                  whitespace changes.

           * - **meta**
             - Dictionary
             - Additional information about the chunk. See below for more
               information.

           * - **numlines**
             - Integer
             - The number of lines in the chunk.

        A chunk's meta information contains:

        .. list-table::
           :header-rows: 1
           :widths: 25 15 60

           * - Field
             - Type
             - Description

           * - **headers**
             - List of (String, String)
             - Class definitions, function definitions, or other useful
               headers that should be displayed before this chunk. This helps
               users to identify where in a file they are and what the current
               chunk may be a part of.

           * - **whitespace_chunk**
             - Boolean
             - Whether or not the entire chunk consists only of whitespace
               changes.

           * - **whitespace_lines**
             - List of (Integer, Integer)
             - A list of ``start, end`` row indexes in the lins that contain
               whitespace-only changes. These are 1-based.

        Other meta information may be available, but most is intended for
        internal use and shouldn't be relied upon.
        """
        mimetype = get_http_requested_mimetype(request,
                                               self.allowed_item_mimetypes)

        if mimetype == 'text/x-patch':
            return self._get_patch(request, *args, **kwargs)
        elif mimetype.startswith(self.DIFF_DATA_MIMETYPE_BASE + "+"):
            return self._get_diff_data(request, mimetype, *args, **kwargs)
        else:
            return super(FileDiffResource, self).get(request, *args, **kwargs)

    def _get_patch(self, request, *args, **kwargs):
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            filediff = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        resp = HttpResponse(filediff.diff, mimetype='text/x-patch')
        filename = '%s.patch' % urllib_quote(filediff.source_file)
        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp

    def _get_diff_data(self, request, mimetype, *args, **kwargs):
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            filediff = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        highlighting = request.GET.get('syntax-highlighting', False)

        files = get_diff_files(filediff.diffset, filediff, request=request)
        populate_diff_chunks(files, highlighting, request=request)

        if not files:
            # This may not be the right error here.
            return DOES_NOT_EXIST

        assert len(files) == 1
        f = files[0]

        payload = {
            'diff_data': {
                'binary': f['binary'],
                'chunks': f['chunks'],
                'num_changes': f['num_changes'],
                'changed_chunk_indexes': f['changed_chunk_indexes'],
                'new_file': f['newfile'],
            }
        }

        # XXX: Kind of a hack.
        api_format = mimetype.split('+')[-1]

        resp = WebAPIResponse(request, payload, api_format=api_format)
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp

filediff_resource = FileDiffResource()


class ChangeResource(WebAPIResource):
    """Provides information on a change made to a public review request.

    A change includes, optionally, text entered by the user describing the
    change, and also includes a list of fields that were changed on the
    review request.

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
        'text': {
            'type': str,
            'description': 'The description of the change written by the '
                           'submitter.'
        },
        'timestamp': {
            'type': str,
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

        for field, data in fields_changed.iteritems():
            if field in ('screenshot_captions', 'file_captions'):
                fields_changed[field] = [
                    {
                        'old': data[pk]['old'][0],
                        'new': data[pk]['new'][0],
                        'screenshot': get_object_cached(Screenshot, pk),
                    }
                    for pk, values in data.iteritems()
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
        review_request = review_request_resource.get_object(
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


class DiffResource(WebAPIResource):
    """Provides information on a collection of complete diffs.

    Each diff contains individual per-file diffs as child resources.
    A diff is revisioned, and more than one can be associated with any
    particular review request.
    """
    model = DiffSet
    name = 'diff'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the diff.',
        },
        'name': {
            'type': str,
            'description': 'The name of the diff, usually the filename.',
        },
        'revision': {
            'type': int,
            'description': 'The revision of the diff. Starts at 1 for public '
                           'diffs. Draft diffs may be at 0.',
        },
        'timestamp': {
            'type': str,
            'description': 'The date and time that the diff was uploaded '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'repository': {
            'type': 'reviewboard.webapi.resources.RepositoryResource',
            'description': 'The repository that the diff is applied against.',
        },
        'basedir': {
                'type': str,
                'description': 'The base directory that will prepended to '
                               'all paths in the diff. This is needed for '
                               'some types of repositories. The directory '
                               'must be between the root of the repository '
                               'and the top directory referenced in the '
                               'diff paths.',
        },
        'base_commit_id': {
            'type': str,
            'description': 'The ID/revision this change is built upon. '
                           'If using a parent diff, then this is the base '
                           'for that diff. This may not be provided for all '
                           'diffs or repository types, depending on how the '
                           'diff was uploaded.',
        },
    }
    item_child_resources = [filediff_resource]

    allowed_methods = ('GET', 'POST')

    uri_object_key = 'diff_revision'
    model_object_key = 'revision'
    model_parent_key = 'history'
    last_modified_field = 'timestamp'

    allowed_item_mimetypes = WebAPIResource.allowed_item_mimetypes + [
        'text/x-patch',
    ]

    def get_queryset(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            raise self.model.DoesNotExist

        return self.model.objects.filter(
            history__review_request=review_request)

    def get_parent_object(self, diffset):
        history = diffset.history

        if history:
            return history.review_request.get()
        else:
            # This isn't in a history yet. It's part of a draft.
            return diffset.review_request_draft.get().review_request

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        review_request = diffset.history.review_request.get()
        return review_request.is_accessible_by(request.user)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    def get_list(self, *args, **kwargs):
        """Returns the list of public diffs on the review request.

        Each diff has a revision and list of per-file diffs associated with it.
        """
        try:
            return super(DiffResource, self).get_list(*args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the information or contents on a particular diff.

        The output varies by mimetype.

        If :mimetype:`application/json` or :mimetype:`application/xml` is
        used, then the fields for the diff are returned, like with any other
        resource.

        If :mimetype:`text/x-patch` is used, then the actual diff file itself
        is returned. This diff should be as it was when uploaded originally,
        with potentially some extra SCM-specific headers stripped. The
        contents will contain that of all per-file diffs that make up this
        diff.
        """
        mimetype = get_http_requested_mimetype(request,
                                               self.allowed_item_mimetypes)

        if mimetype == 'text/x-patch':
            return self._get_patch(request, *args, **kwargs)
        else:
            return super(DiffResource, self).get(request, *args, **kwargs)

    def _get_patch(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            diffset = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        tool = review_request.repository.get_scmtool()
        data = tool.get_parser('').raw_diff(diffset)

        resp = HttpResponse(data, mimetype='text/x-patch')

        if diffset.name == 'diff':
            filename = 'bug%s.patch' % \
                       review_request.bugs_closed.replace(',', '_')
        else:
            filename = diffset.name

        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, diffset.timestamp)

        return resp

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            REPO_FILE_NOT_FOUND, INVALID_FORM_DATA,
                            DIFF_EMPTY, DIFF_TOO_BIG)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The main diff to upload.',
            },
        },
        optional={
            'basedir': {
                'type': str,
                'description': 'The base directory that will prepended to '
                               'all paths in the diff. This is needed for '
                               'some types of repositories. The directory '
                               'must be between the root of the repository '
                               'and the top directory referenced in the '
                               'diff paths.',
            },
            'parent_diff_path': {
                'type': file,
                'description': 'The optional parent diff to upload.',
            },
            'base_commit_id': {
                'type': str,
                'description': 'The ID/revision this change is built upon. '
                               'If using a parent diff, then this is the base '
                               'for that diff. This may not be provided for '
                               'all diffs or repository types, depending on '
                               'how the diff was uploaded.',
            },
        }
    )
    def create(self, request, *args, **kwargs):
        """Creates a new diff by parsing an uploaded diff file.

        This will implicitly create the new Review Request draft, which can
        be updated separately and then published.

        This accepts a unified diff file, validates it, and stores it along
        with the draft of a review request. The new diff will have a revision
        of 0.

        A parent diff can be uploaded along with the main diff. A parent diff
        is a diff based on an existing commit in the repository, which will
        be applied before the main diff. The parent diff will not be included
        in the diff viewer. It's useful when developing a change based on a
        branch that is not yet committed. In this case, a parent diff of the
        parent branch would be provided along with the diff of the new commit,
        and only the new commit will be shown.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The main diff's name and
        content would be stored in the ``path`` field. If a parent diff is
        provided, its name and content would be stored in the
        ``parent_diff_path`` field.

        An example of this would be::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.diff"

            <Unified Diff Content Here>
            -- SoMe BoUnDaRy --
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return _no_access_error(request.user)

        form_data = request.POST.copy()
        form = UploadDiffForm(review_request, form_data, request.FILES,
                              request=request)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': _get_form_errors(form),
            }

        try:
            diffset = form.create(request.FILES['path'],
                                  request.FILES.get('parent_diff_path'))
        except FileNotFoundError, e:
            return REPO_FILE_NOT_FOUND, {
                'file': e.path,
                'revision': unicode(e.revision)
            }
        except EmptyDiffError, e:
            return DIFF_EMPTY
        except DiffTooBigError, e:
            return DIFF_TOO_BIG, {
                'reason': str(e),
                'max_size': e.max_diff_size,
            }
        except Exception, e:
            # This could be very wrong, but at least they'll see the error.
            # We probably want a new error type for this.
            logging.error("Error uploading new diff: %s", e, exc_info=1,
                          request=request)

            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)]
                }
            }

        discarded_diffset = None

        try:
            draft = review_request.draft.get()

            if draft.diffset and draft.diffset != diffset:
                discarded_diffset = draft.diffset
        except ReviewRequestDraft.DoesNotExist:
            try:
                draft = ReviewRequestDraftResource.prepare_draft(
                    request, review_request)
            except PermissionDenied:
                return _no_access_error(request.user)

        draft.diffset = diffset

        # We only want to add default reviewers the first time.  Was bug 318.
        if review_request.diffset_history.diffsets.count() == 0:
            draft.add_default_reviewers();

        draft.save()

        if discarded_diffset:
            discarded_diffset.delete()

        # E-mail gets sent when the draft is saved.

        return 201, {
            self.item_result_key: diffset,
        }

diffset_resource = DiffResource()


class BaseWatchedObjectResource(WebAPIResource):
    """A base resource for objects watched by a user."""
    watched_resource = None
    uri_object_key = 'watched_obj_id'
    profile_field = None
    star_function = None
    unstar_function = None

    allowed_methods = ('GET', 'POST', 'DELETE')

    @property
    def uri_object_key_regex(self):
        return self.watched_resource.uri_object_key_regex

    def get_queryset(self, request, username, local_site_name=None,
                     *args, **kwargs):
        try:
            local_site = _get_local_site(local_site_name)
            if local_site:
                user = local_site.users.get(username=username)
                profile = user.get_profile()
            else:
                profile = Profile.objects.get(user__username=username)

            q = self.watched_resource.get_queryset(
                    request, local_site_name=local_site_name, *args, **kwargs)
            q = q.filter(starred_by=profile)
            return q
        except Profile.DoesNotExist:
            return self.watched_resource.model.objects.none()

    @webapi_check_login_required
    def get(self, request, watched_obj_id, *args, **kwargs):
        try:
            q = self.get_queryset(request, *args, **kwargs)
            obj = self.get_watched_object(q, watched_obj_id, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return HttpResponseRedirect(
            self.watched_resource.get_href(obj, request, *args, **kwargs))

    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST)
    def get_list(self, request, *args, **kwargs):
        # TODO: Handle pagination and ?counts-only=1
        try:
            objects = [
                self.serialize_object(obj)
                for obj in self.get_queryset(request, is_list=True, *args, **kwargs)
            ]

            return 200, {
                self.list_result_key: objects,
            }
        except User.DoesNotExist:
            return DOES_NOT_EXIST

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(required={
        'object_id': {
            'type': str,
            'description': 'The ID of the object to watch.',
        },
    })
    def create(self, request, object_id, *args, **kwargs):
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.watched_resource.uri_object_key] = object_id
            obj = self.watched_resource.get_object(request, *args, **obj_kwargs)
            user = user_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not user_resource.has_modify_permissions(request, user,
                                                    *args, **kwargs):
            return _no_access_error(request.user)

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)
        star = getattr(profile, self.star_function)
        star(obj)

        return 201, {
            self.item_result_key: obj,
        }

    @webapi_check_local_site
    @webapi_login_required
    def delete(self, request, watched_obj_id, *args, **kwargs):
        try:
            obj_kwargs = kwargs.copy()
            obj_kwargs[self.watched_resource.uri_object_key] = watched_obj_id
            obj = self.watched_resource.get_object(request, *args, **obj_kwargs)
            user = user_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not user_resource.has_modify_permissions(request, user,
                                                   *args, **kwargs):
            return _no_access_error(request.user)

        profile, profile_is_new = \
            Profile.objects.get_or_create(user=request.user)

        if not profile_is_new:
            unstar = getattr(profile, self.unstar_function)
            unstar(obj)

        return 204, {}

    def serialize_object(self, obj, *args, **kwargs):
        return {
            'id': obj.pk,
            self.item_result_key: obj,
        }

    def get_watched_object(self, queryset, obj_id, *args, **kwargs):
        return queryset.get(pk=obj_id)


class WatchedReviewGroupResource(BaseWatchedObjectResource):
    """Lists and manipulates entries for review groups watched by the user.

    These are groups that the user has starred in their Dashboard.
    This resource can be used for listing existing review groups and adding
    new review groups to watch.

    Each item in the resource is an association between the user and the
    review group. The entries in the list are not the review groups themselves,
    but rather an entry that represents this association by listing the
    association's ID (which can be used for removing the association) and
    linking to the review group.
    """
    name = 'watched_review_group'
    uri_name = 'review-groups'
    profile_field = 'starred_groups'
    star_function = 'star_review_group'
    unstar_function = 'unstar_review_group'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return review_group_resource

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get(self, *args, **kwargs):
        """Returned an :http:`302` pointing to the review group being
        watched.

        Rather than returning a body with the entry, performing an HTTP GET
        on this resource will redirect the client to the actual review group
        being watched.

        Clients must properly handle :http:`302` and expect this redirect
        to happen.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of watched review groups.

        Each entry in the list consists of a numeric ID that represents the
        entry for the watched review group. This is not necessarily the ID
        of the review group itself. It's used for looking up the resource
        of the watched item so that it can be removed.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def create(self, *args, **kwargs):
        """Marks a review group as being watched.

        The ID of the review group must be passed as ``object_id``, and will
        store that review group in the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def delete(self, *args, **kwargs):
        """Deletes a watched review group entry.

        This is the same effect as unstarring a review group. It does
        not actually delete the review group, just the entry in the list.
        """
        pass

watched_review_group_resource = WatchedReviewGroupResource()


class WatchedReviewRequestResource(BaseWatchedObjectResource):
    """Lists and manipulates entries for review requests watched by the user.

    These are requests that the user has starred in their Dashboard.
    This resource can be used for listing existing review requests and adding
    new review requests to watch.

    Each item in the resource is an association between the user and the
    review request. The entries in the list are not the review requests
    themselves, but rather an entry that represents this association by
    listing the association's ID (which can be used for removing the
    association) and linking to the review request.
    """
    name = 'watched_review_request'
    uri_name = 'review-requests'
    profile_field = 'starred_review_requests'
    star_function = 'star_review_request'
    unstar_function = 'unstar_review_request'

    @property
    def watched_resource(self):
        """Return the watched resource.

        This is implemented as a property in order to work around
        a circular reference issue.
        """
        return review_request_resource

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get(self, *args, **kwargs):
        """Returned an :http:`302` pointing to the review request being
        watched.

        Rather than returning a body with the entry, performing an HTTP GET
        on this resource will redirect the client to the actual review request
        being watched.

        Clients must properly handle :http:`302` and expect this redirect
        to happen.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of watched review requests.

        Each entry in the list consists of a numeric ID that represents the
        entry for the watched review request. This is not necessarily the ID
        of the review request itself. It's used for looking up the resource
        of the watched item so that it can be removed.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def create(self, *args, **kwargs):
        """Marks a review request as being watched.

        The ID of the review group must be passed as ``object_id``, and will
        store that review group in the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseWatchedObjectResource)
    def delete(self, *args, **kwargs):
        """Deletes a watched review request entry.

        This is the same effect as unstarring a review request. It does
        not actually delete the review request, just the entry in the list.
        """
        pass

    def serialize_object(self, obj, *args, **kwargs):
        return {
            'id': obj.display_id,
            self.item_result_key: obj,
        }

    def get_watched_object(self, queryset, obj_id, local_site_name=None,
                           *args, **kwargs):
        if local_site_name:
            return queryset.get(local_id=obj_id)
        else:
            return queryset.get(pk=obj_id)

watched_review_request_resource = WatchedReviewRequestResource()


class WatchedResource(WebAPIResource):
    """
    Links to all Watched Items resources for the user.

    This is more of a linking resource rather than a data resource, much like
    the root resource is. The sole purpose of this resource is for easy
    navigation to the more specific Watched Items resources.
    """
    name = 'watched'
    singleton = True

    list_child_resources = [
        watched_review_group_resource,
        watched_review_request_resource,
    ]

    @webapi_check_login_required
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of Watched Items resources.

        Unlike most resources, the result of this resource is just a list of
        links, rather than any kind of data. It exists in order to index the
        more specific Watched Review Groups and Watched Review Requests
        resources.
        """
        return super(WatchedResource, self).get_list(request, *args, **kwargs)

watched_resource = WatchedResource()


class UserResource(WebAPIResource, DjbletsUserResource):
    """
    Provides information on registered users.

    If a user's profile is private, the fields ``email``, ``first_name``,
    ``last_name``, and ``fullname`` will be omitted for non-staff users.
    """
    item_child_resources = [
        watched_resource,
    ]

    fields = dict({
        'avatar_url': {
            'type': str,
            'description': 'The URL for an avatar representing the user.',
        },
    }, **DjbletsUserResource.fields)

    hidden_fields = ('email', 'first_name', 'last_name', 'fullname')

    def get_etag(self, request, obj, *args, **kwargs):
        if obj.is_profile_visible(request.user):
            return self.generate_etag(obj, self.fields.iterkeys(), request)
        else:
            return self.generate_etag(obj, [
                field
                for field in self.fields.iterkeys()
                if field not in self.hidden_fields
            ], request)

    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        search_q = request.GET.get('q', None)

        local_site = _get_local_site(local_site_name)
        if local_site:
            query = local_site.users.filter(is_active=True)
        else:
            query = self.model.objects.filter(is_active=True)

        if search_q:
            q = Q(username__istartswith=search_q)

            if request.GET.get('fullname', None):
                q = q | (Q(first_name__istartswith=search_q) |
                         Q(last_name__istartswith=search_q))

            query = query.filter(q)

        return query

    def serialize_object(self, obj, request=None, *args, **kwargs):
        data = super(UserResource, self).serialize_object(
            obj, request=request, *args, **kwargs)

        if request:
            # Hide user info from anonymous users and non-staff users (if
            # his/her profile is private).
            if not obj.is_profile_visible(request.user):
                for field in self.hidden_fields:
                    del data[field]

        return data

    def serialize_url_field(self, user, **kwargs):
        return local_site_reverse('user', kwargs['request'],
                                  kwargs={'username': user.username})

    def serialize_avatar_url_field(self, user, request=None, **kwargs):
        return get_gravatar_url(request, user)

    def has_access_permissions(self, request, *args, **kwargs):
        return True

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'q': {
                'type': str,
                'description': 'The string that the username (or the first '
                               'name or last name when using ``fullname``) '
                               'must start with in order to be included in '
                               'the list. This is case-insensitive.',
            },
            'fullname': {
                'type': bool,
                'description': 'Specifies whether ``q`` should also match '
                               'the beginning of the first name or last name.'
            },
        },
        allow_unknown=True
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users on the site.

        This includes only the users who have active accounts on the site.
        Any account that has been disabled (for inactivity, spam reasons,
        or anything else) will be excluded from the list.

        The list of users can be filtered down using the ``q`` and
        ``fullname`` parameters.

        Setting ``q`` to a value will by default limit the results to
        usernames starting with that value. This is a case-insensitive
        comparison.

        If ``fullname`` is set to ``1``, the first and last names will also be
        checked along with the username. ``fullname`` is ignored if ``q``
        is not set.

        For example, accessing ``/api/users/?q=bo&fullname=1`` will list
        any users with a username, first name or last name starting with
        ``bo``.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieve information on a registered user.

        This mainly returns some basic information (username, full name,
        e-mail address) and links to that user's root Watched Items resource,
        which is used for keeping track of the groups and review requests
        that the user has "starred".
        """
        pass

user_resource = UserResource()


class ReviewGroupUserResource(UserResource):
    """Provides information on users that are members of a review group."""
    allowed_methods = ('GET', 'POST', 'DELETE')

    def get_queryset(self, request, group_name, local_site_name=None,
                     *args, **kwargs):
        group = Group.objects.get(name=group_name,
                                  local_site__name=local_site_name)
        return group.users.all()

    def has_access_permissions(self, request, user, *args, **kwargs):
        group = review_group_resource.get_object(request, *args, **kwargs)
        return group.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        group = review_group_resource.get_object(request, *args, **kwargs)
        return group.is_accessible_by(request.user)

    def has_delete_permissions(self, request, user, *args, **kwargs):
        group = review_group_resource.get_object(request, *args, **kwargs)
        return group.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_USER,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(required={
        'username': {
            'type': str,
            'description': 'The user to add to the group.',
        },
    })
    def create(self, request, username, *args, **kwargs):
        """Adds a user to a review group."""
        try:
            group = review_group_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_group_resource.has_modify_permissions(request, group):
            return _no_access_error(request.user)

        local_site = _get_local_site(kwargs.get('local_site_name', None))

        try:
            user = User.objects.get(username=username, local_site=local_site)
        except ObjectDoesNotExist:
            return INVALID_USER

        group.users.add(user)

        return 201, {
            self.item_result_key: user,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_USER,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Removes a user from a review group."""
        try:
            group = review_group_resource.get_object(request, *args, **kwargs)
            user = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_group_resource.has_modify_permissions(request, group):
            return _no_access_error(request.user)

        group.users.remove(user)

        return 204, {}

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users belonging to a specific review group.

        This includes only the users who have active accounts on the site.
        Any account that has been disabled (for inactivity, spam reasons,
        or anything else) will be excluded from the list.

        The list of users can be filtered down using the ``q`` and
        ``fullname`` parameters.

        Setting ``q`` to a value will by default limit the results to
        usernames starting with that value. This is a case-insensitive
        comparison.

        If ``fullname`` is set to ``1``, the first and last names will also be
        checked along with the username. ``fullname`` is ignored if ``q``
        is not set.

        For example, accessing ``/api/users/?q=bo&fullname=1`` will list
        any users with a username, first name or last name starting with
        ``bo``.
        """
        pass

review_group_user_resource = ReviewGroupUserResource()


class ReviewGroupResource(WebAPIResource):
    """Provides information on review groups.

    Review groups are groups of users that can be listed as an intended
    reviewer on a review request.

    Review groups cannot be created or modified through the API.
    """
    model = Group
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the review group.',
        },
        'name': {
            'type': str,
            'description': 'The short name of the group, used in the '
                           'reviewer list and the Dashboard.',
        },
        'display_name': {
            'type': str,
            'description': 'The human-readable name of the group, sometimes '
                           'used as a short description.',
        },
        'invite_only': {
            'type': bool,
            'description': 'Whether or not the group is invite-only. An '
                           'invite-only group is only accessible by members '
                           'of the group.',
        },
        'mailing_list': {
            'type': str,
            'description': 'The e-mail address that all posts on a review '
                           'group are sent to.',
        },
        'url': {
            'type': str,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
        },
        'visible': {
            'type': bool,
            'description': 'Whether or not the group is visible to users '
                           'who are not members. This does not prevent users '
                           'from accessing the group if they know it, though.',
        },
    }

    item_child_resources = [
        review_group_user_resource
    ]

    uri_object_key = 'group_name'
    uri_object_key_regex = '[A-Za-z0-9_-]+'
    model_object_key = 'name'
    autogenerate_etags = True
    mimetype_list_resource_name = 'review-groups'
    mimetype_item_resource_name = 'review-group'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def has_delete_permissions(self, request, group, *args, **kwargs):
        return group.is_mutable_by(request.user)

    def has_modify_permissions(self, request, group):
        return group.is_mutable_by(request.user)

    def get_queryset(self, request, is_list=False, local_site_name=None,
                     *args, **kwargs):
        search_q = request.GET.get('q', None)
        local_site = _get_local_site(local_site_name)

        if is_list:
            query = self.model.objects.accessible(request.user,
                                                  local_site=local_site)
        else:
            query = self.model.objects.filter(local_site=local_site)

        if search_q:
            q = Q(name__istartswith=search_q)

            if request.GET.get('displayname', None):
                q = q | Q(display_name__istartswith=search_q)

            query = query.filter(q)

        return query

    def serialize_url_field(self, group, **kwargs):
        return group.get_absolute_url()

    def has_access_permissions(self, request, group, *args, **kwargs):
        return group.is_accessible_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieve information on a review group.

        Some basic information on the review group is provided, including
        the name, description, and mailing list (if any) that e-mails to
        the group are sent to.

        The group links to the list of users that are members of the group.
        """
        pass

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'q': {
                'type': str,
                'description': 'The string that the group name (or the  '
                               'display name when using ``displayname``) '
                               'must start with in order to be included in '
                               'the list. This is case-insensitive.',
            },
            'displayname': {
                'type': bool,
                'description': 'Specifies whether ``q`` should also match '
                               'the beginning of the display name.'
            },
        },
        allow_unknown=True
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of review groups on the site.

        The list of review groups can be filtered down using the ``q`` and
        ``displayname`` parameters.

        Setting ``q`` to a value will by default limit the results to
        group names starting with that value. This is a case-insensitive
        comparison.

        If ``displayname`` is set to ``1``, the display names will also be
        checked along with the username. ``displayname`` is ignored if ``q``
        is not set.

        For example, accessing ``/api/groups/?q=dev&displayname=1`` will list
        any groups with a name or display name starting with ``dev``.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(GROUP_ALREADY_EXISTS, INVALID_FORM_DATA,
                            INVALID_USER, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required={
            'name': {
                'type': str,
                'description': 'The name of the group.',
            },
            'display_name': {
                'type': str,
                'description': 'The human-readable name of the group.',
            },
        },
        optional={
            'mailing_list': {
                'type': str,
                'description': 'The e-mail address that all posts on a review '
                               'group are sent to.',
            },
            'visible': {
                'type': bool,
                'description': 'Whether or not the group is visible to users '
                               'who are not members. The default is true.',
            },
            'invite_only': {
                'type': bool,
                'description': 'Whether or not the group is invite-only. '
                               'The default is false.',
            },
        }
    )
    def create(self, request, name, display_name, mailing_list=None,
               visible=True, invite_only=False, local_site_name=None,
               *args, **kargs):
        """Creates a new review group.

        This will create a brand new review group with the given name
        and display name. The group will be public by default, unless
        specified otherwise.
        """
        local_site = _get_local_site(local_site_name)

        if not self.model.objects.can_create(request.user, local_site):
            return _no_access_error(request.user)

        group, is_new = self.model.objects.get_or_create(
            name=name,
            local_site=local_site,
            defaults={
                'display_name': display_name,
                'mailing_list': mailing_list or '',
                'visible': bool(visible),
                'invite_only': bool(invite_only),
            })

        if not is_new:
            return GROUP_ALREADY_EXISTS

        return 201, {
            self.item_result_key: group,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            GROUP_ALREADY_EXISTS, NOT_LOGGED_IN,
                            PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'name': {
                'type': str,
                'description': 'The new name for the group.',
            },
            'display_name': {
                'type': str,
                'description': 'The human-readable name of the group.',
            },
            'mailing_list': {
                'type': str,
                'description': 'The e-mail address that all posts on a review '
                               'group are sent to.',
            },
            'visible': {
                'type': bool,
                'description': 'Whether or not the group is visible to users '
                               'who are not members.',
            },
            'invite_only': {
                'type': bool,
                'description': 'Whether or not the group is invite-only.'
            },
        }
    )
    def update(self, request, name=None, *args, **kwargs):
        """Updates an existing review group.

        All the fields of a review group can be modified, including the
        name, so long as it doesn't conflict with another review group.
        """
        try:
            group = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, group):
            return _no_access_error(request.user)

        if name is not None and name != group.name:
            # If we're changing the group name, make sure that group doesn't
            # exist.
            local_site = _get_local_site(kwargs.get('local_site_name', None))

            if self.model.objects.filter(name=name,
                                         local_site=local_site).count():
                return GROUP_ALREADY_EXISTS

            group.name = name

        for field in ("display_name", "mailing_list", "visible",
                      "invite_only"):
            val = kwargs.get(field, None)

            if val is not None:
                setattr(group, field, val)

        group.save()

        return 200, {
            self.item_result_key: group,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a review group.

        This will disassociate the group from all review requests previously
        targetting the group, and permanently delete the group.

        It is best to only delete empty, unused groups, and to instead
        change a group to not be visible if it's on longer needed.
        """
        try:
            group = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, group):
            return _no_access_error(request.user)

        group.delete()

        return 204, {}

review_group_resource = ReviewGroupResource()


class HostingServiceAccountResource(WebAPIResource):
    """Provides information and allows linking of hosting service accounts.

    The list of accounts tied to hosting services can be retrieved, and new
    accounts can be linked through an HTTP POST.
    """
    name = 'hosting_service_account'
    model = HostingServiceAccount
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the hosting service account.',
        },
        'username': {
            'type': str,
            'description': 'The username of the account.',
        },
        'service': {
            'type': str,
            'description': 'The ID of the service this account is on.',
        },
    }
    uri_object_key = 'account_id'
    autogenerate_etags = True

    allowed_methods = ('GET', 'POST',)

    @webapi_check_login_required
    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        local_site = _get_local_site(local_site_name)
        return self.model.objects.accessible(visible_only=True,
                                             local_site=local_site)

    def has_access_permissions(self, request, account, *args, **kwargs):
        return account.is_accessible_by(request.user)

    def has_modify_permissions(self, request, account, *args, **kwargs):
        return account.is_mutable_by(request.user)

    def has_delete_permissions(self, request, account, *args, **kwargs):
        return account.is_mutable_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of accounts on the server.

        This will only list visible accounts. Any account that the
        administrator has hidden will be excluded from the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular account.

        This will only return very basic information on the account.
        Authentication information is not provided.
        """
        pass

    def serialize_service_field(self, obj, **kwargs):
        return obj.service_name

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(BAD_HOST_KEY, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED, REPO_AUTHENTICATION_ERROR,
                            SERVER_CONFIG_ERROR, UNVERIFIED_HOST_CERT,
                            UNVERIFIED_HOST_KEY)
    @webapi_request_fields(
        required={
            'username': {
                'type': str,
                'description': 'The username on the account.',
            },
            'service_id': {
                'type': str,
                'description': 'The registered ID of the service for the '
                               'account.',
            },
        },
        optional={
            'hosting_url': {
                'type': str,
                'description': 'The hosting URL on the account, if the hosting '
                               'service is self-hosted.',
            },
            'password': {
                'type': str,
                'description': 'The password on the account, if the hosting '
                               'service needs it.',
            },
        }
    )
    def create(self, request, username, service_id, password=None,
               hosting_url=None, local_site_name=None, *args, **kwargs):
        local_site = _get_local_site(local_site_name)

        if not HostingServiceAccount.objects.can_create(request.user,
                                                        local_site):
            return _no_access_error(request.user)

        # Validate the service.
        service = get_hosting_service(service_id)

        if not service:
            return INVALID_FORM_DATA, {
                'fields': {
                    'service': ['This is not a valid service name'],
                }
            }

        if service.self_hosted and not hosting_url:
            return INVALID_FORM_DATA, {
                'fields': {
                    'hosting_url': ['This field is required'],
                }
            }

        account = HostingServiceAccount(service_name=service_id,
                                        username=username,
                                        hosting_url=hosting_url,
                                        local_site=local_site)
        service = account.service

        if service.needs_authorization:
            try:
                service.authorize(request, username, password, hosting_url,
                                  local_site_name)
            except AuthorizationError, e:
                return HOSTINGSVC_AUTH_ERROR, {
                    'reason': str(e),
                }

        service.save()

        return 201, {
            self.item_result_key: account,
        }

hosting_service_account_resource = HostingServiceAccountResource()


class RepositoryInfoResource(WebAPIResource):
    """Provides server-side information on a repository.

    Some repositories can return custom server-side information.
    This is not available for all types of repositories. The information
    will be specific to that type of repository.
    """
    name = 'info'
    singleton = True
    allowed_methods = ('GET',)
    mimetype_item_resource_name = 'repository-info'

    @webapi_check_local_site
    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST, REPO_NOT_IMPLEMENTED,
                            REPO_INFO_ERROR)
    def get(self, request, *args, **kwargs):
        """Returns repository-specific information from a server."""
        try:
            repository = repository_resource.get_object(request, *args,
                                                        **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            tool = repository.get_scmtool()

            return 200, {
                self.item_result_key: tool.get_repository_info()
            }
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED
        except:
            return REPO_INFO_ERROR

repository_info_resource = RepositoryInfoResource()


class RepositoryResource(WebAPIResource):
    """Provides information on a registered repository.

    Review Board has a list of known repositories, which can be modified
    through the site's administration interface. These repositories contain
    the information needed for Review Board to access the files referenced
    in diffs.
    """
    model = Repository
    name_plural = 'repositories'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the repository.',
        },
        'name': {
            'type': str,
            'description': 'The name of the repository.',
        },
        'path': {
            'type': str,
            'description': 'The main path to the repository, which is used '
                           'for communicating with the repository and '
                           'accessing files.',
        },
        'tool': {
            'type': str,
            'description': 'The name of the internal repository '
                           'communication class used to talk to the '
                           'repository. This is generally the type of the '
                           'repository.'
        }
    }
    uri_object_key = 'repository_id'
    item_child_resources = [repository_info_resource]
    autogenerate_etags = True

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    @webapi_check_login_required
    def get_queryset(self, request, local_site_name=None, *args, **kwargs):
        local_site = _get_local_site(local_site_name)
        return self.model.objects.accessible(request.user,
                                             visible_only=True,
                                             local_site=local_site)

    def serialize_tool_field(self, obj, **kwargs):
        return obj.tool.name

    def has_access_permissions(self, request, repository, *args, **kwargs):
        return repository.is_accessible_by(request.user)

    def has_modify_permissions(self, request, repository, *args, **kwargs):
        return repository.is_mutable_by(request.user)

    def has_delete_permissions(self, request, repository, *args, **kwargs):
        return repository.is_mutable_by(request.user)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Retrieves the list of repositories on the server.

        This will only list visible repositories. Any repository that the
        administrator has hidden will be excluded from the list.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Retrieves information on a particular repository.

        This will only return basic information on the repository.
        Authentication information, hosting details, and repository-specific
        information are not provided.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(BAD_HOST_KEY, INVALID_FORM_DATA, NOT_LOGGED_IN,
                            PERMISSION_DENIED, REPO_AUTHENTICATION_ERROR,
                            SERVER_CONFIG_ERROR, UNVERIFIED_HOST_CERT,
                            UNVERIFIED_HOST_KEY, REPO_INFO_ERROR)
    @webapi_request_fields(
        required={
            'name': {
                'type': str,
                'description': 'The human-readable name of the repository.',
            },
            'path': {
                'type': str,
                'description': 'The path to the repository.',
            },
            'tool': {
                'type': str,
                'description': 'The ID of the SCMTool to use.',
            },
        },
        optional={
            'bug_tracker': {
                'type': str,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
            },
            'encoding': {
                'type': str,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
            },
            'mirror_path': {
                'type': str,
                'description': 'An alternate path to the repository.',
            },
            'password': {
                'type': str,
                'description': 'The password used to access the repository.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
            },
            'raw_file_url': {
                'type': str,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
            },
            'trust_host': {
                'type': bool,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
            },
            'username': {
                'type': str,
                'description': 'The username used to access the repository.',
            },
        },
    )
    def create(self, request, name, path, tool, trust_host=False,
               bug_tracker=None, encoding=None, mirror_path=None,
               password=None, public=None, raw_file_url=None, username=None,
               local_site_name=None, *args, **kwargs):
        """Creates a repository.

        This will create a new repository that can immediately be used for
        review requests.

        The ``tool`` is a registered SCMTool ID. This must be known beforehand,
        and can be looked up in the Review Board administration UI.

        Before saving the new repository, the repository will be checked for
        access. On success, the repository will be created and this will
        return :http:`201`.

        In the event of an access problem (authentication problems,
        bad/unknown SSH key, or unknown certificate), an error will be
        returned and the repository information won't be updated. Pass
        ``trust_host=1`` to approve bad/unknown SSH keys or certificates.
        """
        local_site = _get_local_site(local_site_name)

        if not Repository.objects.can_create(request.user, local_site):
            return _no_access_error(request.user)

        try:
            scmtool = Tool.objects.get(name=tool)
        except Tool.DoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'tool': ['This is not a valid SCMTool'],
                }
            }

        cert = {}
        error_result = self._check_repository(scmtool.get_scmtool_class(),
                                              path, username, password,
                                              local_site, trust_host, cert,
                                              request)

        if error_result is not None:
            return error_result

        if public is None:
            public = True

        repository = Repository(
            name=name,
            path=path,
            mirror_path=mirror_path or '',
            raw_file_url=raw_file_url or '',
            username=username or '',
            password=password or '',
            tool=scmtool,
            bug_tracker=bug_tracker or '',
            encoding=encoding or '',
            public=public,
            local_site=local_site)

        if cert:
            repository.extra_data['cert'] = cert

        repository.save()

        return 201, {
            self.item_result_key: repository,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA, SERVER_CONFIG_ERROR,
                            BAD_HOST_KEY, UNVERIFIED_HOST_KEY,
                            UNVERIFIED_HOST_CERT, REPO_AUTHENTICATION_ERROR,
                            REPO_INFO_ERROR)
    @webapi_request_fields(
        optional={
            'bug_tracker': {
                'type': str,
                'description': 'The URL to a bug in the bug tracker for '
                               'this repository, with ``%s`` in place of the '
                               'bug ID.',
            },
            'encoding': {
                'type': str,
                'description': 'The encoding used for files in the '
                               'repository. This is an advanced setting '
                               'and should only be used if you absolutely '
                               'need it.',
            },
            'mirror_path': {
                'type': str,
                'description': 'An alternate path to the repository.',
            },
            'name': {
                'type': str,
                'description': 'The human-readable name of the repository.',
            },
            'password': {
                'type': str,
                'description': 'The password used to access the repository.',
            },
            'path': {
                'type': str,
                'description': 'The path to the repository.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not review requests on the '
                               'repository will be publicly accessible '
                               'by users on the site. The default is true.',
            },
            'raw_file_url': {
                'type': str,
                'description': "A URL mask used to check out a particular "
                               "file using HTTP. This is needed for "
                               "repository types that can't access files "
                               "natively. Use ``<revision>`` and "
                               "``<filename>`` in the URL in place of the "
                               "revision and filename parts of the path.",
            },
            'trust_host': {
                'type': bool,
                'description': 'Whether or not any unknown host key or '
                               'certificate should be accepted. The default '
                               'is false, in which case this will error out '
                               'if encountering an unknown host key or '
                               'certificate.',
            },
            'username': {
                'type': str,
                'description': 'The username used to access the repository.',
            },
            'archive_name': {
                'type': bool,
                'description': "Whether or not the (non-user-visible) name of "
                               "the repository should be changed so that it "
                               "(probably) won't conflict with any future "
                               "repository names.",
            },
        },
    )
    def update(self, request, trust_host=False, *args, **kwargs):
        """Updates a repository.

        This will update the information on a repository. If the path,
        username, or password has changed, Review Board will try again to
        verify access to the repository.

        In the event of an access problem (authentication problems,
        bad/unknown SSH key, or unknown certificate), an error will be
        returned and the repository information won't be updated. Pass
        ``trust_host=1`` to approve bad/unknown SSH keys or certificates.
        """
        try:
            repository = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, repository):
            return _no_access_error(request.user)

        for field in ('bug_tracker', 'encoding', 'mirror_path', 'name',
                      'password', 'path', 'public', 'raw_file_url',
                      'username'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(repository, field, value)

        # Only check the repository if the access information has changed.
        if 'path' in kwargs or 'username' in kwargs or 'password' in kwargs:
            cert = {}

            error_result = self._check_repository(
                repository.tool.get_scmtool_class(),
                repository.path,
                repository.username,
                repository.password,
                repository.local_site,
                trust_host,
                cert,
                request)

            if error_result is not None:
                return error_result

            if cert:
                repository.extra_data['cert'] = cert

        # If the API call is requesting that we archive the name, we'll give it
        # a name which won't overlap with future user-named repositories. This
        # should usually be used just before issuing a DELETE call, which will
        # set the visibility flag to False
        if kwargs.get('archive_name', False):
            # This should be sufficiently unlikely to create duplicates. time()
            # will use up a max of 8 characters, so we slice the name down to
            # make the result fit in 64 characters
            repository.name = 'ar:%s:%x' % (repository.name[:50], int(time()))

        repository.save()

        return 200, {
            self.item_result_key: repository,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        """Deletes a repository.

        The repository will not actually be deleted from the database, as
        that would also trigger a deletion of all review requests. Instead,
        it makes a repository as no longer being visible, which will hide it
        in the UIs and in the API.
        """
        try:
            repository = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, repository):
            return _no_access_error(request.user)

        if not repository.review_requests.exists():
            repository.delete()
        else:
            # We don't actually delete the repository. We instead just hide it.
            # Otherwise, all the review requests are lost. By marking it as not
            # visible, it'll be removed from the UI and from the list in the API.
            repository.visible = False
            repository.save()

        return 204, {}

    def _check_repository(self, scmtool_class, path, username, password,
                          local_site, trust_host, ret_cert, request):
        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        while 1:
            # Keep doing this until we have an error we don't want
            # to ignore, or it's successful.
            try:
                scmtool_class.check_repository(path, username, password,
                                               local_site_name)
                return None
            except RepositoryNotFoundError:
                return MISSING_REPOSITORY
            except BadHostKeyError, e:
                if trust_host:
                    try:
                        client = SSHClient(namespace=local_site_name)
                        client.replace_host_key(e.hostname,
                                                e.raw_expected_key,
                                                e.raw_key)
                    except IOError, e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': str(e),
                        }
                else:
                    return BAD_HOST_KEY, {
                        'hostname': e.hostname,
                        'expected_key': e.raw_expected_key.get_base64(),
                        'key': e.raw_key.get_base64(),
                    }
            except UnknownHostKeyError, e:
                if trust_host:
                    try:
                        client = SSHClient(namespace=local_site_name)
                        client.add_host_key(e.hostname, e.raw_key)
                    except IOError, e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': str(e),
                        }
                else:
                    return UNVERIFIED_HOST_KEY, {
                        'hostname': e.hostname,
                        'key': e.raw_key.get_base64(),
                    }
            except UnverifiedCertificateError, e:
                if trust_host:
                    try:
                        cert = scmtool_class.accept_certificate(
                            path, local_site_name)

                        if cert:
                            ret_cert.update(cert)
                    except IOError, e:
                        return SERVER_CONFIG_ERROR, {
                            'reason': str(e),
                        }
                else:
                    return UNVERIFIED_HOST_CERT, {
                        'certificate': {
                            'failures': e.certificate.failures,
                            'fingerprint': e.certificate.fingerprint,
                            'hostname': e.certificate.hostname,
                            'issuer': e.certificate.issuer,
                            'valid': {
                                'from': e.certificate.valid_from,
                                'until': e.certificate.valid_until,
                            },
                        },
                    }
            except AuthenticationError, e:
                if 'publickey' in e.allowed_types and e.user_key is None:
                    return MISSING_USER_KEY
                else:
                    return REPO_AUTHENTICATION_ERROR, {
                        'reason': str(e),
                    }
            except SSHError, e:
                logging.error('Got unexpected SSHError when checking '
                              'repository: %s'
                              % e, exc_info=1, request=request)
                return REPO_INFO_ERROR, {
                    'error': str(e),
                }
            except SCMError, e:
                logging.error('Got unexpected SCMError when checking '
                              'repository: %s'
                              % e, exc_info=1, request=request)
                return REPO_INFO_ERROR, {
                    'error': str(e),
                }
            except Exception, e:
                logging.error('Unknown error in checking repository %s: %s',
                              path, e, exc_info=1, request=request)

                # We should give something better, but I don't have anything.
                # This will at least give a HTTP 500.
                raise


repository_resource = RepositoryResource()


class BaseScreenshotResource(WebAPIResource):
    """A base resource representing screenshots."""
    model = Screenshot
    name = 'screenshot'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the screenshot.',
        },
        'caption': {
            'type': str,
            'description': "The screenshot's descriptive caption.",
        },
        'path': {
            'type': str,
            'description': "The path of the screenshot's image file, "
                           "relative to the media directory configured "
                           "on the Review Board server.",
        },
        'filename': {
            'type': str,
            'description': "The base file name of the screenshot's image.",
        },
        'review_url': {
            'type': str,
            'description': 'The URL to the review UI for this screenshot.',
        },
        'url': {
            'type': str,
            'description': "The URL of the screenshot file. If this is not "
                           "an absolute URL (for example, if it is just a "
                           "path), then it's relative to the Review Board "
                           "server's URL.",
        },
        'thumbnail_url': {
            'type': str,
            'description': "The URL of the screenshot's thumbnail file. "
                           "If this is not an absolute URL (for example, "
                           "if it is just a path), then it's relative to "
                           "the Review Board server's URL.",
        },
    }

    uri_object_key = 'screenshot_id'
    autogenerate_etags = True

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        review_request = review_request_resource.get_object(
            request, review_request_id, *args, **kwargs)

        q = Q(review_request=review_request)

        if not is_list:
            q = q | Q(inactive_review_request=review_request)

        if request.user == review_request.submitter:
            try:
                draft = review_request_draft_resource.get_object(
                    request, review_request_id, *args, **kwargs)

                q = q | Q(drafts=draft)

                if not is_list:
                    q = q | Q(inactive_drafts=draft)
            except ObjectDoesNotExist:
                pass

        return self.model.objects.filter(q)

    def serialize_path_field(self, obj, **kwargs):
        return obj.image.name

    def serialize_filename_field(self, obj, **kwargs):
        return os.path.basename(obj.image.name)

    def serialize_review_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    def serialize_url_field(self, obj, **kwargs):
        return obj.image.url

    def serialize_thumbnail_url_field(self, obj, **kwargs):
        return obj.get_thumbnail_url()

    def serialize_caption_field(self, obj, **kwargs):
        # We prefer 'caption' here, because when creating a new screenshot, it
        # won't be full of data yet (and since we're posting to screenshots/,
        # it doesn't hit DraftScreenshotResource). DraftScreenshotResource will
        # prefer draft_caption, in case people are changing an existing one.
        return obj.caption or obj.draft_caption

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The screenshot to upload.',
            },
        },
        optional={
            'caption': {
                'type': str,
                'description': 'The optional caption describing the '
                               'screenshot.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a new screenshot from an uploaded file.

        This accepts any standard image format (PNG, GIF, JPEG) and associates
        it with a draft of a review request.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The screenshot's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.png"

            <PNG content here>
            -- SoMe BoUnDaRy --
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return _no_access_error(request.user)

        form_data = request.POST.copy()
        form = UploadScreenshotForm(form_data, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': _get_form_errors(form),
            }

        try:
            screenshot = form.create(request.FILES['path'], review_request)
        except ValueError, e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)],
                },
            }

        return 201, {
            self.item_result_key: screenshot,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        optional={
            'caption': {
                'type': str,
                'description': 'The new caption for the screenshot.',
            },
        }
    )
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot in a draft. The caption, currently,
        is the only thing that can be updated.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return _no_access_error(request.user)

        try:
            screenshot = screenshot_resource.get_object(request, *args,
                                                        **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            review_request_draft_resource.prepare_draft(request,
                                                        review_request)
        except PermissionDenied:
            return _no_access_error(request.user)

        screenshot.draft_caption = caption
        screenshot.save()

        return 200, {
            self.item_result_key: screenshot,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            screenshot = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, screenshot, *args,
                                           **kwargs):
            return self._no_access_error(request.user)

        try:
            draft = review_request_draft_resource.prepare_draft(request,
                                                                review_request)
        except PermissionDenied:
            return _no_access_error(request.user)

        draft.screenshots.remove(screenshot)
        draft.inactive_screenshots.add(screenshot)
        draft.save()

        return 204, {}


class DraftScreenshotResource(BaseScreenshotResource):
    """Provides information on new screenshots being added to a draft of
    a review request.

    These are screenshots that will be shown once the pending review request
    draft is published.
    """
    name = 'draft_screenshot'
    uri_name = 'screenshots'
    model_parent_key = 'drafts'
    allowed_methods = ('GET', 'DELETE', 'POST', 'PUT',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        try:
            draft = review_request_draft_resource.get_object(
                request, review_request_id, *args, **kwargs)

            inactive_ids = \
                draft.inactive_screenshots.values_list('pk', flat=True)

            q = Q(review_request=review_request_id) | Q(drafts=draft)
            query = self.model.objects.filter(q)
            query = query.exclude(pk__in=inactive_ids)
            return query
        except ObjectDoesNotExist:
            return self.model.objects.none()

    def serialize_caption_field(self, obj, **kwargs):
        return obj.draft_caption or obj.caption

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the screenshot from the draft.

        This will remove the screenshot from the draft review request.
        This cannot be undone.

        This can be used to remove old screenshots that were previously
        shown, as well as newly added screenshots that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of draft screenshots.

        Each screenshot in this list is an uploaded screenshot that will
        be shown in the final review request. These may include newly
        uploaded screenshots or screenshots that were already part of the
        existing review request. In the latter case, existing screenshots
        are shown so that their captions can be added.
        """
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Returns the list of screenshots on this draft.

        This is a specialized version of the standard get_list function
        that uses this resource to serialize the children, in order to
        guarantee that we'll be able to identify them as screenshots that are
        part of the draft.
        """
        return WebAPIResponsePaginated(
            request,
            queryset=self.get_queryset(request, is_list=True,
                                       *args, **kwargs),
            results_key=self.list_result_key,
            serialize_object_func=
                lambda obj: self.serialize_object(obj, request=request,
                                                  *args, **kwargs),
            extra_data={
                'links': self.get_links(self.list_child_resources,
                                        request=request, *args, **kwargs),
            },
            **self.build_response_args(request))

draft_screenshot_resource = DraftScreenshotResource()


class BaseFileAttachmentResource(WebAPIResource):
    """A base resource representing file attachments."""
    model = FileAttachment
    name = 'file_attachment'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the file.',
        },
        'caption': {
            'type': str,
            'description': "The file's descriptive caption.",
        },
        'filename': {
            'type': str,
            'description': "The name of the file.",
        },
        'url': {
            'type': str,
            'description': "The URL of the file, for downloading purposes. "
                           "If this is not an absolute URL, then it's "
                           "relative to the Review Board server's URL.",
        },
        'icon_url': {
            'type': str,
            'description': 'The URL to a 24x24 icon representing this file.'
        },
        'thumbnail': {
            'type': str,
            'description': 'A thumbnail representing this file.',
        },
        'review_url': {
            'type': str,
            'description': 'The URL to a review UI for this file.',
        },
    }

    uri_object_key = 'file_attachment_id'
    autogenerate_etags = True

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        review_request = review_request_resource.get_object(
            request, review_request_id, *args, **kwargs)

        q = Q(review_request=review_request)

        if not is_list:
            q = q | Q(inactive_review_request=review_request)

        if request.user == review_request.submitter:
            try:
                draft = review_request_draft_resource.get_object(
                    request, review_request_id, *args, **kwargs)

                q = q | Q(drafts=draft)

                if not is_list:
                    q = q | Q(inactive_drafts=draft)
            except ObjectDoesNotExist:
                pass

        return self.model.objects.filter(q)

    def serialize_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    def serialize_caption_field(self, obj, **kwargs):
        # We prefer 'caption' here, because when creating a new screenshot, it
        # won't be full of data yet (and since we're posting to screenshots/,
        # it doesn't hit DraftFileAttachmentResource).
        # DraftFileAttachmentResource will prefer draft_caption, in case people
        # are changing an existing one.
        return obj.caption or obj.draft_caption

    def serialize_review_url_field(self, obj, **kwargs):
        if obj.review_ui:
            review_request = obj.get_review_request()
            if review_request.local_site_id:
                local_site_name = review_request.local_site.name
            else:
                local_site_name = None

            return local_site_reverse(
                'file_attachment', local_site_name=local_site_name,
                kwargs={
                    'review_request_id': review_request.display_id,
                    'file_attachment_id': obj.pk,
                })

        return ''

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, PERMISSION_DENIED,
                            INVALID_FORM_DATA, NOT_LOGGED_IN)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The file to upload.',
            },
        },
        optional={
            'caption': {
                'type': str,
                'description': 'The optional caption describing the '
                               'file.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a new file from a file attachment.

        This accepts any file type and associates it with a draft of a
        review request.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The file's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.zip"

            <Content here>
            -- SoMe BoUnDaRy --
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return _no_access_error(request.user)

        form_data = request.POST.copy()
        form = UploadFileForm(form_data, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': _get_form_errors(form),
            }

        try:
            file = form.create(request.FILES['path'], review_request)
        except ValueError, e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [str(e)],
                },
            }

        return 201, {
            self.item_result_key: file,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'caption': {
                'type': str,
                'description': 'The new caption for the file.',
            },
            'thumbnail': {
                'type': str,
                'description': 'The thumbnail data for the file.',
            },
        }
    )
    def update(self, request, caption=None, thumbnail=None, *args, **kwargs):
        """Updates the file's data.

        This allows updating the file in a draft. The caption, currently,
        is the only thing that can be updated.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return PERMISSION_DENIED

        try:
            file = file_attachment_resource.get_object(request, *args,
                                                       **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if caption is not None:
            try:
                review_request_draft_resource.prepare_draft(request,
                                                            review_request)
            except PermissionDenied:
                return _no_access_error(request.user)

            file.draft_caption = caption
            file.save()

        if thumbnail is not None:
            try:
                file.thumbnail = thumbnail
            except Exception, e:
                logging.error(
                    'Failed to store thumbnail for attachment %d: %s',
                    file.pk, e, request=request)
                return INVALID_FORM_DATA, {
                    'fields': {
                        'thumbnail': str(e),
                    }
                }

        return 200, {
            self.item_result_key: file,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            file_attachment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, file_attachment, *args,
                                           **kwargs):
            return self._no_access_error(request.user)

        try:
            draft = review_request_draft_resource.prepare_draft(request,
                                                                review_request)
        except PermissionDenied:
            return _no_access_error(request.user)

        draft.file_attachments.remove(file_attachment)
        draft.inactive_file_attachments.add(file_attachment)
        draft.save()

        return 204, {}


class DraftFileAttachmentResource(BaseFileAttachmentResource):
    """Provides information on new file attachments being added to a draft of
    a review request.

    These are files that will be shown once the pending review request
    draft is published.
    """
    name = 'draft_file_attachment'
    uri_name = 'file-attachments'
    model_parent_key = 'drafts'
    allowed_methods = ('GET', 'DELETE', 'POST', 'PUT',)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        try:
            draft = review_request_draft_resource.get_object(
                request, review_request_id, *args, **kwargs)

            inactive_ids = \
                draft.inactive_file_attachments.values_list('pk', flat=True)

            q = Q(review_request=review_request_id) | Q(drafts=draft)
            query = self.model.objects.filter(q)
            query = query.exclude(pk__in=inactive_ids)
            return query
        except ObjectDoesNotExist:
            return self.model.objects.none()

    def serialize_caption_field(self, obj, **kwargs):
        return obj.draft_caption or obj.caption

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(BaseFileAttachmentResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(BaseFileAttachmentResource)
    def delete(self, *args, **kwargs):
        """Deletes the file attachment from the draft.

        This will remove the file attachment from the draft review request.
        This cannot be undone.

        This can be used to remove old files that were previously
        shown, as well as newly added files that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of draft files.

        Each file attachment in this list is an uploaded file attachment that
        will be shown in the final review request. These may include newly
        file attachments or files that were already part of the
        existing review request. In the latter case, existing files
        are shown so that their captions can be added.
        """
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Returns the list of files on this draft.

        This is a specialized version of the standard get_list function
        that uses this resource to serialize the children, in order to
        guarantee that we'll be able to identify them as files that are
        part of the draft.
        """
        return WebAPIResponsePaginated(
            request,
            queryset=self.get_queryset(request, is_list=True,
                                       *args, **kwargs),
            results_key=self.list_result_key,
            serialize_object_func=
                lambda obj: self.serialize_object(obj, request=request,
                                                  *args, **kwargs),
            extra_data={
                'links': self.get_links(self.list_child_resources,
                                        request=request, *args, **kwargs),
            },
            **self.build_response_args(request))

draft_file_attachment_resource = DraftFileAttachmentResource()


class ReviewRequestDraftResource(WebAPIResource):
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
            'type': 'reviewboard.webapi.resources.ReviewRequestResource',
            'description': 'The review request that owns this draft.',
            'mutable': False,
        },
        'last_updated': {
            'type': str,
            'description': 'The date and time that the draft was last updated '
                           '(in YYYY-MM-DD HH:MM:SS format).',
            'mutable': False,
        },
        'branch': {
            'type': str,
            'description': 'The branch name.',
        },
        'bugs_closed': {
            'type': str,
            'description': 'The new list of bugs closed or referenced by this '
                           'change.',
        },
        'depends_on': {
            'type': ['reviewboard.webapi.resources.ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request depends on.',
        },
        'changedescription': {
            'type': str,
            'description': 'A custom description of what changes are being '
                           'made in this update. It often will be used to '
                           'describe the changes in the diff.',
        },
        'description': {
            'type': str,
            'description': 'The new review request description.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the draft is public. '
                           'This will always be false up until the time '
                           'it is first made public. At that point, the '
                           'draft is deleted.',
        },
        'summary': {
            'type': str,
            'description': 'The new review request summary.',
        },
        'target_groups': {
            'type': str,
            'description': 'A comma-separated list of review groups '
                           'that will be on the reviewer list.',
        },
        'target_people': {
            'type': str,
            'description': 'A comma-separated list of users that will '
                           'be on a reviewer list.',
        },
        'testing_done': {
            'type': str,
            'description': 'The new testing done text.',
        },
    }

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    item_child_resources = [
        draft_screenshot_resource,
        draft_file_attachment_resource
    ]

    @classmethod
    def prepare_draft(self, request, review_request):
        """Creates a draft, if the user has permission to."""
        if not review_request.is_mutable_by(request.user):
           raise PermissionDenied

        return ReviewRequestDraft.create(review_request)

    def get_queryset(self, request, review_request_id, *args, **kwargs):
        review_request = review_request_resource.get_object(
            request, review_request_id, *args, **kwargs)
        return self.model.objects.filter(review_request=review_request)

    def serialize_bugs_closed_field(self, obj, **kwargs):
        return obj.get_bug_list()

    def serialize_changedescription_field(self, obj, **kwargs):
        if obj.changedesc:
            return obj.changedesc.text
        else:
            return ''

    def serialize_status_field(self, obj, **kwargs):
        return status_to_string(obj.status)

    def serialize_public_field(self, obj, **kwargs):
        return False

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
                'type': str,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': str,
                'description': 'A comma-separated list of bug IDs.',
            },
            'depends_on': {
                'type': str,
                'description': 'The new list of dependencies of this review '
                               'request.',
            },
            'changedescription': {
                'type': str,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': str,
                'description': 'The new review request description.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
            'summary': {
                'type': str,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': str,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': str,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': str,
                'description': 'The new testing done text.',
            },
        },
    )
    def create(self, *args, **kwargs):
        """Creates a draft of a review request.

        If a draft already exists, this will just reuse the existing draft.
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
                'type': str,
                'description': 'The new branch name.',
            },
            'bugs_closed': {
                'type': str,
                'description': 'A comma-separated list of bug IDs.',
            },
            'depends_on': {
                'type': str,
                'description': 'The new list of dependencies of this review '
                               'request.',
            },
            'changedescription': {
                'type': str,
                'description': 'The change description for this update.',
            },
            'description': {
                'type': str,
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
                'type': str,
                'description': 'The new review request summary.',
            },
            'target_groups': {
                'type': str,
                'description': 'A comma-separated list of review groups '
                               'that will be on the reviewer list.',
            },
            'target_people': {
                'type': str,
                'description': 'A comma-separated list of users that will '
                               'be on a reviewer list.',
            },
            'testing_done': {
                'type': str,
                'description': 'The new testing done text.',
            },
        },
    )
    def update(self, request, always_save=False, local_site_name=None,
               *args, **kwargs):
        """Updates a draft of a review request.

        This will update the draft with the newly provided data.

        Most of the fields correspond to fields in the review request, but
        there is one special one, ``public``. When ``public`` is set to ``1``,
        the draft will be published, moving the new content to the
        Review Request itself, making it public, and sending out a notification
        (such as an e-mail) if configured on the server. The current draft will
        then be deleted.
        """
        try:
            review_request =  review_request_resource.get_object(
                request, local_site_name=local_site_name, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        try:
            draft = self.prepare_draft(request, review_request)
        except PermissionDenied:
            return _no_access_error(request.user)

        modified_objects = []
        invalid_fields = {}

        for field_name, field_info in self.fields.iteritems():
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

        if always_save or not invalid_fields:
            for obj in modified_objects:
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
                review_request_resource.get_object(request, *args, **kwargs)
            draft = review_request.draft.get()
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, draft, *args, **kwargs):
            return _no_access_error(request.user)

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

            local_site = _get_local_site(local_site_name)

            for value in values:
                # Prevent problems if the user leaves a trailing comma,
                # generating an empty value.
                if not value:
                    continue

                try:
                    if field_name == "target_groups":
                        obj = Group.objects.get((Q(name__iexact=value) |
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
                    user = backend.get_or_create_user(username, request)
                except:
                    pass

                if user:
                    return user

        return None

review_request_draft_resource = ReviewRequestDraftResource()


class BaseScreenshotCommentResource(BaseCommentResource):
    """A base resource for screenshot comments."""
    model = ScreenshotComment
    name = 'screenshot_comment'

    fields = dict({
        'id': {
            'type': int,
            'description': 'The numeric ID of the comment.',
        },
        'screenshot': {
            'type': 'reviewboard.webapi.resources.ScreenshotResource',
            'description': 'The screenshot the comment was made on.',
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
        'public': {
            'type': bool,
            'description': 'Whether or not the comment is part of a public '
                           'review.',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.UserResource',
            'description': 'The user who made the comment.',
        },
        'x': {
            'type': int,
            'description': 'The X location of the comment region on the '
                           'screenshot.',
        },
        'y': {
            'type': int,
            'description': 'The Y location of the comment region on the '
                           'screenshot.',
        },
        'w': {
            'type': int,
            'description': 'The width of the comment region on the '
                           'screenshot.',
        },
        'h': {
            'type': int,
            'description': 'The height of the comment region on the '
                           'screenshot.',
        },
        'thumbnail_url': {
            'type': str,
            'description': 'The URL to an image showing what was commented '
                           'on.',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'

    allowed_methods = ('GET',)

    def get_queryset(self, request, *args, **kwargs):
        review_request = \
            review_request_resource.get_object(request, *args, **kwargs)
        return self.model.objects.filter(Q(screenshot__review_request=review_request) |
                                         Q(screenshot__inactive_review_request=review_request),
                                         review__isnull=False)

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    def serialize_thumbnail_url_field(self, obj, **kwargs):
        return obj.get_image_url()

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment.

        This contains the comment text, time the comment was made,
        and the location of the comment region on the screenshot, amongst
        other information. It can be used to reconstruct the exact
        position of the comment for use as an overlay on the screenshot.
        """
        pass


class ScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on screenshots comments made on a review request.

    The list of comments cannot be modified from this resource. It's meant
    purely as a way to see existing comments that were made on a diff. These
    comments will span all public reviews.
    """
    model_parent_key = 'screenshot'
    uri_object_key = None

    def get_queryset(self, request, review_request_id, screenshot_id,
                     *args, **kwargs):
        q = super(ScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(screenshot=screenshot_id)
        return q

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of screenshot comments on a screenshot.

        This list of comments will cover all comments made on this
        screenshot from all reviews.
        """
        pass

screenshot_comment_resource = ScreenshotCommentResource()


class ReviewScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on screenshots comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id,
                     *args, **kwargs):
        q = super(ReviewScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        required = {
            'screenshot_id': {
                'type': int,
                'description': 'The ID of the screenshot being commented on.',
            },
            'x': {
                'type': int,
                'description': 'The X location for the comment.',
            },
            'y': {
                'type': int,
                'description': 'The Y location for the comment.',
            },
            'w': {
                'type': int,
                'description': 'The width of the comment region.',
            },
            'h': {
                'type': int,
                'description': 'The height of the comment region.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
        optional = {
            'issue_opened': {
                'type': bool,
                'description': 'Whether or not the comment opens an issue.',
            },
        }
    )
    def create(self, request, screenshot_id, x, y, w, h, text,
               issue_opened=False, *args, **kwargs):
        """Creates a screenshot comment on a review.

        This will create a new comment on a screenshot as part of a review.
        The comment contains text and dimensions for the area being commented
        on.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        try:
            screenshot = Screenshot.objects.get(pk=screenshot_id,
                                                review_request=review_request)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'screenshot_id': ['This is not a valid screenshot ID'],
                }
            }

        new_comment = self.model(screenshot=screenshot, x=x, y=y, w=w, h=h,
                                 text=text, issue_opened=bool(issue_opened))

        if issue_opened:
            new_comment.issue_status = BaseComment.OPEN
        else:
            new_comment.issue_status = None

        new_comment.save()

        review.screenshot_comments.add(new_comment)
        review.save()

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional = {
            'x': {
                'type': int,
                'description': 'The X location for the comment.',
            },
            'y': {
                'type': int,
                'description': 'The Y location for the comment.',
            },
            'w': {
                'type': int,
                'description': 'The width of the comment region.',
            },
            'h': {
                'type': int,
                'description': 'The height of the comment region.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
            'issue_opened': {
                'type': bool,
                'description': 'Whether or not the comment opens an issue.',
            },
            'issue_status': {
                'type': ('dropped', 'open', 'resolved'),
                'description': 'The status of an open issue.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a screenshot comment.

        This can update the text or region of an existing comment. It
        can only be done for comments that are part of a draft review.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            screenshot_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Determine whether or not we're updating the issue status.
        # If so, delegate to the base_comment_resource.
        if base_comment_resource.should_update_issue_status(screenshot_comment,
                                                            **kwargs):
            return base_comment_resource.update_issue_status(request, self,
                                                             *args, **kwargs)

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        # If we've changed the screenshot comment from having no issue
        # opened, to having an issue opened, we should update the issue
        # status to be OPEN
        if not screenshot_comment.issue_opened \
            and kwargs.get('issue_opened', False):
            screenshot_comment.issue_status = BaseComment.OPEN

        for field in ('x', 'y', 'w', 'h', 'text', 'issue_opened'):
            value = kwargs.get(field, None)
            if value is not None:
                setattr(screenshot_comment, field, value)

        screenshot_comment.save()

        return 200, {
            self.item_result_key: screenshot_comment,
        }

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of screenshot comments made on a review."""
        pass

review_screenshot_comment_resource = ReviewScreenshotCommentResource()


class ReviewReplyScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on replies to screenshot comments made on a
    review reply.

    If the reply is a draft, then comments can be added, deleted, or
    changed on this list. However, if the reply is already published,
    then no changed can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'
    fields = dict({
        'reply_to': {
            'type': ReviewScreenshotCommentResource,
            'description': 'The comment being replied to.',
        },
    }, **BaseScreenshotCommentResource.fields)

    mimetype_list_resource_name = 'review-reply-screenshot-comments'
    mimetype_item_resource_name = 'review-reply-screenshot-comment'

    def get_queryset(self, request, review_request_id, review_id, reply_id,
                     *args, **kwargs):
        q = super(ReviewReplyScreenshotCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'reply_to_id': {
                'type': int,
                'description': 'The ID of the comment being replied to.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, reply_to_id, text, *args, **kwargs):
        """Creates a reply to a screenshot comment on a review.

        This will create a reply to a screenshot comment on a review.
        The new comment will contain the same dimensions of the comment
        being replied to, but may contain new text.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        try:
            comment = review_screenshot_comment_resource.get_object(
                request,
                comment_id=reply_to_id,
                *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid screenshot '
                                    'comment ID'],
                }
            }

        q = self.get_queryset(request, *args, **kwargs)
        q = q.filter(Q(reply_to=comment) & Q(review=reply))

        try:
            new_comment = q.get()

            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            is_new = False
        except self.model.DoesNotExist:
            new_comment = self.model(screenshot=comment.screenshot,
                                     reply_to=comment,
                                     x=comment.x,
                                     y=comment.y,
                                     w=comment.w,
                                     h=comment.h)
            is_new = True

        new_comment.text = text
        new_comment.save()

        data = {
            self.item_result_key: new_comment,
        }

        if is_new:
            reply.screenshot_comments.add(new_comment)
            reply.save()

            return 201, data
        else:
            return 303, data, {
                'Location': self.get_href(new_comment, request, *args, **kwargs)
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'text': {
                'type': str,
                'description': 'The new comment text.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply to a screenshot comment.

        This can only update the text in the comment. The comment being
        replied to cannot change.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
            screenshot_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        for field in ('text',):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(screenshot_comment, field, value)

        screenshot_comment.save()

        return 200, {
            self.item_result_key: screenshot_comment,
        }

    @augment_method_from(BaseScreenshotCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes a screenshot comment from a draft reply.

        This will remove the comment from the reply. This cannot be undone.

        Only comments on draft replies can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @augment_method_from(BaseScreenshotCommentResource)
    def get(self, *args, **kwargs):
        """Returns information on a reply to a screenshot comment.

        Much of the information will be identical to that of the comment
        being replied to. For example, the region on the screenshot.
        This is because the reply to the comment is meant to cover the
        exact same section of the screenshot that the original comment covers.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of replies to screenshot comments made on a
        review reply.
        """
        pass

review_reply_screenshot_comment_resource = \
    ReviewReplyScreenshotCommentResource()


class BaseFileAttachmentCommentResource(BaseCommentResource):
    """A base resource for file comments."""
    model = FileAttachmentComment
    name = 'file_attachment_comment'
    fields = dict({
        'id': {
            'type': int,
            'description': 'The numeric ID of the comment.',
        },
        'file_attachment': {
            'type': 'reviewboard.webapi.resources.FileAttachmentResource',
            'description': 'The file the comment was made on.',
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
        'public': {
            'type': bool,
            'description': 'Whether or not the comment is part of a public '
                           'review.',
        },
        'user': {
            'type': 'reviewboard.webapi.resources.UserResource',
            'description': 'The user who made the comment.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the comment. This depends '
                           'on the type of file being commented on.',
        },
        'link_text': {
            'type': str,
            'description': 'The text used to describe a link to the file. '
                           'This may differ depending on the comment.',
        },
        'review_url': {
            'type': str,
            'description': 'The URL to the review UI for the comment on this '
                           'file attachment.',
        },
        'thumbnail_html': {
            'type': str,
            'description': 'The HTML representing a thumbnail, if any, for '
                           'this comment.',
        },
    }, **BaseCommentResource.fields)

    uri_object_key = 'comment_id'
    allowed_methods = ('GET',)

    def get_queryset(self, request, *args, **kwargs):
        review_request = \
            review_request_resource.get_object(request, *args, **kwargs)

        return self.model.objects.filter(
            (Q(file_attachment__review_request=review_request) |
             Q(file_attachment__inactive_review_request=review_request)) &
            Q(review__isnull=False))

    def serialize_link_text_field(self, obj, **kwargs):
        return obj.get_link_text()

    def serialize_public_field(self, obj, **kwargs):
        return obj.review.get().public

    def serialize_review_url_field(self, obj, **kwargs):
        return obj.get_review_url()

    def serialize_thumbnail_html_field(self, obj, **kwargs):
        return obj.thumbnail

    def serialize_timesince_field(self, obj, **kwargs):
        return timesince(obj.timestamp)

    def serialize_user_field(self, obj, **kwargs):
        return obj.review.get().user

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on the comment.

        This contains the comment text, time the comment was made,
        and the file the comment was made on, amongst other information.
        """
        pass


class FileAttachmentCommentResource(BaseFileAttachmentCommentResource):
    """Provides information on filess comments made on a review request.

    The list of comments cannot be modified from this resource. It's meant
    purely as a way to see existing comments that were made on a file. These
    comments will span all public reviews.
    """
    model_parent_key = 'file_attachment'
    uri_object_key = None

    def get_queryset(self, request, review_request_id, file_attachment_id,
                     *args, **kwargs):
        q = super(FileAttachmentCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(file_attachment=file_attachment_id)
        return q

    @webapi_check_local_site
    @augment_method_from(BaseFileAttachmentCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of screenshot comments on a file.

        This list of comments will cover all comments made on this
        file from all reviews.
        """
        pass

file_comment_resource = FileAttachmentCommentResource()


class ReviewFileAttachmentCommentResource(BaseFileAttachmentCommentResource):
    """Provides information on file comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_request_id, review_id,
                     *args, **kwargs):
        q = super(ReviewFileAttachmentCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            PERMISSION_DENIED, NOT_LOGGED_IN)
    @webapi_request_fields(
        required = {
            'file_attachment_id': {
                'type': int,
                'description': 'The ID of the file attachment being '
                               'commented on.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
        optional = {
            'issue_opened': {
                'type': bool,
                'description': 'Whether the comment opens an issue.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, file_attachment_id=None, text=None,
               issue_opened=False, extra_fields={}, *args, **kwargs):
        """Creates a file comment on a review.

        This will create a new comment on a file as part of a review.
        The comment contains text and dimensions for the area being commented
        on.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        try:
            file_attachment = \
                FileAttachment.objects.get(pk=file_attachment_id,
                                           review_request=review_request)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'file_attachment_id': ['This is not a valid file '
                                           'attachment ID'],
                }
            }

        new_comment = self.model(file_attachment=file_attachment,
                                 text=text,
                                 issue_opened=bool(issue_opened))

        _import_extra_data(new_comment.extra_data, extra_fields)

        if issue_opened:
            new_comment.issue_status = BaseComment.OPEN
        else:
            new_comment.issue_status = None

        new_comment.save()

        review.file_attachment_comments.add(new_comment)
        review.save()

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional = {
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
            'issue_opened': {
                'type': bool,
                'description': 'Whether or not the comment opens an issue.',
            },
            'issue_status': {
                'type': ('dropped', 'open', 'resolved'),
                'description': 'The status of an open issue.',
            }
        },
        allow_unknown=True
    )
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates a file comment.

        This can update the text or region of an existing comment. It
        can only be done for comments that are part of a draft review.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            file_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Determine whether or not we're updating the issue status.
        # If so, delegate to the base_comment_resource.
        if base_comment_resource.should_update_issue_status(file_comment,
                                                            **kwargs):
            return base_comment_resource.update_issue_status(request, self,
                                                             *args, **kwargs)

        if not review_resource.has_modify_permissions(request, review):
            return _no_access_error(request.user)

        # If we've updated the comment from having no issue opened,
        # to having an issue opened, we need to set the issue status
        # to OPEN.
        if not file_comment.issue_opened and kwargs.get('issue_opened', False):
            file_comment.issue_status = BaseComment.OPEN

        for field in ('text', 'issue_opened'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(file_comment, field, value)

        _import_extra_data(file_comment.extra_data, extra_fields)
        file_comment.save()

        return 200, {
            self.item_result_key: file_comment,
        }

    @augment_method_from(BaseFileAttachmentCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @augment_method_from(BaseFileAttachmentCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of file comments made on a review."""
        pass

review_file_comment_resource = ReviewFileAttachmentCommentResource()


class ReviewReplyFileAttachmentCommentResource(BaseFileAttachmentCommentResource):
    """Provides information on replies to file comments made on a
    review reply.

    If the reply is a draft, then comments can be added, deleted, or
    changed on this list. However, if the reply is already published,
    then no changed can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'
    fields = dict({
        'reply_to': {
            'type': ReviewFileAttachmentCommentResource,
            'description': 'The comment being replied to.',
        },
    }, **BaseFileAttachmentCommentResource.fields)

    mimetype_list_resource_name = 'review-reply-file-attachment-comments'
    mimetype_item_resource_name = 'review-reply-file-attachment-comment'

    def get_queryset(self, request, review_request_id, review_id, reply_id,
                     *args, **kwargs):
        q = super(ReviewReplyFileAttachmentCommentResource, self).get_queryset(
            request, review_request_id, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'reply_to_id': {
                'type': int,
                'description': 'The ID of the comment being replied to.',
            },
            'text': {
                'type': str,
                'description': 'The comment text.',
            },
        },
    )
    def create(self, request, reply_to_id, text, *args, **kwargs):
        """Creates a reply to a file comment on a review.

        This will create a reply to a file comment on a review.
        The new comment will contain the same dimensions of the comment
        being replied to, but may contain new text.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        try:
            comment = review_file_comment_resource.get_object(
                request,
                comment_id=reply_to_id,
                *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid file comment ID'],
                }
            }

        q = self.get_queryset(request, *args, **kwargs)
        q = q.filter(Q(reply_to=comment) & Q(review=reply))

        try:
            new_comment = q.get()

            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            is_new = False
        except self.model.DoesNotExist:
            new_comment = self.model(file_attachment=comment.file_attachment,
                                     reply_to=comment)
            is_new = True

        new_comment.text = text
        new_comment.save()

        data = {
            self.item_result_key: new_comment,
        }

        if is_new:
            reply.file_attachment_comments.add(new_comment)
            reply.save()

            return 201, data
        else:
            return 303, data, {
                'Location': self.get_href(new_comment, request, *args, **kwargs)
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required = {
            'text': {
                'type': str,
                'description': 'The new comment text.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply to a file comment.

        This can only update the text in the comment. The comment being
        replied to cannot change.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            reply = review_reply_resource.get_object(request, *args, **kwargs)
            file_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_reply_resource.has_modify_permissions(request, reply):
            return _no_access_error(request.user)

        for field in ('text',):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(file_comment, field, value)

        file_comment.save()

        return 200, {
            self.item_result_key: file_comment,
        }

    @augment_method_from(BaseFileAttachmentCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes a file comment from a draft reply.

        This will remove the comment from the reply. This cannot be undone.

        Only comments on draft replies can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @augment_method_from(BaseFileAttachmentCommentResource)
    def get(self, *args, **kwargs):
        """Returns information on a reply to a file comment.

        Much of the information will be identical to that of the comment
        being replied to.
        """
        pass

    @augment_method_from(BaseFileAttachmentCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of replies to file comments made on a review reply.
        """
        pass

review_reply_file_comment_resource = \
    ReviewReplyFileAttachmentCommentResource()


class BaseReviewResource(WebAPIResource):
    """Base class for review resources.

    Provides common fields and functionality for all review resources.
    """
    model = Review
    fields = {
        'body_bottom': {
            'type': str,
            'description': 'The review content below the comments.',
        },
        'body_top': {
            'type': str,
            'description': 'The review content above the comments.',
        },
        'id': {
            'type': int,
            'description': 'The numeric ID of the review.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the review is currently '
                           'visible to other users.',
        },
        'ship_it': {
            'type': bool,
            'description': 'Whether or not the review has been marked '
                           '"Ship It!"',
        },
        'timestamp': {
            'type': str,
            'description': 'The date and time that the review was posted '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': UserResource,
            'description': 'The user who wrote the review.',
        },
    }
    last_modified_field = 'timestamp'

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_queryset(self, request, review_request_id, is_list=False,
                     *args, **kwargs):
        review_request = review_request_resource.get_object(
            request, review_request_id, *args, **kwargs)
        q = Q(review_request=review_request) & \
            Q(**self.get_base_reply_to_field(*args, **kwargs))

        if is_list:
            # We don't want to show drafts in the list.
            q = q & Q(public=True)

        return self.model.objects.filter(q)

    def get_base_reply_to_field(self):
        raise NotImplementedError

    def has_access_permissions(self, request, review, *args, **kwargs):
        return review.is_accessible_by(request.user)

    def has_modify_permissions(self, request, review, *args, **kwargs):
        return review.is_mutable_by(request.user)

    def has_delete_permissions(self, request, review, *args, **kwargs):
        return review.is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional = {
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a new review.

        The new review will start off as private. Only the author of the
        review (the user who is logged in and issuing this API call) will
        be able to see and interact with the review.

        Initial data for the review can be provided by passing data for
        any number of the fields. If nothing is provided, the review will
        start off as blank.

        If the user submitting this review already has a pending draft review
        on this review request, then this will update the existing draft and
        return :http:`303`. Otherwise, this will create a new draft and
        return :http:`201`. Either way, this request will return without
        a payload and with a ``Location`` header pointing to the location of
        the new draft review.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        review, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            **self.get_base_reply_to_field(*args, **kwargs))

        if is_new:
            status_code = 201 # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303 # See Other

        result = self._update_review(request, review, *args, **kwargs)

        if not isinstance(result, tuple) or result[0] != 200:
            return result
        else:
            return status_code, result[1], {
                'Location': self.get_href(review, request, *args, **kwargs),
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional = {
            'ship_it': {
                'type': bool,
                'description': 'Whether or not to mark the review "Ship It!"',
            },
            'body_top': {
                'type': str,
                'description': 'The review content above the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The review content below the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the review public. '
                               'If a review is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a review.

        This updates the fields of a draft review. Published reviews cannot
        be updated.

        Only the owner of a review can make changes. One or more fields can
        be updated at once.

        The only special field is ``public``, which, if set to ``1``, will
        publish the review. The review will then be made publicly visible. Once
        public, the review cannot be modified or made private again.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self._update_review(request, review, *args, **kwargs)

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the draft review.

        This only works for draft reviews, not public reviews. It will
        delete the review and all comments on it. This cannot be undone.

        Only the user who owns the draft can delete it.

        Upon deletion, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on a particular review.

        If the review is not public, then the client's logged in user
        must either be the owner of the review. Otherwise, an error will
        be returned.
        """
        pass

    def _update_review(self, request, review, public=None, *args, **kwargs):
        """Common function to update fields on a draft review."""
        if not self.has_modify_permissions(request, review):
            # Can't modify published reviews or those not belonging
            # to the user.
            return _no_access_error(request.user)

        for field in ('ship_it', 'body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(review, field, value)

        review.save()

        if public:
            review.publish(user=request.user)

        return 200, {
            self.item_result_key: review,
        }


class ReviewReplyDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft reply.

    This works as a convenience to access the current draft reply, so that
    clients can discover the proper location.
    """
    name = 'reply_draft'
    singleton = True
    uri_name = 'draft'

    @webapi_check_local_site
    @webapi_login_required
    def get(self, request, *args, **kwargs):
        """Returns the location of the current draft reply.

        If the draft reply exists, this will return :http:`301` with
        a ``Location`` header pointing to the URL of the draft. Any
        operations on the draft can be done at that URL.

        If the draft reply does not exist, this will return a Does Not
        Exist error.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
            reply = review.get_pending_reply(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not reply:
            return DOES_NOT_EXIST

        return 301, {}, {
            'Location': review_reply_resource.get_href(reply, request,
                                                       *args, **kwargs),
        }

review_reply_draft_resource = ReviewReplyDraftResource()


class ReviewReplyResource(BaseReviewResource):
    """Provides information on a reply to a review.

    A reply is much like a review, but is always tied to exactly one
    parent review. Every comment associated with a reply is also tied to
    a parent comment.
    """
    name = 'reply'
    name_plural = 'replies'
    fields = {
        'body_bottom': {
            'type': str,
            'description': 'The response to the review content below '
                           'the comments.',
        },
        'body_top': {
            'type': str,
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
        'timestamp': {
            'type': str,
            'description': 'The date and time that the reply was posted '
                           '(in YYYY-MM-DD HH:MM:SS format).',
        },
        'user': {
            'type': UserResource,
            'description': 'The user who wrote the reply.',
        },
    }

    item_child_resources = [
        review_reply_diff_comment_resource,
        review_reply_screenshot_comment_resource,
        review_reply_file_comment_resource,
    ]

    list_child_resources = [
        review_reply_draft_resource,
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
        optional = {
            'body_top': {
                'type': str,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
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

        If the user submitting this reply already has a pending draft reply
        on this review, then this will update the existing draft and
        return :http:`303`. Otherwise, this will create a new draft and
        return :http:`201`. Either way, this request will return without
        a payload and with a ``Location`` header pointing to the location of
        the new draft reply.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        reply, is_new = Review.objects.get_or_create(
            review_request=review_request,
            user=request.user,
            public=False,
            base_reply_to=review)

        if is_new:
            status_code = 201 # Created
        else:
            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            status_code = 303 # See Other

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
        optional = {
            'body_top': {
                'type': str,
                'description': 'The response to the review content above '
                               'the comments.',
            },
            'body_bottom': {
                'type': str,
                'description': 'The response to the review content below '
                               'the comments.',
            },
            'public': {
                'type': bool,
                'description': 'Whether or not to make the reply public. '
                               'If a reply is public, it cannot be made '
                               'private again.',
            },
        },
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply.

        This updates the fields of a draft reply. Published replies cannot
        be updated.

        Only the owner of a reply can make changes. One or more fields can
        be updated at once.

        The only special field is ``public``, which, if set to ``1``, will
        publish the reply. The reply will then be made publicly visible. Once
        public, the reply cannot be modified or made private again.
        """
        try:
            review_request_resource.get_object(request, *args, **kwargs)
            review_resource.get_object(request, *args, **kwargs)
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
            return _no_access_error(request.user)

        for field in ('body_top', 'body_bottom'):
            value = kwargs.get(field, None)

            if value is not None:
                setattr(reply, field, value)

                if value == '':
                    reply_to = None
                else:
                    reply_to = reply.base_reply_to

                setattr(reply, '%s_reply_to' % field, reply_to)

        if public:
            reply.publish(user=request.user)
        else:
            reply.save()

        return 200, {
            self.item_result_key: reply,
        }

review_reply_resource = ReviewReplyResource()


class ReviewDraftResource(WebAPIResource):
    """A redirecting resource that points to the current draft review."""
    name = 'review_draft'
    singleton = True
    uri_name = 'draft'

    @webapi_check_local_site
    @webapi_login_required
    def get(self, request, *args, **kwargs):
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
            review = review_request.get_pending_review(request.user)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review:
            return DOES_NOT_EXIST

        return 301, {}, {
            'Location': review_resource.get_href(review, request,
                                                 *args, **kwargs),
        }

review_draft_resource = ReviewDraftResource()


class ReviewResource(BaseReviewResource):
    """Provides information on reviews."""
    uri_object_key = 'review_id'
    model_parent_key = 'review_request'

    item_child_resources = [
        review_diff_comment_resource,
        review_reply_resource,
        review_screenshot_comment_resource,
        review_file_comment_resource,
    ]

    list_child_resources = [
        review_draft_resource,
    ]

    @webapi_check_local_site
    @augment_method_from(BaseReviewResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of all public reviews on a review request."""
        pass

    def get_base_reply_to_field(self, *args, **kwargs):
        return {
            'base_reply_to__isnull': True,
        }

review_resource = ReviewResource()


class ScreenshotResource(BaseScreenshotResource):
    """A resource representing a screenshot on a review request."""
    model_parent_key = 'review_request'

    item_child_resources = [
        screenshot_comment_resource,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_parent_object(self, obj):
        return obj.get_review_request()

    @augment_method_from(BaseScreenshotResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of screenshots on the review request.

        Each screenshot in this list is an uploaded screenshot that is
        shown on the review request.
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def create(self, request, *args, **kwargs):
        """Creates a new screenshot from an uploaded file.

        This accepts any standard image format (PNG, GIF, JPEG) and associates
        it with a draft of a review request.

        Creating a new screenshot will automatically create a new review
        request draft, if one doesn't already exist. This screenshot will
        be part of that draft, and will be shown on the review request
        when it's next published.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The screenshot's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.png"

            <PNG content here>
            -- SoMe BoUnDaRy --
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot. The caption, currently,
        is the only thing that can be updated.

        Updating a screenshot will automatically create a new review request
        draft, if one doesn't already exist. The updates won't be public
        until the review request draft is published.
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def delete(self, *args, **kwargs):
        """Deletes the screenshot.

        This will remove the screenshot from the draft review request.
        This cannot be undone.

        Deleting a screenshot will automatically create a new review request
        draft, if one doesn't already exist. The screenshot won't be actually
        removed until the review request draft is published.

        This can be used to remove old screenshots that were previously
        shown, as well as newly added screenshots that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

screenshot_resource = ScreenshotResource()


class FileAttachmentResource(BaseFileAttachmentResource):
    """A resource representing a screenshot on a review request."""
    model_parent_key = 'review_request'

    item_child_resources = [
        file_comment_resource,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    mimetype_list_resource_name = 'file-attachments'
    mimetype_item_resource_name = 'file-attachment'

    def get_parent_object(self, obj):
        return obj.get_review_request()

    @augment_method_from(BaseFileAttachmentResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of file attachments on the review request.

        Each screenshot in this list is a file attachment attachment that is
        shown on the review request.
        """
        pass

    @augment_method_from(BaseFileAttachmentResource)
    def create(self, request, *args, **kwargs):
        """Creates a new file attachment from a file attachment.

        This accepts any file type and associates it with a draft of a
        review request.

        Creating a new file attachment will automatically create a new review
        request draft, if one doesn't already exist. This attachment will
        be part of that draft, and will be shown on the review request
        when it's next published.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The file's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.zip"

            <Content here>
            -- SoMe BoUnDaRy --
        """
        pass

    @augment_method_from(BaseFileAttachmentResource)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot. The caption, currently,
        is the only thing that can be updated.

        Updating a screenshot will automatically create a new review request
        draft, if one doesn't already exist. The updates won't be public
        until the review request draft is published.
        """
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(BaseFileAttachmentResource)
    def delete(self, *args, **kwargs):
        """Deletes the file attachment

        This will remove the file attachment from the draft review request.
        This cannot be undone.

        Deleting a file attachment will automatically create a new review
        request draft, if one doesn't already exist. The attachment won't
        be actually removed until the review request draft is published.

        This can be used to remove old file attachments that were previously
        shown, as well as newly added file attachments that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

file_attachment_resource = FileAttachmentResource()


class ReviewRequestLastUpdateResource(WebAPIResource):
    """Provides information on the last update made to a review request.

    Clients can periodically poll this to see if any new updates have been
    made.
    """
    name = 'last_update'
    singleton = True
    allowed_methods = ('GET',)

    fields = {
        'summary': {
            'type': str,
            'description': 'A short summary of the update. This should be one '
                           'of "Review request updated", "Diff updated", '
                           '"New reply" or "New review".',
        },
        'timestamp': {
            'type': str,
            'description': 'The timestamp of this most recent update '
                           '(YYYY-MM-DD HH:MM:SS format).',
        },
        'type': {
            'type': ('review-request', 'diff', 'reply', 'review'),
            'description': "The type of the last update. ``review-request`` "
                           "means the last update was an update of the "
                           "review request's information. ``diff`` means a "
                           "new diff was uploaded. ``reply`` means a reply "
                           "was made to an existing review. ``review`` means "
                           "a new review was posted.",
        },
        'user': {
            'type': str,
            'description': 'The user who made the last update.',
        },
    }

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, *args, **kwargs):
        """Returns the last update made to the review request.

        This shows the type of update that was made, the user who made the
        update, and when the update was made. Clients can use this to inform
        the user that the review request was updated, or automatically update
        it in the background.

        This does not take into account changes to a draft review request, as
        that's generally not update information that the owner of the draft is
        interested in. Only public updates are represented.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request_resource.has_access_permissions(request,
                                                              review_request):
            return _no_access_error(request.user)

        timestamp, updated_object = review_request.get_last_activity()

        if get_modified_since(request, timestamp):
            return HttpResponseNotModified()

        user = None
        summary = None
        update_type = None

        if isinstance(updated_object, ReviewRequest):
            user = updated_object.submitter

            if updated_object.status == ReviewRequest.SUBMITTED:
                summary = _("Review request submitted")
            elif updated_object.status == ReviewRequest.DISCARDED:
                summary = _("Review request discarded")
            else:
                summary = _("Review request updated")

            update_type = "review-request"
        elif isinstance(updated_object, DiffSet):
            summary = _("Diff updated")
            update_type = "diff"
        elif isinstance(updated_object, Review):
            user = updated_object.user

            if updated_object.is_reply():
                summary = _("New reply")
                update_type = "reply"
            else:
                summary = _("New review")
                update_type = "review"
        else:
            # Should never be able to happen. The object will always at least
            # be a ReviewRequest.
            assert False

        return 200, {
            self.item_result_key: {
                'timestamp': timestamp.isoformat(),
                'user': user,
                'summary': summary,
                'type': update_type,
            }
        }, {
            'Last-Modified': http_date(timestamp)
        }

review_request_last_update_resource = ReviewRequestLastUpdateResource()


class ReviewRequestResource(WebAPIResource):
    """Provides information on review requests."""
    model = ReviewRequest
    name = 'review_request'

    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the review request.',
        },
        'blocks': {
            'type': ['reviewboard.webapi.resources.ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request is blocking.',
        },
        'depends_on': {
            'type': ['reviewboard.webapi.resources.ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request depends on.',
        },
        'submitter': {
            'type': UserResource,
            'description': 'The user who submitted the review request.',
        },
        'time_added': {
            'type': str,
            'description': 'The date and time that the review request was '
                           'added (in YYYY-MM-DD HH:MM:SS format).',
        },
        'last_updated': {
            'type': str,
            'description': 'The date and time that the review request was '
                           'last updated (in YYYY-MM-DD HH:MM:SS format).',
        },
        'status': {
            'type': ('discarded', 'pending', 'submitted'),
            'description': 'The current status of the review request.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the review request is currently '
                           'visible to other users.',
        },
        'changenum': {
            'type': int,
            'description': 'The change number that the review request is '
                           'representing. These are server-side '
                           'repository-specific change numbers, and are not '
                           'supported by all types of repositories. This may '
                           'be ``null``.',
        },
        'repository': {
            'type': RepositoryResource,
            'description': "The repository that the review request's code "
                           "is stored on.",
        },
        'summary': {
            'type': str,
            'description': "The review request's brief summary.",
        },
        'description': {
            'type': str,
            'description': "The review request's description.",
        },
        'testing_done': {
            'type': str,
            'description': 'The information on the testing that was done '
                           'for the change.',
        },
        'bugs_closed': {
            'type': [str],
            'description': 'The list of bugs closed or referenced by this '
                           'change.',
        },
        'branch': {
            'type': str,
            'description': 'The branch that the code was changed on or that '
                           'the code will be committed to. This is a '
                           'free-form field that can store any text.',
        },
        'target_groups': {
            'type': [ReviewGroupResource],
            'description': 'The list of review groups who were requested '
                           'to review this change.',
        },
        'target_people': {
            'type': [UserResource],
            'description': 'The list of users who were requested to review '
                           'this change.',
        },
        'url': {
            'type': str,
            'description': "The URL to the review request's page on the site.",
        },
    }
    uri_object_key = 'review_request_id'
    model_object_key = 'display_id'
    last_modified_field = 'last_updated'
    item_child_resources = [
        change_resource,
        diffset_resource,
        review_request_draft_resource,
        review_request_last_update_resource,
        review_resource,
        screenshot_resource,
        file_attachment_resource
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    _close_type_map = {
        'submitted': ReviewRequest.SUBMITTED,
        'discarded': ReviewRequest.DISCARDED,
    }

    def get_queryset(self, request, is_list=False, local_site_name=None,
                     *args, **kwargs):
        """Returns a queryset for ReviewRequest models.

        By default, this returns all published or formerly published
        review requests.

        If the queryset is being used for a list of review request
        resources, then it can be further filtered by one or more of the
        following arguments in the URL:

          * ``changenum``
              - The change number the review requests must be
                against. This will only return one review request
                per repository, and only works for repository
                types that support server-side changesets.

          * ``time-added-to``
              - The date/time that all review requests must be added before.
                This is compared against the review request's ``time_added``
                field. See below for information on date/time formats.

          * ``time-added-from``
              - The earliest date/time the review request could be added.
                This is compared against the review request's ``time_added``
                field. See below for information on date/time formats.

          * ``last-updated-to``
              - The date/time that all review requests must be last updated
                before. This is compared against the review request's
                ``last_updated`` field. See below for information on date/time
                formats.

          * ``last-updated-from``
              - The earliest date/time the review request could be last
                updated. This is compared against the review request's
                ``last_updated`` field. See below for information on date/time
                formats.

          * ``from-user``
              - The username that the review requests must be owned by.

          * ``repository``
              - The ID of the repository that the review requests must be on.

          * ``ship-it``
              - The review request must have at least one review with Ship It
                set, if this is 1. Otherwise, if 0, it must not have any marked
                Ship It.

          * ``status``
              - The status of the review requests. This can be ``pending``,
                ``submitted`` or ``discarded``.

          * ``to-groups``
              - A comma-separated list of review group names that the review
                requests must have in the reviewer list.

          * ``to-user-groups``
              - A comma-separated list of usernames who are in groups that the
                review requests must have in the reviewer list.

          * ``to-users``
              - A comma-separated list of usernames that the review requests
                must either have in the reviewer list specifically or by way
                of a group.

          * ``to-users-directly``
              - A comma-separated list of usernames that the review requests
                must have in the reviewer list specifically.

        Some arguments accept dates. The handling of dates is quite flexible,
        accepting a variety of date/time formats, but we recommend sticking
        with ISO8601 format.

        ISO8601 format defines a date as being in ``{yyyy}-{mm}-{dd}`` format,
        and a date/time as being in ``{yyyy}-{mm}-{dd}T{HH}:{MM}:{SS}``.
        A timezone can also be appended to this, using ``-{HH:MM}``.

        The following examples are valid dates and date/times:

            * ``2010-06-27``
            * ``2010-06-27T16:26:30``
            * ``2010-06-27T16:26:30-08:00``
        """
        local_site = _get_local_site(local_site_name)

        if is_list:
            q = Q()

            if 'to-groups' in request.GET:
                for group_name in request.GET.get('to-groups').split(','):
                    q = q & self.model.objects.get_to_group_query(group_name,
                                                                  None)

            if 'to-users' in request.GET:
                for username in request.GET.get('to-users').split(','):
                    q = q & self.model.objects.get_to_user_query(username)

            if 'to-users-directly' in request.GET:
                for username in request.GET.get('to-users-directly').split(','):
                    q = q & self.model.objects.get_to_user_directly_query(
                        username)

            if 'to-users-groups' in request.GET:
                for username in request.GET.get('to-users-groups').split(','):
                    q = q & self.model.objects.get_to_user_groups_query(
                        username)

            if 'from-user' in request.GET:
                q = q & self.model.objects.get_from_user_query(
                    request.GET.get('from-user'))

            if 'repository' in request.GET:
                q = q & Q(repository=int(request.GET.get('repository')))

            if 'changenum' in request.GET:
                q = q & Q(changenum=int(request.GET.get('changenum')))

            if 'ship-it' in request.GET:
                ship_it = request.GET.get('ship-it')

                if ship_it in ('1', 'true', 'True'):
                    q = q & Q(shipit_count__gt=0)
                elif ship_it in ('0', 'false', 'False'):
                    q = q & Q(shipit_count=0)

            if 'time-added-from' in request.GET:
                date = self._parse_date(request.GET['time-added-from'])

                if date:
                    q = q & Q(time_added__gte=date)

            if 'time-added-to' in request.GET:
                date = self._parse_date(request.GET['time-added-to'])

                if date:
                    q = q & Q(time_added__lt=date)

            if 'last-updated-from' in request.GET:
                date = self._parse_date(request.GET['last-updated-from'])

                if date:
                    q = q & Q(last_updated__gte=date)

            if 'last-updated-to' in request.GET:
                date = self._parse_date(request.GET['last-updated-to'])

                if date:
                    q = q & Q(last_updated__lt=date)

            status = string_to_status(request.GET.get('status', 'pending'))

            queryset = self.model.objects.public(user=request.user,
                                                 status=status,
                                                 local_site=local_site,
                                                 extra_query=q)

            return queryset
        else:
            return self.model.objects.filter(local_site=local_site)

    def has_access_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_mutable_by(request.user)

    def has_delete_permissions(self, request, review_request, *args, **kwargs):
        return request.user.has_perm('reviews.delete_reviewrequest')

    def serialize_bugs_closed_field(self, obj, **kwargs):
        return obj.get_bug_list()

    def serialize_status_field(self, obj, **kwargs):
        return status_to_string(obj.status)

    def serialize_id_field(self, obj, **kwargs):
        return obj.display_id

    def serialize_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, INVALID_USER,
                            INVALID_REPOSITORY, CHANGE_NUMBER_IN_USE,
                            INVALID_CHANGE_NUMBER, EMPTY_CHANGESET,
                            REPO_AUTHENTICATION_ERROR, REPO_INFO_ERROR,
                            MISSING_REPOSITORY)
    @webapi_request_fields(
        optional={
            'changenum': {
                'type': int,
                'description': 'The optional changenumber to look up for the '
                               'review request details. This only works with '
                               'repositories that support server-side '
                               'changesets.',
            },
            'repository': {
                'type': str,
                'description': 'The path or ID of the repository that the '
                               'review request is for.',
            },
            'submit_as': {
                'type': str,
                'description': 'The optional user to submit the review '
                               'request as. This requires that the actual '
                               'logged in user is either a superuser or has '
                               'the "reviews.can_submit_as_another_user" '
                               'permission.',
            },
        })
    def create(self, request, repository=None, submit_as=None, changenum=None,
               local_site_name=None, *args, **kwargs):
        """Creates a new review request.

        The new review request will start off as private and pending, and
        will normally be blank. However, if ``changenum`` is passed and the
        given repository both supports server-side changesets and has changeset
        support in Review Board, some details (Summary, Description and Testing
        Done sections, for instance) may be automatically filled in from the
        server.

        Any new review request will have an associated draft (reachable
        through the ``draft`` link). All the details of the review request
        must be set through the draft. The new review request will be public
        when that first draft is published.

        A repository can be passed. This is required for diffs associated
        with a review request. A valid repository is in the form of a numeric
        repository ID, the name of a repository, or the path to a repository
        (matching exactly the registered repository's Path or Mirror Path
        fields in the adminstration interface).

        If a repository is not passed, this review request can only be
        used for attached files.

        Clients can create review requests on behalf of another user by setting
        the ``submit_as`` parameter to the username of the desired user. This
        requires that the client is currently logged in as a user that has the
        ``reviews.can_submit_as_another_user`` permission set. This capability
        is useful when writing automation scripts, such as post-commit hooks,
        that need to create review requests for another user.
        """
        user = request.user
        local_site = _get_local_site(local_site_name)

        if submit_as and user.username != submit_as:
            if not user.has_perm('reviews.can_submit_as_another_user'):
                return _no_access_error(request.user)

            try:
                user = User.objects.get(username=submit_as)
            except User.DoesNotExist:
                return INVALID_USER

        if repository is not None:
            try:
                try:
                    repository = Repository.objects.get(pk=int(repository),
                                                        local_site=local_site)
                except ValueError:
                    # The repository is not an ID.
                    repository = Repository.objects.get(
                        (Q(path=repository) |
                         Q(mirror_path=repository) |
                         Q(name=repository)) &
                        Q(local_site=local_site))
            except Repository.DoesNotExist, e:
                return INVALID_REPOSITORY, {
                    'repository': repository
                }

            if not repository.is_accessible_by(request.user):
                return _no_access_error(request.user)

        try:
            review_request = ReviewRequest.objects.create(user, repository,
                                                          changenum, local_site)

            return 201, {
                self.item_result_key: review_request
            }
        except AuthenticationError:
            return REPO_AUTHENTICATION_ERROR
        except RepositoryNotFoundError:
            return MISSING_REPOSITORY
        except ChangeNumberInUseError, e:
            return CHANGE_NUMBER_IN_USE, {
                'review_request': e.review_request
            }
        except InvalidChangeNumberError:
            return INVALID_CHANGE_NUMBER
        except EmptyChangeSetError:
            return EMPTY_CHANGESET
        except SSHError, e:
            logging.error("Got unexpected SSHError when creating repository: %s"
                          % e, exc_info=1, request=request)
            return REPO_INFO_ERROR
        except SCMError, e:
            logging.error("Got unexpected SCMError when creating repository: %s"
                          % e, exc_info=1, request=request)
            return REPO_INFO_ERROR

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'status': {
                'type': ('discarded', 'pending', 'submitted'),
                'description': 'The status of the review request. This can '
                               'be changed to close or reopen the review '
                               'request',
            },
            'changenum': {
                'type': int,
                'description': 'The optional changenumber to set or update. '
                               'This can be used to re-associate with a new '
                               'change number, or to create/update a draft '
                               'with new information from the current '
                               'change number. This only works with '
                               'repositories that support server-side '
                               'changesets.',
            },
            'description': {
                'type': str,
                'description': 'The description of the update. Should only be '
                               'used if the review request have been submitted '
                               'or discarded.',
            },
        },
    )
    def update(self, request, status=None, changenum=None, description=None,
               *args, **kwargs):
        """Updates the status of the review request.

        The only supported update to a review request's resource is to change
        the status, the associated server-side, change number, or to update
        information from the existing change number.

        The status can be set in order to close the review request as
        discarded or submitted, or to reopen as pending.

        The change number can either be changed to a new number, or the
        current change number can be passed. In either case, a new draft will
        be created or an existing one updated to include information from
        the server based on the change number.

        Changes to a review request's fields, such as the summary or the
        list of reviewers, is made on the Review Request Draft resource.
        This can be accessed through the ``draft`` link. Only when that
        draft is published will the changes end up back in this resource.
        """
        try:
            review_request = \
                review_request_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, review_request):
            return _no_access_error(request.user)

        if (status is not None and
            (review_request.status != string_to_status(status) or
             review_request.status != ReviewRequest.PENDING_REVIEW)):
            try:
                if status in self._close_type_map:
                    review_request.close(self._close_type_map[status],
                                         request.user, description)
                elif status == 'pending':
                    review_request.reopen(request.user)
                else:
                    raise AssertionError("Code path for invalid status '%s' "
                                         "should never be reached." % status)
            except PermissionError:
                return _no_access_error(request.user)

        if changenum is not None:
            if changenum != review_request.changenum:
                review_request.update_changenum(changenum, request.user)

            try:
                draft = ReviewRequestDraftResource.prepare_draft(
                    request, review_request)
            except PermissionDenied:
                return PERMISSION_DENIED

            try:
                draft.update_from_changenum(changenum)
            except InvalidChangeNumberError:
                return INVALID_CHANGE_NUMBER

            draft.save()
            review_request.reopen()

        return 200, {
            self.item_result_key: review_request,
        }

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the review request permanently.

        This is a dangerous call to make, as it will delete the review
        request, associated screenshots, diffs, and reviews. There is no
        going back after this call is made.

        Only users who have been granted the ``reviews.delete_reviewrequest``
        permission (which includes administrators) can perform a delete on
        the review request.

        After a successful delete, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'changenum': {
                'type': str,
                'description': 'The change number the review requests must '
                               'have set. This will only return one review '
                               'request per repository, and only works for '
                               'repository types that support server-side '
                               'changesets.',
            },
            'time-added-to': {
                'type': str,
                'description': 'The date/time that all review requests must '
                               'be added before. This is compared against the '
                               'review request\'s ``time_added`` field. This '
                               'must be a valid :term:`date/time format`.',
            },
            'time-added-from': {
                'type': str,
                'description': 'The earliest date/time the review request '
                               'could be added. This is compared against the '
                               'review request\'s ``time_added`` field. This '
                               'must be a valid :term:`date/time format`.',
            },
            'last-updated-to': {
                'type': str,
                'description': 'The date/time that all review requests must '
                               'be last updated before. This is compared '
                               'against the review request\'s '
                               '``last_updated`` field. This must be a valid '
                               ':term:`date/time format`.',
            },
            'last-updated-from': {
                'type': str,
                'description': 'The earliest date/time the review request '
                               'could be last updated. This is compared '
                               'against the review request\'s ``last_updated`` '
                               'field. This must be a valid '
                               ':term:`date/time format`.',
            },
            'from-user': {
                'type': str,
                'description': 'The username that the review requests must '
                               'be owned by.',
            },
            'repository': {
                'type': int,
                'description': 'The ID of the repository that the review '
                               'requests must be on.',
            },
            'ship-it': {
                'type': bool,
                'description': 'The review request must have at least one '
                               'review with Ship It set, if this is 1. '
                               'Otherwise, if 0, it must not have any marked '
                               'Ship It.',
            },
            'status': {
                'type': ('all', 'discarded', 'pending', 'submitted'),
                'description': 'The status of the review requests.'
            },
            'to-groups': {
                'type': str,
                'description': 'A comma-separated list of review group names '
                               'that the review requests must have in the '
                               'reviewer list.',
            },
            'to-user-groups': {
                'type': str,
                'description': 'A comma-separated list of usernames who are '
                               'in groups that the review requests must have '
                               'in the reviewer list.',
            },
            'to-users': {
                'type': str,
                'description': 'A comma-separated list of usernames that the '
                               'review requests must either have in the '
                               'reviewer list specifically or by way of '
                               'a group.',
            },
            'to-users-directly': {
                'type': str,
                'description': 'A comma-separated list of usernames that the '
                               'review requests must have in the reviewer '
                               'list specifically.',
            }
        },
        allow_unknown=True
    )
    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Returns all review requests that the user has read access to.

        By default, this returns all published or formerly published
        review requests.

        The resulting list can be filtered down through the many
        request parameters.
        """
        pass

    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on a particular review request.

        This contains full information on the latest published review request.

        If the review request is not public, then the client's logged in user
        must either be the owner of the review request or must have the
        ``reviews.can_edit_reviewrequest`` permission set. Otherwise, an
        error will be returned.
        """
        pass

    def get_object(self, request, review_request_id, local_site_name=None,
                   is_list=True, *args, **kwargs):
        """Returns an object, given captured parameters from a URL.

        This is an override of the djblets WebAPIResource get_object, which
        knows about local_id and local_site_name.
        """
        queryset = self.get_queryset(request, local_site_name=local_site_name,
                                     review_request_id=review_request_id,
                                     *args, **kwargs)

        if local_site_name:
            return queryset.get(local_id=review_request_id)
        else:
            return queryset.get(pk=review_request_id)

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object.

        This is an override of WebAPIResource.get_href which will use the
        local_id instead of the pk.
        """
        if obj.local_site_id:
            local_site_name = obj.local_site.name
        else:
            local_site_name = None

        href_kwargs = {
            self.uri_object_key: obj.display_id,
        }
        href_kwargs.update(self.get_href_parent_ids(obj))

        return request.build_absolute_uri(
            local_site_reverse(self._build_named_url(self.name),
                               kwargs=href_kwargs,
                               local_site_name=local_site_name))

    def _parse_date(self, timestamp_str):
        try:
            return dateutil.parser.parse(timestamp_str)
        except ValueError:
            return None


review_request_resource = ReviewRequestResource()


class SearchResource(WebAPIResource, DjbletsUserResource):
    """
    Provides information on users, groups and review requests.

    This is the resource for the autocomplete widget for
    quick search. This resource helps filter for
    users, groups and review requests.
    """
    name = 'search'
    singleton = True

    def has_access_permissions(self, request, *args, **kwargs):
        return True

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, local_site_name=None, fullname=None, q=None,
            displayname=None, id=None, *args, **kwargs):
        """Returns information on users, groups and review requests.

        This is used by the autocomplete widget for quick search to
        get information on users, groups and review requests. This
        function returns users' first name, last name and username,
        groups' name and display name, and review requests' ID and
        summary.
        """
        search_q = request.GET.get('q', None)
        local_site = _get_local_site(local_site_name)
        if local_site:
            query = local_site.users.filter(is_active=True)
        else:
            query = self.model.objects.filter(is_active=True)

        if search_q:
            q = (Q(username__istartswith=search_q) |
                 Q(first_name__istartswith=search_q) |
                 Q(last_name__istartswith=search_q))

            if request.GET.get('fullname', None):
                q = q | (Q(first_name__istartswith=search_q) |
                         Q(last_name__istartswith=search_q))

            query = query.filter(q)

        search_q = request.GET.get('q', None)
        local_site = _get_local_site(local_site_name)
        query_groups = Group.objects.filter(local_site=local_site)

        if search_q:
            q = (Q(name__istartswith=search_q) |
                  Q(display_name__istartswith=search_q))

            if request.GET.get('displayname', None):
                q = q | Q(display_name__istartswith=search_q)

            query_groups = query_groups.filter(q)

        search_q = request.GET.get('q', None)
        query_review_requests = ReviewRequest.objects.filter(local_site=local_site)

        if search_q:
            q = (Q(id__istartswith=search_q) |
                  Q(summary__icontains=search_q))

            if request.GET.get('id', None):
                q = q | Q(id__istartswith=search_q)

            query_review_requests = query_review_requests.filter(q)

        return 200, {
            self.name: {
                'users': query,
                'groups': query_groups,
                'review_requests': query_review_requests,
            },
        }

search_resource = SearchResource()


class ServerInfoResource(WebAPIResource):
    """Information on the Review Board server.

    This contains product information, such as the version, and
    site-specific information, such as the main URL and list of
    administrators.
    """
    name = 'info'
    singleton = True
    mimetype_item_resource_name = 'server-info'

    @webapi_check_local_site
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns the information on the Review Board server."""
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        url = '%s://%s%s' % (siteconfig.get('site_domain_method'), site.domain,
                             local_site_reverse('root', request=request))

        return 200, {
            self.item_result_key: {
                'product': {
                    'name': 'Review Board',
                    'version': get_version_string(),
                    'package_version': get_package_version(),
                    'is_release': is_release(),
                },
                'site': {
                    'url': url,
                    'administrators': [{'name': name, 'email': email}
                                       for name, email in settings.ADMINS],
                    'time_zone': settings.TIME_ZONE,
                },
                'capabilities': {
                    'diffs': {
                        'base_commit_ids': True,
                        'moved_files': True,
                    },
                    'scmtools': {
                        'perforce': {
                            'moved_files': True,
                        },
                    },
                },
            },
        }

server_info_resource = ServerInfoResource()


class SessionResource(WebAPIResource):
    """Information on the active user's session.

    This includes information on the user currently logged in through the
    calling client, if any. Currently, the resource links to that user's
    own resource, making it easy to figure out the user's information and
    any useful related resources.
    """
    name = 'session'
    singleton = True

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns information on the client's session.

        This currently just contains information on the currently logged-in
        user (if any).
        """
        expanded_resources = request.GET.get('expand', '').split(',')

        authenticated = request.user.is_authenticated()

        data = {
            'authenticated': authenticated,
            'links': self.get_links(request=request, *args, **kwargs),
        }

        if authenticated and 'user' in expanded_resources:
            data['user'] = request.user
            del data['links']['user']

        return 200, {
            self.name: data,
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        links = {}

        if request and request.user.is_authenticated():
            user_resource = get_resource_for_object(request.user)
            href = user_resource.get_href(request.user, request,
                                          *args, **kwargs)

            links['user'] = {
                'method': 'GET',
                'href': href,
                'title': unicode(request.user),
                'resource': user_resource,
                'list-resource': False,
            }

        return links

session_resource = SessionResource()


class RootResource(DjbletsRootResource):
    """Links to all the main resources, including URI templates to resources
    anywhere in the tree.

    This should be used as a starting point for any clients that need to access
    any resources in the API. By browsing through the resource tree instead of
    hard-coding paths, your client can remain compatible with any changes in
    the resource URI scheme.
    """
    mimetype_vendor = 'reviewboard.org'

    def __init__(self, *args, **kwargs):
        super(RootResource, self).__init__([
            default_reviewer_resource,
            extension_resource,
            hosting_service_account_resource,
            repository_resource,
            review_group_resource,
            review_request_resource,
            search_resource,
            server_info_resource,
            session_resource,
            user_resource,
        ], *args, **kwargs)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsRootResource)
    def get(self, request, *args, **kwargs):
        """Retrieves the list of top-level resources and templates.

        This is a specialization of djblets.webapi.RootResource which does a
        permissions check on the LocalSite.
        """
        pass

root_resource = RootResource()


register_resource_for_model(ChangeDescription, change_resource)
register_resource_for_model(
    Comment,
    lambda obj: obj.review.get().is_reply() and
                review_reply_diff_comment_resource or
                review_diff_comment_resource)
register_resource_for_model(DefaultReviewer, default_reviewer_resource)
register_resource_for_model(DiffSet, diffset_resource)
register_resource_for_model(FileDiff, filediff_resource)
register_resource_for_model(Group, review_group_resource)
register_resource_for_model(RegisteredExtension, extension_resource)
register_resource_for_model(HostingServiceAccount,
                            hosting_service_account_resource)
register_resource_for_model(Repository, repository_resource)
register_resource_for_model(
    Review,
    lambda obj: obj.is_reply() and review_reply_resource or review_resource)
register_resource_for_model(ReviewRequest, review_request_resource)
register_resource_for_model(ReviewRequestDraft, review_request_draft_resource)
register_resource_for_model(Screenshot, screenshot_resource)
register_resource_for_model(FileAttachment, file_attachment_resource)
register_resource_for_model(
    ScreenshotComment,
    lambda obj: obj.review.get().is_reply() and
                review_reply_screenshot_comment_resource or
                review_screenshot_comment_resource)
register_resource_for_model(
    FileAttachmentComment,
    lambda obj: obj.review.get().is_reply() and
                review_reply_file_comment_resource or
                review_file_comment_resource)
register_resource_for_model(User, user_resource)
