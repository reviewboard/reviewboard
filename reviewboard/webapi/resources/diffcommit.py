"""Resource representing the commits in a multi-commit review request."""

from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils.six.moves.urllib.parse import urlencode
from djblets.util.decorators import augment_method_from
from djblets.util.http import get_http_requested_mimetype, set_last_modified
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import (DateTimeFieldType, DictFieldType,
                                   IntFieldType, StringFieldType)

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.diffviewer.validators import COMMIT_ID_LENGTH
from reviewboard.webapi.base import ImportExtraDataError, WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required,
                                           webapi_login_required,
                                           webapi_response_errors)
from reviewboard.webapi.resources import resources


class DiffCommitResource(WebAPIResource):
    """Provides information on a collection of commits in a review request.

    Each diff commit resource contains individual per-file diffs as child
    resources, as well as metadata to reproduce the actual commits in a
    version control system.
    """

    added_in = '4.0'
    model = DiffCommit
    name = 'commit'

    model_parent_key = 'diffset'
    model_object_key = 'commit_id'

    uri_object_key = 'commit_id'
    uri_object_key_regex = r'[A-Za-z0-9]{1,%s}' % COMMIT_ID_LENGTH

    allowed_methods = ('GET', 'PUT')

    required_features = [dvcs_feature]

    allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
        {'item': 'text/x-patch'},
    ]

    fields = {
        'id': {
            'type': IntFieldType,
            'description': 'The numeric ID of the commit resource.',
        },
        'author_name': {
            'type': StringFieldType,
            'description': 'The name of the author of this commit.',
        },
        'author_date': {
            'type': DateTimeFieldType,
            'description': 'The date and time this commit was authored in ISO '
                           '8601 format (YYYY-MM-DD HH:MM:SS+ZZZZ).',
        },
        'author_email': {
            'type': StringFieldType,
            'description': 'The e-mail address of the author of this commit.',
        },
        'commit_id': {
            'type': StringFieldType,
            'description': 'The ID of this commit.',
        },
        'committer_name': {
            'type': StringFieldType,
            'description': 'The name of the the committer of this commit, if '
                           'applicable.',
        },
        'committer_date': {
            'type': StringFieldType,
            'description': 'The date and time this commit was committed in '
                           'ISO 8601 format (YYYY-MM-DD HH:MM:SS+ZZZZ).',
        },
        'committer_email': {
            'type': StringFieldType,
            'description': 'The e-mail address of the committer of this '
                           'commit.',
        },
        'commit_message': {
            'type': StringFieldType,
            'description': 'The commit message.',
        },
        'extra_data': {
            'type': DictFieldType,
            'description': 'Extra data as part of the commit. This can be set '
                           'by the API or extensions.',
        },
        'filename': {
            'type': StringFieldType,
            'description': 'The name of the corresponding diff.',
        },
        'parent_id': {
            'type': StringFieldType,
            'description': 'The ID of the parent commit.',
        },
    }

    def get_queryset(self, request, *args, **kwargs):
        """Return the queryset for the available commits.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            The queryset of all available commits.
        """
        try:
            diffset = resources.diff.get_object(request, *args, **kwargs)
        except DiffSet.DoesNotExist:
            return self.model.objects.none()

        return self.model.objects.filter(diffset=diffset)

    def has_access_permissions(self, request, commit, *args, **kwargs):
        """Return whether or not the user has access permissions to the commit.

        A user has access permissions for a commit if they have permission to
        access the parent review request.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            commit (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The object to check access permissions for.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            bool:
            Whether or not the user has permission to access the commit.
        """
        review_request = resources.review_request.get_object(request, *args,
                                                             **kwargs)
        return review_request.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Return whether the user has access permissions to the list resource.

        A user has list access permissions if they have premission to access
        the parent review request.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            commit (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The object to check access permissions for.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            bool:
            Whether or not the user has permission to access the list resource.
        """
        review_request = resources.review_request.get_object(request, *args,
                                                             **kwargs)
        return review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Return whether the user has access permissions to modify the object.

        A user has modify permissions for a commit if they have permission to
        modify the parent review request.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.

            commit (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The object to check access permissions for.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            bool:
            Whether or not the user has permission to modify the object.
        """
        review_request = resources.review_request.get_object(request, *args,
                                                             **kwargs)
        return review_request.is_mutable_by(request.user)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    @augment_method_from(WebAPIResource)
    def get_list(self, request, *args, **kwargs):
        """Return the list of commits."""

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    def get(self, request, *args, **kwargs):
        """Return information about a commit.

        If the :mimetype:`text/x-patch` mimetype is requested, the contents of
        the patch will be returned.

        Otherwise, metadata about the commit (such as author name, author date,
        etc.) will be returned.
        """
        mimetype = get_http_requested_mimetype(
            request,
            [mimetype['item'] for mimetype in self.allowed_mimetypes])

        if mimetype != 'text/x-patch':
            return super(DiffCommitResource, self).get(request, *args,
                                                       **kwargs)

        try:
            review_request = resources.review_request.get_object(
                request, *args, **kwargs)
            commit = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, commit, *args, **kwargs):
            return self.get_no_access_error(request)

        tool = review_request.repository.get_scmtool()
        data = tool.get_parser(b'').raw_diff(commit)

        rsp = HttpResponse(data, content_type=mimetype)
        rsp['Content-Disposition'] = ('inline; filename=%s.patch'
                                      % commit.commit_id)

        set_last_modified(rsp, commit.last_modified)
        return rsp

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(allow_unknown=True)
    def update(self, request, extra_fields=None, *args, **kwargs):
        """Update a commit.

        This is used solely for modifying the extra data on a commit. The
        contents of a commit cannot be modified.

        Extra data can be stored for later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            commit = self.get_object(request, *args, **kwargs)
        except DiffCommit.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, commit, *args, **kwargs):
            return self.get_no_access_error(request)

        if extra_fields:
            try:
                self.import_extra_data(commit, commit.extra_data, extra_fields)
            except ImportExtraDataError as e:
                return e.error_payload

            commit.save(update_fields=['extra_data'])

        return 200, {
            self.item_result_key: commit,
        }

    def _get_files_link(self, commit, request, diff_resource,
                        filediff_resource, files_key, *args, **kwargs):
        """Return the link for the files.

        As an alternative to having a per-commit files resources (and draft
        resource equivalent), this method generates link to the
        :py:class:`~reviewboard.webapi.resources.filediff.FileDiffResource`
        (or :py:class:`~reviewboard.webapi.resources.draft_filediff.
        DraftFileDiffResource` for commits on a review request draft) filtered
        specifically for this commit.

        Args:
            commit (reviewboard.diffviewer.models.diffcommit.DiffCommit):
                The commit to retrieve the link for.

            request (django.http.HttpRequest):
                The current HTTP request.

            diff_resource (reviewboard.webapi.resources.diff.DiffResource):
                Either the diff resource (if this is the diff commit resource)
                or the draft diff resource (if this is the draft diff commit
                resource).

            filediff_resource (reviewboard.webapi.resources.filediff.
                               FileDiffResource):
                Either the filedif resource (if this is the diff commit
                resource) or the draft filediff resource (if this is the draft
                diff commit resource).

            files_key (unicode):
                The key that maps to the files link in the ``links`` field of
                the ``diff_resource``.

            *args (tuple):
                Additional positional argument.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The link information for the file resource that contains only the
            :py:class:`FileDiffs
            <reviewboard.diffviewer.models.filediff.FileDiff>` of the
            requested commit.
        """
        files_link = diff_resource.get_links(
            [filediff_resource],
            commit.diffset,
            request,
            *args,
            **kwargs)[files_key]

        files_link['href'] = '%s?%s' % (
            files_link['href'],
            urlencode({'commit-id': commit.commit_id}),
        )

        return files_link

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Return the related links for the resource.

        If this is for an item resource, this will return links for all the
        associated
        :py:class:`~reviewboard.diffviewer.models.filediff.FileDiffs`.

        Args:
            obj (reviewboard.diffviewer.models.diffcommit.DiffCommit,
                 optional):
                The DiffCommit to get links for.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            The related links.
        """
        links = {}

        if obj is not None and request:
            links['files'] = self._get_files_link(
                commit=obj,
                request=request,
                diff_resource=resources.diff,
                filediff_resource=resources.filediff,
                files_key='files',
                *args,
                **kwargs)

        return links


diffcommit_resource = DiffCommitResource()
