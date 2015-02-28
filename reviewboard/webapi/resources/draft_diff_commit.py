from __future__ import unicode_literals

import logging

from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)

from reviewboard.diffviewer.errors import DiffTooBigError, EmptyDiffError
from reviewboard.diffviewer.forms import UploadDiffCommitForm
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_login_required,
                                           webapi_response_errors)
from reviewboard.webapi.errors import (DIFF_EMPTY,
                                       DIFF_TOO_BIG,
                                       REPO_FILE_NOT_FOUND)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.diff_commit import DiffCommitResource


class DraftDiffCommitResource(DiffCommitResource):
    """Provides information on pending draft commits for a review request.

    POSTing to this resource will update a review request draft with the
    provided diff.
    """
    added_in = '3.0'

    name = 'draft_diff_commit'

    mimetype_item_resource_name = 'diff-commit'
    mimetype_list_resource_name = 'diff-commits'

    allowed_methods = ('GET', 'POST', 'PUT')

    def get_queryset(self, request, *args, **kwargs):
        try:
            diffset = resources.draft_diff.get_object(request, *args, **kwargs)
        except DiffSet.DoesNotExist:
            return self.model.objects.none()

        return self.model.objects.filter(diffset=diffset)

    def has_access_permissions(self, request, commit, *args, **kwargs):
        draft = ReviewRequestDraft.objects.get(diffset__diff_commits=commit)
        return draft.is_accessible_by(request.user)

    def has_list_access_permissions(self, request, *args, **kwargs):
        review_request = resources.review_request.get_object(request, *args,
                                                             **kwargs)

        return review_request.is_accessible_by(request.user)

    @webapi_login_required
    @augment_method_from(DiffCommitResource)
    def get(self, request, *args, **kwargs):
        """Return the information on a particular commit.

        This currently only returns the metadata associated with the commit.
        """
        pass

    @webapi_login_required
    @augment_method_from(DiffCommitResource)
    def get_list(self, request, *args, **kwargs):
        """Get the list of commits on the draft diff revision.."""
        pass

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA, DIFF_EMPTY, DIFF_TOO_BIG,
                            REPO_FILE_NOT_FOUND, DOES_NOT_EXIST,
                            INVALID_ATTRIBUTE)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The main diff to upload.',
            },
            'commit_id': {
                'type': six.text_type,
                'description': 'The ID/revision of the commit to upload.',
            },
            'parent_id': {
                'type': six.text_type,
                'description': 'The parent revision of this commit.',
            },
            'description': {
                'type': six.text_type,
                'description': 'The commit message.',
            },
            'author_name': {
                'type': six.text_type,
                'description': 'The name of the author of this commit.',
            },
            'author_email': {
                'type': six.text_type,
                'description': 'The e-mail address of the author of this '
                               'commit.',
            },
            'author_date': {
                'type': six.text_type,
                'description': 'The date and time this commit was authored in '
                               'ISO 8601 format.',
            },
            'commit_type': {
                'type': ('merge', 'change'),
                'description': 'The type of this commit.',
            },
        },
        optional={
            'parent_diff_path': {
                'type': file,
                'description': 'The optional parent diff to upload.',
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
                'description': 'The date and time this commit was committed '
                               'in ISO 8601 format.'
            },
            'base_commit_id': {
                'type': six.text_type,
                'description': 'The ID/revision this change is built upon. '
                               'If using a parent diff, then this is the base '
                               'for that diff. This may not be provided for '
                               'all diffs or repository types, depending on '
                               'how the diff was uploaded.',
            },
            'merge_parent_ids': {
                'type': six.text_type,
                'description': 'The other parents of this commit if it is a '
                               'merge commit.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, extra_fields=None, *args, **kwargs):
        """Creates a new commit resource instance by parsing an uploaded diff.

        This accepts a unified diff file, validates it, and stores it under the
        parent diff revision of a review request draft. See the documentation
        for :ref:`webapi2.0-diff-resource` for further information with regards
        to diffs.

        A parent diff revision must be created before POSTing to this resource.
        The parent diff revision should be created via the ``with_history``
        flag set to true so that it is created empty.

        Upload of multiple commits to this resource should be done in the order
        of a topological sorting of the directed acyclic graph they correspond
        to. That is, in a linear sequence of commits, they must be uploaded in
        a linear order. If a merge commit is to be uploaded, both parent
        commits must have been uploaded before it so that it can be applied.

        Extra data can be stored on the diff for later lookup by passing
        ``extra_data.key_name=value``. The ``key_name`` and ``value`` can be
        any valid strings. Passing a blank ``value`` will remove the key. The
        ``extra_data.`` prefix is required.
        """
        try:
            review_request = resources.review_request.get_object(request,
                                                                 *args,
                                                                 **kwargs)
        except ReviewRequest.DoesNotExit:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self._no_access_error(request.user)

        if review_request.repository is None:
            return INVALID_ATTRIBUTE, {
                'reason': 'This review request was created as attachments-'
                          'only, with no repository.'
            }

        try:
            draft = review_request.draft.get()
            diffset = draft.diffset

            if diffset.diff_commit_count == 0 and diffset.files.count() > 0:
                return INVALID_ATTRIBUTE, {
                    'reason': 'The DiffSet for this commit contains filediffs '
                              'and no commits. It must be empty to allow '
                              'uploading of individual commits.'
                }
        except ReviewRequestDraft.DoesNotExist:
            return DOES_NOT_EXIST, {
                'reason': 'Review request draft does not exist.'
            }
        except DiffSet.DoesNotExist:
            return DOES_NOT_EXIST, {
                'reason': 'Diff set does not exist.'
            }

        form_data = request.POST.copy()
        form = UploadDiffCommitForm(review_request, data=form_data,
                                    files=request.FILES, request=request)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form)
            }

        try:
            commit = form.create(diffset, request.FILES['path'],
                                 request.FILES.get('parent_diff_path'))
        except FileNotFoundError as e:
            return REPO_FILE_NOT_FOUND, {
                'file': e.path,
                'revision': six.text_type(e.revision)
            }
        except EmptyDiffError:
            return DIFF_EMPTY
        except DiffTooBigError as e:
            return DIFF_TOO_BIG, {
                'reason': six.text_type(e),
                'max_size': e.max_diff_size,
            }
        except Exception as e:
            logging.error('Error uploading new diff: %s', e, exc_info=1,
                          request=request)

            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [six.text_type(e)]
                }
            }

        if extra_fields:
            self.import_extra_data(commit, commit.extra_data, extra_fields)
            commit.save(update_fields=['extra_data'])

        return 201, {
            self.item_result_key: commit,
        }

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        if obj and request:
            return self._get_files_links(obj, request, resources.draft_diff,
                                         resources.draft_filediff,
                                         'draft_files', *args, **kwargs)
        else:
            return {}

draft_diff_commit_resource = DraftDiffCommitResource()
