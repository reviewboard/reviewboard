from __future__ import unicode_literals

import logging

from django.utils import six
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site,
                                           webapi_login_required,
                                           webapi_response_errors)
from reviewboard.webapi.resources import resources


class DiffCommitResource(WebAPIResource):
    """Provides information on a collection of commits.

    Each diff commit resource contains individual per-file diffs as child
    resources as well as metadata to reproduce the actual commits in a version
    control system.
    """
    added_in = '3.0'

    model = DiffCommit

    name = 'diff_commit'
    uri_name = 'commits'

    model_parent_key = 'diffset'

    model_object_key = 'commit_id'
    uri_object_key = 'commit_id'
    uri_object_key_regex = DiffCommit.COMMIT_ID_RE

    allowed_methods = ('GET', 'PUT')

    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the commit resource.',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the commit. This can be set '
                           'by the API or extensions.',
        },
        'name': {
            'type': six.text_type,
            'description': 'The name of the corresponding diff.',
        },
        'commit_id': {
            'type': six.text_type,
            'description': 'The ID/revision of this commit.',
        },
        'parent_id': {
            'type': six.text_type,
            'description': "The ID/revision of this commit's parent.",
        },
        'merge_parent_ids': {
            'type': list,
            'description': 'A list of merge parents of this commit.',
        },
        'author_name': {
            'type': six.text_type,
            'description': 'The name of the author of this commit.',
        },
        'author_email': {
            'type': six.text_type,
            'description': 'The e-mail address of the author of this commit.',
        },
        'author_date': {
            'type': six.text_type,
            'description': 'The date and time this commit was authored in ISO '
                           '8601 format (YYYY-MM-DD HH:MM:SS+ZZZZ).',
        },
        'committer_name': {
            'type': six.text_type,
            'description': 'The name of the committer of this commit.',
        },
        'committer_email': {
            'type': six.text_type,
            'description': 'The e-mail address of the committer of this '
                           'commit.',
        },
        'committer_date': {
            'type': six.text_type,
            'description': 'The date and time this commit was committed in '
                           'ISO 8601 format (YYYY-MM-DD HH:MM:SS+ZZZZ).',
        },
        'commit_type': {
            'type': ('merge', 'change'),
            'description': 'The type of this commit.',
        },
        'description': {
            'type': six.text_type,
            'description': 'The commit message.',
        },
    }

    def get_queryset(self, request, *args, **kwargs):
        try:
            diffset = resources.diff.get_object(request, *args, **kwargs)
        except DiffSet.DoesNotExist:
            return self.model.objects.none()

        return self.model.objects.filter(diffset=diffset)

    def serialize_merge_parent_ids_field(self, obj, **kwargs):
        return obj.merge_parent_ids.values_list('commit_id', flat=True)

    def serialize_author_date_field(self, obj, **kwargs):
        return obj.author_date.strftime(DiffCommit.DATE_FORMAT)

    def serialize_committer_date_field(self, obj, **kwargs):
        committer_date = obj.committer_date

        if committer_date:
            committer_date = committer_date.strftime(DiffCommit.DATE_FORMAT)

        return committer_date

    def serialize_commit_type_field(self, obj, **kwargs):
        if obj.commit_type == DiffCommit.COMMIT_CHANGE_TYPE:
            return 'change'
        elif obj.commit_type == DiffCommit.COMMIT_MERGE_TYPE:
            return 'merge'

        logging.error('Could not serialize commit_type field: unknown commit '
                      'type: %s',
                      obj.commit_type)
        raise ValueError('Unknown commit type: %s', obj.commit_type)

    def has_access_permissions(self, request, commit, *args, **kwargs):
        review_request = commit.diffset.history.review_request.get()
        return review_request.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        review_request = resources.review_request.get_object(request, *args,
                                                             **kwargs)
        return review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, commit, *args, **kwargs):
        review_request = commit.diffset.history.review_request.get()
        return review_request.is_mutable_by(request.user)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    def get(self, request, *args, **kwargs):
        """Return the information on a particular commit in a diff revision.

        This provides the metadota associated the the commit, such as the
        commit message, author, revisions, and other information available on
        the commit.
        """
        return super(DiffCommitResource, self).get(request, *args, **kwargs)

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST)
    def get_list(self, request, *args, **kwargs):
        """Returns the list of public commits."""
        return super(DiffCommitResource, self).get_list(request, *args,
                                                        **kwargs)

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(allow_unknown=True)
    def update(self, request, extra_fields={}, *args, **kwargs):
        """Updates information on the commit.

        Extra data can be stored on the diff for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can be
        any valid strings. Passing a blank ``value`` will remove the key. The
        ``extra_data.`` prefix is required.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            commit = self.get_object(request, *args, **kwargs)
        except self.model.DoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self._no_access_error(request.user)

        if extra_fields:
            self.import_extra_data(commit, commit.extra_data, extra_fields)
            commit.save(update_fields=['extra_data'])

        return 200, {
            self.item_result_key: commit
        }

    def _add_commit_id_query_parameter(self, url, commit_id):
        """Add a query parameter to filter by commit_id on the given URL."""
        if '?' in url:
            url += '&'
        else:
            url += '?'

        return '%scommit-id=%s' % (url, commit_id)

    def _get_files_links(self, commit, request, diff_resource,
                         filediff_resource, files_key, *args, **kwargs):
        """Build the files link for the given commit."""
        links = diff_resource.get_links([filediff_resource],
                                        commit.diffset,
                                        request,
                                        *args,
                                        **kwargs)

        links[files_key]['href'] = self._add_commit_id_query_parameter(
            links[files_key]['href'],
            commit.commit_id)

        return links

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        if obj and request:
            return self._get_files_links(obj, request, resources.diff,
                                         resources.filediff, 'files', *args,
                                         **kwargs)
        else:
            return {}

diff_commit_resource = DiffCommitResource()
