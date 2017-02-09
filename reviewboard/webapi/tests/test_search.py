"""Tests for the SearchResource APIs."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six

from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import search_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_search_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the SearchResource APIs."""

    fixtures = ['test_users']
    sample_api_url = 'search/'
    resource = resources.search

    def setup_http_not_allowed_list_test(self, user):
        return get_search_url()

    def setup_http_not_allowed_item_test(self, user):
        return get_search_url()

    def compare_item(self, item_rsp, local_site_name):
        if local_site_name:
            local_site = LocalSite.objects.get(name=local_site_name)
            self.assertEqual(len(item_rsp['users']), local_site.users.count())
        else:
            self.assertEqual(len(item_rsp['users']), User.objects.count())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_search_url(local_site_name),
                search_mimetype,
                local_site_name)

    def test_get_with_max_results(self):
        """Testing the GET search/ API with max_results"""
        for i in range(20):
            self.create_review_request(public=True)

        max_results = 10

        rsp = self.api_get(get_search_url(),
                           query={'max_results': max_results},
                           expected_mimetype=search_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), max_results)
