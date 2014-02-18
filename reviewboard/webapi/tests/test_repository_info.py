from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import repository_info_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_repository_info_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryInfoResource APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'repositories/<id>/info/'
    resource = resources.repository_info

    def setup_http_not_allowed_list_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_info_url(repository)

    def setup_http_not_allowed_item_test(self, user):
        repository = self.create_repository(tool_name='Test')

        return get_repository_info_url(repository)

    def compare_item(self, item_rsp, info):
        self.assertEqual(item_rsp, info)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Test',
                                            with_local_site=with_local_site)

        return (get_repository_info_url(repository, local_site_name),
                repository_info_item_mimetype,
                repository.get_scmtool().get_repository_info())
