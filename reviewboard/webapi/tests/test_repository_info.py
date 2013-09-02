from djblets.testing.decorators import add_fixtures

from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class RepositoryInfoResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryInfoResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    item_mimetype = _build_mimetype('repository-info')

    def test_get_repository_info(self):
        """Testing the GET repositories/<id>/info API"""
        rsp = self.apiGet(self.get_url(self.repository),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         self.repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site(self):
        """Testing the GET repositories/<id>/info API with a local site"""
        self._login_user(local_site=True)
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        rsp = self.apiGet(self.get_url(self.repository, self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         self.repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site_no_access(self):
        """Testing the GET repositories/<id>/info API with a local site and Permission Denied error"""
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        self.apiGet(self.get_url(self.repository, self.local_site_name),
                    expected_status=403)

    def get_url(self, repository, local_site_name=None):
        return local_site_reverse('info-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'repository_id': repository.pk,
                                  })
