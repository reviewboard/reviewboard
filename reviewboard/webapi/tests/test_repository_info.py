from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import repository_info_item_mimetype
from reviewboard.webapi.tests.urls import get_repository_info_url


class RepositoryInfoResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryInfoResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_repository_info(self):
        """Testing the GET repositories/<id>/info API"""
        repository = self.create_repository(tool_name='Subversion')
        rsp = self.apiGet(get_repository_info_url(repository),
                          expected_mimetype=repository_info_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site(self):
        """Testing the GET repositories/<id>/info API with a local site"""
        self._login_user(local_site=True)
        repository = self.create_repository(with_local_site=True,
                                            tool_name='Subversion')

        rsp = self.apiGet(
            get_repository_info_url(repository, self.local_site_name),
            expected_mimetype=repository_info_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site_no_access(self):
        """Testing the GET repositories/<id>/info API with a local site and Permission Denied error"""
        repository = self.create_repository(with_local_site=True)

        self.apiGet(
            get_repository_info_url(repository, self.local_site_name),
            expected_status=403)
