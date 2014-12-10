from __future__ import unicode_literals

from django.db.models import Q
from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.diffviewer.errors import (DiffParserError,
                                           DiffTooBigError,
                                           EmptyDiffError)
from reviewboard.diffviewer.models import DiffSet
from reviewboard.scmtools.models import Repository
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
from reviewboard.webapi.resources.diff import DiffResource


class ValidateDiffResource(DiffResource):
    """Verifies whether a diff file will work.

    This allows clients to validate whether a diff file (with optional parent
    diff) can be parsed and displayed, without actually creating a review
    request first.
    """
    added_in = '2.0'

    singleton = True
    name = 'diff_validation'
    uri_name = 'diffs'
    uri_object_key = None

    allowed_methods = ('GET', 'POST',)

    item_child_resources = []
    list_child_resources = []

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns links for using this resource."""
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
            'repository': {
                'type': six.text_type,
                'description': 'The path or ID of the repository.',
            },
            'path': {
                'type': file,
                'description': 'The main diff file.',
            },
        },
        optional={
            'basedir': {
                'type': six.text_type,
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
        }
    )
    def create(self, request, repository, basedir=None, local_site_name=None,
               *args, **kwargs):
        """Validate a diff.

        This API has a similar signature to the ReviewRequest resource POST
        API, but instead of actually creating a review request, will return
        either OK or an error, depending on whether the included diff file
        parsed correctly.
        """
        local_site = self._get_local_site(local_site_name)

        path = request.FILES.get('path')
        parent_diff_path = request.FILES.get('parent_diff_path')

        try:
            query = Q(pk=int(repository), local_site=local_site)
        except ValueError:
            query = (Q(local_site=local_site)
                     & (Q(path=repository)
                        | Q(mirror_path=repository)
                        | Q(name=repository)))

        try:
            repository = Repository.objects.get(query)
        except Repository.DoesNotExist:
            return INVALID_REPOSITORY, {
                'repository': repository
            }

        if (not repository.get_scmtool().get_diffs_use_absolute_paths() and
            basedir is None):

            return INVALID_FORM_DATA, {
                'fields': {
                    'basedir': 'Given repository requires a base directory',
                },
            }

        if basedir is None:
            # If we get here, the repository uses absolute paths. Deeper down
            # (where we don't necessarily know about the details of the
            # repository), we do an os.path.join() with the basedir value,
            # which will choke if it's None.
            basedir = ''

        try:
            DiffSet.objects.create_from_upload(
                repository, path, parent_diff_path, None, basedir, request,
                save=False)
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
                'reason': six.text_type(e),
            }

        return 200, {}

    def _build_named_url(self, name):
        """Builds a Django URL name from the provided name."""
        return 'validate-diffs-resource'


validate_diff_resource = ValidateDiffResource()
