from __future__ import unicode_literals

import os

from djblets.testing.decorators import add_fixtures
from djblets.util.compat import six
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.webapi.resources import resources
from reviewboard.webapi.errors import REPO_NOT_IMPLEMENTED
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import repository_commits_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_repository_commits_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryCommitsResource APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/commits/'
    resource = resources.repository_commits
    test_http_methods = ('DELETE', 'POST', 'PUT')

    def setup_http_not_allowed_list_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_commits_url(repository)

    def setup_http_not_allowed_item_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_commits_url(repository)

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the GET repositories/<id>/commits/ API"""
        repository = self.create_repository(tool_name='Test')

        rsp = self.apiGet(get_repository_commits_url(repository),
                          query={'start': 5},
                          expected_mimetype=repository_commits_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['commits']), 5)
        self.assertEqual(rsp['commits'][0]['message'], 'Commit 5')
        self.assertEqual(rsp['commits'][3]['author_name'], 'user2')

    def test_get_without_start(self):
        """Testing the GET repositories/<id>/commits/ API
        without providing a start parameter
        """
        repository = self.create_repository()
        rsp = self.apiGet(get_repository_commits_url(repository),
                          expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('start' in rsp['fields'])

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET repositories/<id>/commits/ API with a local site"""
        self._login_user(local_site=True)
        repository = self.create_repository(with_local_site=True,
                                            tool_name='Test')

        rsp = self.apiGet(
            get_repository_commits_url(repository, self.local_site_name),
            query={'start': 7},
            expected_mimetype=repository_commits_item_mimetype)
        self.assertEqual(len(rsp['commits']), 7)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['commits'][0]['id'], '7')
        self.assertEqual(rsp['commits'][1]['message'], 'Commit 6')

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET repositories/<id>/commits/ API
        with a local site and Permission Denied error
        """
        repository = self.create_repository(with_local_site=True)

        self.apiGet(
            get_repository_commits_url(repository, self.local_site_name),
            expected_status=403)

    def test_get_with_no_support(self):
        """Testing the GET repositories/<id>/commits/ API
        with a repository that does not implement it
        """
        repository = self.create_repository(tool_name='CVS')
        repository.save()

        rsp = self.apiGet(
            get_repository_commits_url(repository),
            query={'start': ''},
            expected_status=501)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_NOT_IMPLEMENTED.code)
