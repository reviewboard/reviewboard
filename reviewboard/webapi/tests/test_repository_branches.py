import os

from djblets.testing.decorators import add_fixtures

from reviewboard import scmtools
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.errors import REPO_NOT_IMPLEMENTED
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class RepositoryBranchesResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryBranchesResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    item_mimetype = _build_mimetype('repository-branches')

    def test_get_repository_branches(self):
        """Testing the GET repositories/<id>/branches/ API"""
        rsp = self.apiGet(self.get_url(self.repository),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['branches'],
            [
                {'name': 'trunk', 'commit': '5', 'default': True},
                {'name': 'branch1', 'commit': '7', 'default': False},
            ])

    @add_fixtures(['test_site'])
    def test_get_repository_branches_with_site(self):
        """Testing the GET repositories/<id>/branches/ API with a local site"""
        self._login_user(local_site=True)
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        rsp = self.apiGet(self.get_url(self.repository, self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['branches'],
            [
                {'name': 'trunk', 'commit': '5', 'default': True},
                {'name': 'branch1', 'commit': '7', 'default': False},
            ])

    @add_fixtures(['test_site'])
    def test_get_repository_branches_with_site_no_access(self):
        """Testing the GET repositories/<id>/branches/ API with a local site and Permission Denied error"""
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        self.apiGet(self.get_url(self.repository, self.local_site_name),
                    expected_status=403)

    def test_get_repository_branches_with_no_support(self):
        """Testing the GET repositories/<id>/branches/ API with a repository that does not implement it"""
        hg_repo_path = os.path.join(os.path.dirname(scmtools.__file__),
                                    'testdata', 'hg_repo.bundle')
        repository = Repository(name='Test HG',
                                path=hg_repo_path,
                                tool=Tool.objects.get(name='Mercurial'))
        repository.save()

        rsp = self.apiGet(self.get_url(repository),
                          expected_status=501)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_NOT_IMPLEMENTED.code)

    def get_url(self, repository, local_site_name=None):
        return local_site_reverse('branches-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'repository_id': repository.pk,
                                  })
