"""Resources representing commits on a multi-commit review request draft."""

from __future__ import unicode_literals

import logging

from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA)
from djblets.webapi.fields import (DateTimeFieldType,
                                   FileFieldType,
                                   StringFieldType)

from reviewboard.diffviewer.errors import DiffTooBigError, EmptyDiffError
from reviewboard.reviews.forms import UploadCommitForm
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.core import FileNotFoundError
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_login_required,
                                           webapi_response_errors)
from reviewboard.webapi.errors import (DIFF_EMPTY,
                                       DIFF_TOO_BIG,
                                       REPO_FILE_NOT_FOUND)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.diffcommit import DiffCommitResource


logger = logging.getLogger(__name__)


class DraftDiffCommitResource(DiffCommitResource):
    """Provides information on pending draft commits for a review request.

    POSTing to this resource will update a review request draft with the
    provided diff.
    """

    name = 'draft_commit'
    model_parent_key = 'diffset'

    allowed_methods = ('GET', 'POST', 'PUT')

    def get_queryset(self, request, *args, **kwargs):
        """Return a QuerySet limited to the review request draft.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            The generated QuerySet.
        """
        try:
            draft = resources.review_request_draft.get_object(request, *args,
                                                              **kwargs)
        except ReviewRequestDraft.DoesNotExist:
            return self.model.objects.none()

        if draft.diffset_id is None:
            return self.model.objects.none()

        return self.model.objects.filter(diffset__pk=draft.diffset_id)

    def has_access_permissions(self, request, commit, *args, **kwargs):
        """Return whether or not the user has access permissions to the commit.

        A user has access permissions for a commit if they have permission to
        access the review request draft.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

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
        draft = resources.review_request_draft.get_object(request, *args,
                                                          **kwargs)
        return draft.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Return whether the user has access permissions to the list resource.

        A user has list access permissions if they have premission to access
        the review request draft.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

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
        draft = resources.review_request_draft.get_object(request, *args,
                                                          **kwargs)
        return draft.is_accessible_by(request.user)

    def has_modify_permissions(self, request, commit, *args, **kwargs):
        """Return whether the user has access permissions to modify the object.

        A user has modify permissions for a commit if they have permission to
        modify the review request draft.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

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
        draft = resources.review_request_draft.get_object(request, *args,
                                                          **kwargs)
        return draft.is_mutable_by(request.user)

    @webapi_login_required
    @augment_method_from(DiffCommitResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_login_required
    @augment_method_from(DiffCommitResource)
    def get_list(self, *args, **kwargs):
        pass

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(DIFF_EMPTY, DIFF_TOO_BIG, DOES_NOT_EXIST,
                            INVALID_ATTRIBUTE, INVALID_FORM_DATA,
                            REPO_FILE_NOT_FOUND)
    @webapi_request_fields(
        required={
            'diff': {
                'type': FileFieldType,
                'description': 'The corresponding diff for this commit.',
            },
            'commit_id': {
                'type': StringFieldType,
                'description': 'The ID of this commit.',
            },
            'author_name': {
                'type': StringFieldType,
                'description': 'The name of the author of this commit.',
            },
            'author_date': {
                'type': DateTimeFieldType,
                'description': 'The date and time this commit was authored in '
                               'ISO 8601 format (YYYY-MM-DD HH:MM:SS+ZZZZ).',
            },
            'author_email': {
                'type': StringFieldType,
                'description': 'The e-mail address of the author of this '
                               'commit.',
            },
            'commit_message': {
                'type': StringFieldType,
                'description': 'The commit message.',
            },
        },
        optional={
            'committer_name': {
                'type': StringFieldType,
                'description': (
                    'The name of the the committer of this commit, if '
                    'applicable.\n'
                    '\n'
                    'If this field is specified, the "committer_date" and '
                    '"committer_email" fields must also be specified.'
                ),
            },
            'committer_date': {
                'type': StringFieldType,
                'description': (
                    'The date and time this commit was committed in ISO 8601 '
                    'format (YYYY-MM-DD HH:MM:SS+ZZZZ).\n'
                    '\n'
                    'If this field is specified, the "committer_name" and '
                    '"committer_email" fields must also be specified.'
                ),
            },
            'committer_email': {
                'type': StringFieldType,
                'description': (
                    'The e-mail address of the committer of this commit.\n'
                    '\n'
                    'If this field is specified, the "committer_name" and '
                    '"committer_date" fields must also be specified.'
                ),
            },
            'parent_diff': {
                'type': FileFieldType,
                'description': 'The optional parent diff to upload.',
            },
            'validation_info': {
                'type': StringFieldType,
                'description': (
                    'Validation metadata from the :ref:`DiffCommit validation '
                    'resource <webapi2.0-validate-diff-commit-resource>`.'
                    '\n\n'
                    'This is required for all but the first commit.'
                ),
            },
        },
        allow_unknown=True
    )
    @webapi_check_local_site
    def create(self, request, extra_fields=None, *args, **kwargs):
        """Create a new commit.

        A draft must exist and the review request must be created with history
        support in order to post to this resource.
        """
        try:
            review_request = resources.review_request.get_object(
                request, *args, **kwargs)
        except ReviewRequest.DoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_modify_permissions(request, review_request, *args,
                                           **kwargs):
            return self.get_no_access_error(request)

        if review_request.repository is None:
            return INVALID_ATTRIBUTE, {
                'reason': 'This review request was created as attachments-'
                          'only, with no repository.',
            }
        elif not review_request.created_with_history:
            reverse_kwargs = {
                'review_request_id': kwargs['review_request_id'],
            }

            if request.local_site:
                reverse_kwargs['local_site_name'] = request.local_site.name

            return INVALID_ATTRIBUTE, {
                'reason': (
                    'This review request was not created with support for '
                    'multiple commits.\n\n'
                    'Use the %(name)s resource to upload diffs instead. See '
                    'the %(name)s link on the parent resource for the URL.'
                    % {
                        'name': resources.draft_diff.name,
                    }
                ),
            }

        try:
            draft = review_request.draft.get()
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST, {
                'reason': 'Review request draft does not exist.',
            }

        diffset = draft.diffset

        if diffset is None:
            return DOES_NOT_EXIST, {
                'reason': 'An empty diff must be created first.',
            }
        elif diffset.is_commit_series_finalized:
            return INVALID_ATTRIBUTE, {
                'reason': 'The diff has already been finalized.',
            }

        form = UploadCommitForm(
            review_request=review_request,
            diffset=diffset,
            request=request,
            data=request.POST.copy(),
            files=request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        try:
            commit = form.create()
        except FileNotFoundError as e:
            return REPO_FILE_NOT_FOUND, {
                'file': e.path,
                'revision': six.text_type(e.revision),
            }
        except EmptyDiffError as e:
            return DIFF_EMPTY
        except DiffTooBigError as e:
            return DIFF_TOO_BIG, {
                'reason': six.text_type(e),
                'max_size': e.max_diff_size,
            }
        except Exception as e:
            logger.exception('Error uploading new commit: %s', e,
                             request=request)

            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [six.text_type(e)],
                },
            }

        return 201, {
            self.item_result_key: commit,
        }

    def get_related_links(self, obj, request=None, *args, **kwargs):
        """Return the related links for the resource.

        If this is for an item resource, this will return links for all the
        associated FileDiffs.

        Args:
            obj (reviewboard.diffviewer.models.DiffCommit, optional):
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

        if obj and request:
            links['draft_files'] = self._get_files_link(
                commit=obj,
                request=request,
                diff_resource=resources.draft_diff,
                filediff_resource=resources.draft_filediff,
                files_key='draft_files',
                *args,
                **kwargs)

        return links


draft_diffcommit_resource = DraftDiffCommitResource()
