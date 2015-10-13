from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.utils import six
from djblets.webapi.decorators import (webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import SCMError
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.errors import REPO_INFO_ERROR, REPO_NOT_IMPLEMENTED
from reviewboard.webapi.resources import resources


class RepositoryCommitsResource(WebAPIResource):
    """Provides information on the commits in a repository.

    Get a single page of commit history from the repository. This will usually
    be 30 items, but the exact count is dependent on the repository type. The
    'start' parameter is the id of the most recent commit to start fetching log
    information from.

    Successive pages of commit history can be fetched by using the 'parent'
    field of the last entry as the 'start' parameter for another request.

    Returns an array of objects with the following fields:

        'author_name' is a string with the author's real name or user name,
        depending on the repository type.

        'id' is a string representing the revision identifier of the commit,
        and the format depends on the repository type (it may contain an
        integer, SHA-1 hash, or other type).

        'date' is an ISO8601-formatted string.

        'message' is a string with the commit message, if any.

        'parent' is a string with the id of the parent revision. This may be
        the empty string for the first revision in the commit history. The
        parent

    This is not available for all types of repositories.
    """
    added_in = '2.0'

    name = 'commits'
    policy_id = 'repository_commits'
    singleton = True
    allowed_methods = ('GET',)
    mimetype_item_resource_name = 'repository-commits'

    @webapi_check_local_site
    @webapi_check_login_required
    @webapi_response_errors(DOES_NOT_EXIST, REPO_INFO_ERROR,
                            REPO_NOT_IMPLEMENTED)
    @webapi_request_fields(
        optional={
            'branch': {
                'type': six.text_type,
                "description": "The ID of the branch to limit the commits "
                               "to, as provided by the 'id' field of the "
                               "repository branches API.",
                'added_in': '2.5',
            },
            'start': {
                'type': six.text_type,
                'description': 'A commit ID to start listing from.',
            },
        }
    )
    def get(self, request, branch=None, start=None, *args, **kwargs):
        """Retrieves a set of commits from a particular repository.

        The ``start`` parameter is a commit ID to use as a starting point. This
        allows both pagination and logging of different branches. Successive
        pages of commit history can be fetched by using the ``parent`` field of
        the last entry as the ``start`` parameter for another request.
        """
        try:
            repository = resources.repository.get_object(request, *args,
                                                         **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            items = repository.get_commits(branch=branch, start=start)
        except SCMError as e:
            return REPO_INFO_ERROR.with_message(six.text_type(e))
        except NotImplementedError:
            return REPO_NOT_IMPLEMENTED

        commits = []
        commit_ids = []
        for commit in items:
            commits.append({
                'author_name': commit.author_name,
                'id': commit.id,
                'date': commit.date,
                'message': commit.message,
                'parent': commit.parent,
            })
            commit_ids.append(commit.id)

        by_commit_id = {}
        for obj in ReviewRequest.objects.filter(repository=repository,
                                                commit_id__in=commit_ids):
            by_commit_id[obj.commit_id] = obj

        for commit in commits:
            try:
                review_request = by_commit_id[commit['id']]
                commit['review_request_url'] = \
                    review_request.get_absolute_url()
            except KeyError:
                commit['review_request_url'] = ''

        return 200, {
            self.item_result_key: commits,
        }


repository_commits_resource = RepositoryCommitsResource()
