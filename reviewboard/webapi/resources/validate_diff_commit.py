from __future__ import unicode_literals

import logging

from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.diffviewer.errors import (DiffParserError,
                                           DiffTooBigError,
                                           EmptyDiffError)
from reviewboard.diffviewer.forms import UploadDiffCommitForm
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import (FileNotFoundError,
                                         SCMError)
from reviewboard.scmtools.git import ShortSHA1Error
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import (DIFF_EMPTY,
                                       DIFF_PARSE_ERROR,
                                       DIFF_TOO_BIG,
                                       INVALID_REPOSITORY,
                                       REPO_FILE_NOT_FOUND)
from reviewboard.webapi.resources.diff_commit import DiffCommitResource


class ValidateDiffCommitResource(DiffCommitResource):
    """Verifies if a commit will work."""

    added_in = '4.0'

    singleton = True
    name = 'diff_commit_validation'
    uri_name = 'commits'
    uri_object_key = None

    allowed_methods = ('GET', 'POST')

    item_child_resources = []
    list_child_resources = []

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Return the links for using this resource."""
        return 200, {
            'links': self.get_links(request=request, *args, **kwargs),
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            REPO_FILE_NOT_FOUND, INVALID_FORM_DATA,
                            INVALID_REPOSITORY, DIFF_EMPTY, DIFF_TOO_BIG,
                            DIFF_PARSE_ERROR)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The main diff file.',
            },
            'diff_id': {
                'type': int,
                'description': 'The ID of the diff that this commit will '
                               'belong to',
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
        })
    def create(self, request, diff_id, *args, **kwargs):
        """Validate a diff commit.

        This API has a similar signature to the commit resource POST API, but
        instead of actually creating a commit, it will return either OK or an
        error, depending on whether the included diff file parsed correctly.
        """

        try:
            diffset = DiffSet.objects.get(pk=diff_id)
        except DiffSet.DoesNotExist:
            return DOES_NOT_EXIST

        review_request = ReviewRequest.objects.get(draft__diffset=diffset)

        form = UploadDiffCommitForm(review_request, data=request.POST.copy(),
                                    files=request.FILES, request=request)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form)
            }

        try:
            form.create(diffset, request.FILES['path'],
                        request.FILES.get('parent_diff_path'), save=False)
        except FileNotFoundError as e:
            return REPO_FILE_NOT_FOUND, {
                'file': e.path,
                'revision': six.text_type(e.revision),
            }
        except EmptyDiffError:
            return DIFF_EMPTY
        except DiffTooBigError as e:
            return DIFF_TOO_BIG, {
                'reason': six.text_type(e),
                'max_size': e.max_diff_size,
            }
        except DiffParserError as e:
            return DIFF_PARSE_ERROR, {
                'reason': six.text_type(e),
                'linenum': e.linenum,
            }
        except ShortSHA1Error as e:
            return REPO_FILE_NOT_FOUND, {
                'reason': six.text_type(e),
                'file': e.path,
                'revision': six.text_type(e.revision),
            }
        except SCMError as e:
            return DIFF_PARSE_ERROR, {
                'reason': six.text_type(e)
            }
        except Exception as e:
            # If we've reached this point, we don't know what has caused it.
            logging.error('An unexpected exception occurred during commit '
                          'validation: %s',
                          e, exc_info=True)
            return INVALID_FORM_DATA, {
                'reason': six.text_type(e)
            }

        return 200, {}

    def _build_named_url(self, name):
        """Build a Django URL name from the provided name."""
        return 'validate-diff-commit-resource'


validate_diff_commit_resource = ValidateDiffCommitResource()
