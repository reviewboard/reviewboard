from __future__ import unicode_literals

import json

from django.utils import six
from kgb import SpyAgency

from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.repository import RemoteRepository
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.hostingsvcs.utils.paginator import APIPaginator
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    remote_repository_item_mimetype,
    remote_repository_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_remote_repository_item_url,
                                           get_remote_repository_list_url)


def _compare_item(self, item_rsp, remote_repository):
    self.assertEqual(item_rsp['id'], remote_repository.id)
    self.assertEqual(item_rsp['name'], remote_repository.name)
    self.assertEqual(item_rsp['owner'], remote_repository.owner)
    self.assertEqual(item_rsp['scm_type'], remote_repository.scm_type)
    self.assertEqual(item_rsp['path'], remote_repository.path)
    self.assertEqual(item_rsp['mirror_path'], remote_repository.mirror_path)


class RemoteRepositoryTestPaginator(APIPaginator):
    def __init__(self, results):
        self.results = results

        super(RemoteRepositoryTestPaginator, self).__init__(client=None,
                                                            url='')

    def fetch_url(self, url):
        return {
            'data': self.results,
        }


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(SpyAgency, BaseWebAPITestCase):
    """Testing the RemoteRepositoryResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'hosting-service-accounts/<id>/remote-repositories/'
    resource = resources.remote_repository
    basic_get_use_admin = True

    compare_item = _compare_item

    def setup_http_not_allowed_list_test(self, user):
        account = HostingServiceAccount.objects.create(service_name='github',
                                                       username='bob')

        return get_remote_repository_list_url(account)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='bob',
            local_site=self.get_local_site_or_none(name=local_site_name),
            data=json.dumps({
                'authorization': {
                    'token': '123',
                },
            }))

        service = account.service

        remote_repositories = [
            RemoteRepository(service,
                             repository_id='123',
                             name='repo1',
                             owner='bob',
                             scm_type='Git',
                             path='ssh://example.com/repo1',
                             mirror_path='https://example.com/repo1'),
            RemoteRepository(service,
                             repository_id='456',
                             name='repo2',
                             owner='bob',
                             scm_type='Git',
                             path='ssh://example.com/repo2',
                             mirror_path='https://example.com/repo2'),
        ]

        paginator = RemoteRepositoryTestPaginator(remote_repositories)

        self.spy_on(GitHub.get_remote_repositories,
                    call_fake=lambda *args, **kwargs: paginator)

        return (get_remote_repository_list_url(account, local_site_name),
                remote_repository_list_mimetype,
                remote_repositories)

    def test_get_remote_repositories_hosting_service(self):
        """Testing the GET
        hosting-service-accounts/<id>/remote-repositories/?id= API with
        HostingService.get_remote_repositories failure
        """
        class SandboxHostingService(HostingService):
            name = 'sandbox'

            def get_remote_repositories(self,
                                        owner=None,
                                        owner_type=None,
                                        filter_type=None,
                                        start=None,
                                        per_page=None):
                raise Exception

        self._login_user(admin=self.basic_get_use_admin)

        account = HostingServiceAccount.objects.create()
        service = SandboxHostingService(account=account)
        account._service = service
        remote_repository = [
            RemoteRepository(service,
                             repository_id='123',
                             name='repo1',
                             owner='bob',
                             scm_type='Git',
                             path='ssh://example.com/repo1')
        ]

        self.spy_on(service.get_remote_repositories)
        self.spy_on(resources.hosting_service_account.get_object,
                    call_fake=lambda *args, **kwargs: account)

        self.assertRaisesMessage(AttributeError,
                                 "'NoneType' object has no "
                                 "attribute 'page_data'",
                                 self.api_get,
                                 get_remote_repository_list_url(account, None),
                                 {'id': '123'},
                                 remote_repository_list_mimetype,
                                 remote_repository)

        self.assertTrue(service.get_remote_repositories.called)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(SpyAgency, BaseWebAPITestCase):
    """Testing the RemoteRepositoryResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'hosting-service-accounts/<id>/remote-repositories/<id>/'
    resource = resources.remote_repository
    basic_get_use_admin = True

    compare_item = _compare_item

    def setup_http_not_allowed_item_test(self, user):
        account = HostingServiceAccount.objects.create(service_name='github',
                                                       username='bob')

        remote_repository = RemoteRepository(
            account.service,
            repository_id='123',
            name='repo1',
            owner='bob',
            scm_type='Git',
            path='ssh://example.com/repo1')

        return get_remote_repository_item_url(remote_repository)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='bob',
            local_site=self.get_local_site_or_none(name=local_site_name),
            data=json.dumps({
                'authorization': {
                    'token': '123',
                },
            }))

        remote_repository = RemoteRepository(
            account.service,
            repository_id='123',
            name='repo1',
            owner='bob',
            scm_type='Git',
            path='ssh://example.com/repo1',
            mirror_path='https://example.com/repo1')

        self.spy_on(GitHub.get_remote_repository,
                    call_fake=lambda *args, **kwargs: remote_repository)

        return (get_remote_repository_item_url(remote_repository,
                                               local_site_name),
                remote_repository_item_mimetype,
                remote_repository)
