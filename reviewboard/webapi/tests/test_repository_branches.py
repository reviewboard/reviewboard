from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.errors import REPO_NOT_IMPLEMENTED
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    repository_branches_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_repository_branches_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryBranchesResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/branches/'
    resource = resources.repository_branches

    def setup_http_not_allowed_list_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_branches_url(repository)

    def setup_http_not_allowed_item_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_branches_url(repository)

    def compare_item(self, item_rsp, branch):
        self.assertEqual(item_rsp, branch)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Test',
                                            with_local_site=with_local_site)

        return (get_repository_branches_url(repository, local_site_name),
                repository_branches_item_mimetype,
                [
                    {
                        'id': 'trunk',
                        'name': 'trunk',
                        'commit': '5',
                        'default': True
                    },
                    {
                        'id': 'branch1',
                        'name': 'branch1',
                        'commit': '7',
                        'default': False
                    },
                ])

    def test_get_with_no_support(self):
        """Testing the GET repositories/<id>/branches/ API
        with a repository that does not implement it
        """
        repository = self.create_repository(tool_name='CVS')

        rsp = self.api_get(get_repository_branches_url(repository),
                           expected_status=501)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_NOT_IMPLEMENTED.code)
