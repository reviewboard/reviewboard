"""Generic unit tests for Web API resources"""

from __future__ import unicode_literals

import json

from django.conf.urls import include, url
from django.core.urlresolvers import clear_url_caches
from djblets.features import Feature, get_features_registry
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.site.models import LocalSite
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.tests.base import BaseWebAPITestCase


# The URL conf for testing.
urlpatterns = []


class TestingFeature(Feature):
    """A dummy feature for testing."""

    feature_id = 'test.feature'
    name = 'Test Feature'
    summary = 'A testing feature'


class BaseTestingResource(WebAPIResource):
    """A testing resource for testing required_features."""

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    uri_object_key = 'obj_id'

    def has_access_permissions(self, *args, **kwargs):
        return True

    def has_list_access_permissions(self, *args, **kwargs):
        return True

    def has_modify_permissions(self, *args, **kwargs):
        return True

    def has_delete_permissions(self, *args, **kwargs):
        return True

    def get(self, request, obj_id=None, *args, **kwargs):
        return 418, {'obj_id': obj_id}

    def get_list(self, request, obj_id=None, *args, **kwargs):
        return 418, {'obj_id': obj_id}

    def update(self, request, obj_id=None, *args, **kwargs):
        return 418, {'obj_id': obj_id}

    def create(self, request, obj_id=None, *args, **kwargs):
        return 418, {'obj_id': obj_id}

    def delete(self, request, obj_id=None, *args, **kwargs):
        return 418, {'obj_id': obj_id}


class WebAPIResourceFeatureTests(BaseWebAPITestCase):
    """Tests for Web API Resources with required features"""

    @classmethod
    def setUpClass(cls):
        super(WebAPIResourceFeatureTests, cls).setUpClass()

        cls.feature = TestingFeature()

        class TestingResource(BaseTestingResource):
            required_features = [cls.feature]

        cls.resource_cls = TestingResource
        cls.resource = cls.resource_cls()

        # We are going to be using a different URLconf from Review Board for
        # these tests so that we can use cls.client to perform the requests.
        # That way, the requests will go through all of our middleware.
        urlpatterns.append(
            url(r'^/api/', include(cls.resource.get_url_patterns()))
        )
        urlpatterns.append(
            url(r'^s/(?P<local_site_name>[\w\.-]+)',
                include(list(urlpatterns)))
        )

    @classmethod
    def tearDownClass(cls):
        super(WebAPIResourceFeatureTests, cls).tearDownClass()

        registry = get_features_registry()
        registry.unregister(cls.feature)

        del urlpatterns[:]

    def test_disabled_feature_post(self):
        """Testing POST with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('post', False)

    def test_disabled_feature_get_list(self):
        """Testing GET with a disabled required feature returns
        PERMISSION_DENIED for a list_resource
        """
        self._test_method('get', False)

    def test_disabled_feature_get(self):
        """Testing GET with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('get', False, obj_id='123')

    def test_disabled_feature_delete(self):
        """Testing DELETE with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('delete', False, obj_id='123')

    def test_disabled_feature_forbidden_update(self):
        """Testing PUT with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('put', False, obj_id='123')

    def test_enabled_feature_post(self):
        """Testing POST with an enabled required feature returns the correct
        response
        """
        self._test_method('post', True)

    def test_enabled_feature_get_list(self):
        """Testing GET with an enabled required feature returns the correct
        response for a list resource
        """
        self._test_method('get', True)

    def test_enabled_feature_get(self):
        """Testing GET with an enabled required feature returns the correct
        response
        """
        self._test_method('get', True, obj_id='123')

    def test_enabled_feature_delete(self):
        """Testing DELETE with an enabled required feature returns the correct
        response
        """
        self._test_method('delete', True, obj_id='123')

    def test_enabled_feature_update(self):
        """Testing PUT with an enabled required feature returns the correct
        response
        """
        self._test_method('put', True, obj_id='123')

    @add_fixtures(['test_site'])
    def test_disabled_feature_post_local_site(self):
        """Testing POST with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'post', False,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_disabled_feature_get_list_local_site(self):
        """Testing GET with a disabled required feature returns
        PERMISSION_DENIED for a list_resource on a LocalSite
        """
        self._test_method('get', False)

    @add_fixtures(['test_site'])
    def test_disabled_feature_get_local_site(self):
        """Testing GET with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'get', False, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_disabled_feature_delete_local_site(self):
        """Testing DELETE with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'delete', False, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_disabled_feature_forbidden_update_local_site(self):
        """Testing PUT with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'put', False, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_post_local_site(self):
        """Testing POST with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'post', True,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_get_list_local_site(self):
        """Testing GET with an enabled required feature returns the correct
        response for a list resource on a LocalSite
        """
        self._test_method(
            'get', True,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_get_local_site(self):
        """Testing GET with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'get', True, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_delete_local_site(self):
        """Testing DELETE with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'delete', True, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_update_local_site(self):
        """Testing PUT with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'put', True, obj_id='123',
            local_site=LocalSite.objects.get(name='local-site-1'))

    def _test_method(self, method, feature_enabled, local_site=None,
                     obj_id=None):
        # When a LocalSite is provided, we want to enable/disable the feature
        # only for that LocalSite and do the opposite for the global settings
        # to ensure that we are picking up the setting from the LocalSite and
        # not from the global settings.
        if local_site is not None:
            enabled_globally = not feature_enabled

            if not local_site.extra_data:
                local_site.extra_data = {}

            local_site.extra_data['enabled_features'] = {
                TestingFeature.feature_id: feature_enabled,
            }

            local_site.save(update_fields=('extra_data',))
        else:
            enabled_globally = feature_enabled

        method = getattr(self.client, method)

        local_site_name = None

        if local_site:
            local_site_name = local_site.name

        settings = {
            'ENABLED_FEATURES': {
                TestingFeature.feature_id: enabled_globally,
            },
            'ROOT_URLCONF': 'reviewboard.webapi.tests.test_base',
        }

        try:
            # If we don't clear the URL caches then lookups for the URL will
            # break (due to using the URLs cached from the regular Review Board
            # URL conf).
            clear_url_caches()

            with self.settings(**settings):
                if obj_id is None:
                    resource_url = self.resource.get_list_url(
                        local_site_name=local_site_name)
                else:
                    resource_url = self.resource.get_item_url(
                        local_site_name=local_site_name,
                        obj_id=obj_id)

                rsp = method(resource_url)
        finally:
            clear_url_caches()

        content = json.loads(rsp.content)

        if feature_enabled:
            self.assertEqual(rsp.status_code, 418)
            self.assertEqual(content['stat'], 'ok')
            self.assertEqual(content['obj_id'], obj_id)
        else:
            self.assertEqual(rsp.status_code, 403)
            self.assertEqual(content['stat'], 'fail')
            self.assertEqual(content['err']['msg'], PERMISSION_DENIED.msg)
            self.assertEqual(content['err']['code'], PERMISSION_DENIED.code)
