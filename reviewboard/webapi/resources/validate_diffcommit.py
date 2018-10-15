"""The DiffCommit validation resource."""

from __future__ import unicode_literals

import base64
import json
import logging

from django.db.models import Q
from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_ATTRIBUTE,
                                   INVALID_FORM_DATA, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import FileFieldType, StringFieldType

from reviewboard.diffviewer.commit_utils import (serialize_validation_info,
                                                 update_validation_info)
from reviewboard.diffviewer.errors import (DiffParserError,
                                           DiffTooBigError,
                                           EmptyDiffError)
from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.forms import ValidateCommitForm
from reviewboard.diffviewer.models import FileDiff
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.scmtools.git import ShortSHA1Error
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.errors import (DIFF_EMPTY, DIFF_PARSE_ERROR,
                                       DIFF_TOO_BIG, INVALID_REPOSITORY,
                                       REPO_FILE_NOT_FOUND)


logger = logging.getLogger(__name__)


class ValidateDiffCommitResource(WebAPIResource):
    """Verifies whether or not a diff file for a commit will work.

    This allows clients to validate whether or not diff files for commits can
    be parsed and displayed without actually creating a review request first.
    """

    added_in = '4.0'

    singleton = True
    name = 'commit_validation'
    uri_name = 'commits'
    uri_object_key = None
    model = None

    allowed_methods = ('GET', 'POST')

    required_features = [dvcs_feature]

    item_child_resources = []
    list_child_resources = []

    fields = {
        'validation_info': {
            'type': StringFieldType,
            'description': (
                'Validation metdata to pass to this resource to help validate '
                'the next commit.'
            ),
        },
    }

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Return links for using this resource."""
        return 200, {
            'links': self.get_links(request=request, *args, **kwargs),
        }

    @webapi_login_required
    @webapi_check_local_site
    @webapi_response_errors(
        DIFF_EMPTY,
        DIFF_PARSE_ERROR,
        DIFF_TOO_BIG,
        DOES_NOT_EXIST,
        INVALID_ATTRIBUTE,
        INVALID_FORM_DATA,
        INVALID_REPOSITORY,
        NOT_LOGGED_IN,
        REPO_FILE_NOT_FOUND,
        PERMISSION_DENIED
    )
    @webapi_request_fields(
        required={
            'repository': {
                'type': StringFieldType,
                'description': 'The path or ID of the repository.',
            },
            'diff': {
                'type': FileFieldType,
                'description': 'The diff file to validate.',
            },
            'commit_id': {
                'type': StringFieldType,
                'description': 'The ID of the commit being validated.',
            },
            'parent_id': {
                'type': StringFieldType,
                'description': 'The ID of the parent commit.',
            },
        },
        optional={
            'base_commit_id': {
                'type': StringFieldType,
                'description': 'The base commit ID.',
            },
            'parent_diff': {
                'type': FileFieldType,
                'description': (
                    'The parent diff of the commit being validated.\n'
                ),
            },
            'validation_info': {
                'type': StringFieldType,
                'description': (
                    'Validation metadata from a previous call to this API.\n'
                    '\n'
                    'This field is required for all but the first commit in a '
                    'series.'
                ),
            },
        }
    )
    def create(self, request, repository, commit_id, parent_id,
               base_commit_id=None, local_site_name=None, *args, **kwargs):
        """Validate a diff for a commit.

        This API has a similar signature to the :ref:`Draft DiffCommit resource
        <webapi2.0-draft-diff-commit-list-resource>` POST API, but instead of
        actually creating commits, it will return a result representing whether
        or not the included diff file parsed and validated correctly.

        This API must be called before posting to the :ref:`Draft DiffCommit
        resource <webapi2.0-draft-diff-commit-list-resource>` because the
        ``validation_info`` field returned by this resource is required for
        posting to that resource.
        """
        local_site = self._get_local_site(local_site_name)

        try:
            q = Q(pk=int(repository))
        except ValueError:
            q = (Q(path=repository) |
                 Q(mirror_path=repository) |
                 Q(name=repository))

        repository_qs = (
            Repository.objects
            .accessible(request.user, local_site=local_site)
            .filter(q)
        )
        repository_count = len(repository_qs)

        if repository_count == 0:
            return INVALID_REPOSITORY, {
                'repository': repository,
            }
        elif repository_count > 1:
            msg = (
                'Too many repositories matched "%s". Try specifying the '
                'repository by name instead.'
                % repository
            )

            return INVALID_REPOSITORY.with_message(msg), {
                'repository': repository,
            }

        repository = repository_qs.first()

        if not repository.scmtool_class.supports_history:
            return INVALID_ATTRIBUTE, {
                'reason': (
                    'The "%s" repository does not support review requests '
                    'created with history.'
                    % repository.name
                ),
            }

        form = ValidateCommitForm(repository=repository,
                                  request=request,
                                  data=request.POST,
                                  files=request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        try:
            filediffs = form.validate_diff()
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
            return DIFF_PARSE_ERROR.with_message(six.text_type(e))
        except Exception as e:
            logger.exception(
                'Unexpected exception occurred while validating commit "%s" '
                'in repository "%s" (id %d) with base_commit_id="%s"',
                commit_id,
                repository.name,
                repository.pk,
                base_commit_id,
                request=request)
            return DIFF_PARSE_ERROR.with_message(
                'Unexpected error while validating the diff: %s' % e)

        validation_info = update_validation_info(
            form.cleaned_data.get('validation_info', {}),
            commit_id,
            parent_id,
            filediffs)

        return 200, {
            self.item_result_key: {
                'validation_info': serialize_validation_info(
                    validation_info),
            }
        }


validate_diffcommit_resource = ValidateDiffCommitResource()
