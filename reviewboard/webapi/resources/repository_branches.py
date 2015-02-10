from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from djblets.webapi.decorators import webapi_response_errors
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.scmtools.errors import SCMError
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import REPO_INFO_ERROR, REPO_NOT_IMPLEMENTED
from reviewboard.webapi.resources import resources


class RepositoryBranchesResource(WebAPIResource):
    """Provides information on the branches in a repository.

    Returns an array of objects with the following fields:

        'id' is the ID of the branch.

        'name' is simply the name of the branch.

        'commit' is a string representing the revision identifier of the
        commit, and the format depends on the repository type (it may contain
        an integer, SHA-1 hash, or other type). This should be treated as a
        relatively opaque value, but can be used as the "start" parameter to
        the repositories/<id>/commits/ resource.

        'default' will be true for exactly one of the results, and false for
        all the others. This represents whichever branch is considered the tip
        (such as "master" for git repositories, or "trunk" for subversion).

    This is not available for all types of repositories.
    """
    added_in = '2.0'

    name = 'branches'
    policy_id = 'repository_branches'
    singleton = True
    allowed_methods = ('GET',)
    mimetype_item_resource_name = 'repository-branches'

    @webapi_check_local_site
    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST, REPO_INFO_ERROR,
                            REPO_NOT_IMPLEMENTED)
    def get(self, request, *args, **kwargs):
        """Retrieves an array of the branches in a repository."""
        try:
            repository = resources.repository.get_object(request, *args,
                                                         **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            branches = []
            for branch in repository.get_branches():
                branches.append({
                    'id': branch.id,
                    'name': branch.name,
                    'commit': branch.commit,
                    'default': branch.default,
                })

            return 200, {
                self.item_result_key: branches,
            }
        except SCMError as e:
            return REPO_INFO_ERROR.with_message(six.text_type(e))
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED


repository_branches_resource = RepositoryBranchesResource()
