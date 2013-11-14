from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.decorators import webapi_response_errors
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import REPO_NOT_IMPLEMENTED
from reviewboard.webapi.resources import resources


class RepositoryBranchesResource(WebAPIResource):
    """Provides information on the branches in a repository.

    Returns an array of objects with the following fields:

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
    name = 'branches'
    singleton = True
    allowed_methods = ('GET',)
    mimetype_item_resource_name = 'repository-branches'

    @webapi_check_local_site
    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST, REPO_NOT_IMPLEMENTED)
    def get(self, request, *args, **kwargs):
        try:
            repository = resources.repository.get_object(request, *args,
                                                         **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            branches = []
            for branch in repository.get_branches():
                branches.append({
                    'name': branch.name,
                    'commit': branch.commit,
                    'default': branch.default,
                })

            return 200, {
                self.item_result_key: branches,
            }
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED


repository_branches_resource = RepositoryBranchesResource()
