"""Generic unit tests for Web API resources"""

from __future__ import unicode_literals

import json

from django.test.client import RequestFactory
from djblets.features import Feature, get_features_registry
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.site.models import LocalSite
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.tests.base import BaseWebAPITestCase


class DummyFeature(Feature):
    """A dummy feature for testing."""

    feature_id = 'dummy.feature'
    name = 'Dummy Feature'
    summary = 'A dummy feature'


class BaseDummyResource(WebAPIResource):
    """A dummy resource for testing required_features."""

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    uri_object_key = 'dummy'

    def has_access_permissions(self, *args, **kwargs):
        return True

    def has_list_access_permissions(self, *args, **kwargs):
        return True

    def has_modify_permissions(self, *args, **kwargs):
        return True

    def has_delete_permissions(self, *args, **kwargs):
        return True

    def get(self, request, dummy=None, *args, **kwargs):
        return 418, {'dummy': dummy}

    def get_list(self, request, dummy=None, *args, **kwargs):
        return 418, {'dummy': dummy}

    def update(self, request, dummy=None, *args, **kwargs):
        return 418, {'dummy': dummy}

    def create(self, request, dummy=None, *args, **kwargs):
        return 418, {'dummy': dummy}

    def delete(self, request, dummy=None, *args, **kwargs):
        return 418, {'dummy': dummy}


class WebAPIResourceFeatureTests(BaseWebAPITestCase):
    """Tests for Web API Resources with required features"""

    def setUp(self):
        super(WebAPIResourceFeatureTests, self).setUp()

        self.feature = DummyFeature()

        class DummyResource(BaseDummyResource):
            required_features = [self.feature]

        self.resource_cls = DummyResource
        self.resource = self.resource_cls()

    def tearDown(self):
        super(WebAPIResourceFeatureTests, self).tearDown()

        registry = get_features_registry()
        registry.unregister(self.feature)

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
        self._test_method('get', False, dummy=123)

    def test_disabled_feature_delete(self):
        """Testing DELETE with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('delete', False, dummy=123)

    def test_disabled_feature_forbidden_update(self):
        """Testing PUT with a disabled required feature returns
        PERMISSION_DENIED
        """
        self._test_method('put', False, dummy=123)

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
        self._test_method('get', True, dummy=123)

    def test_enabled_feature_delete(self):
        """Testing DELETE with an enabled required feature returns the correct
        response
        """
        self._test_method('delete', True, dummy=123)

    def test_enabled_feature_update(self):
        """Testing PUT with an enabled required feature returns the correct
        response
        """
        self._test_method('put', True, dummy=123)

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
            'get', False, dummy=123,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_disabled_feature_delete_local_site(self):
        """Testing DELETE with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'delete', False, dummy=123,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_disabled_feature_forbidden_update_local_site(self):
        """Testing PUT with a disabled required feature returns
        PERMISSION_DENIED on a LocalSite
        """
        self._test_method(
            'put', False, dummy=123,
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
            'get', True, dummy=123,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_delete_local_site(self):
        """Testing DELETE with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'delete', True, dummy=123,
            local_site=LocalSite.objects.get(name='local-site-1'))

    @add_fixtures(['test_site'])
    def test_enabled_feature_update_local_site(self):
        """Testing PUT with an enabled required feature returns the correct
        response on a LocalSite
        """
        self._test_method(
            'put', True, dummy=123,
            local_site=LocalSite.objects.get(name='local-site-1'))

    def _test_method(self, method, feature_enabled, local_site=None,
                     dummy=None):
        # When a LocalSite is provided, we want to enable/disable the feature
        # only for that LocalSite and do the opposite for the global settings
        # to ensure that we are picking up the setting from the LocalSite and
        # not from the global settings.
        if local_site is not None:
            enabled_globally = not feature_enabled

            if not local_site.extra_data:
                local_site.extra_data = {}

            local_site.extra_data['enabled_features'] = {
                DummyFeature.feature_id: feature_enabled,
            }

            local_site.save(update_fields=('extra_data',))
        else:
            enabled_globally = feature_enabled

        settings = {
            'ENABLED_FEATURES': {
                DummyFeature.feature_id: enabled_globally,
            },
        }

        request = getattr(RequestFactory(), method)('/')
        request.local_site = local_site
        request.session = {}

        with self.settings(**settings):
            rsp = self.resource(request, dummy=dummy)

        content = json.loads(rsp.content)

        if feature_enabled:
            self.assertEqual(rsp.status_code, 418)
            self.assertEqual(content['stat'], 'ok')
            self.assertEqual(content['dummy'], dummy)
        else:
            self.assertEqual(rsp.status_code, 403)
            self.assertEqual(content['stat'], 'fail')
            self.assertEqual(content['err']['msg'], PERMISSION_DENIED.msg)
            self.assertEqual(content['err']['code'], PERMISSION_DENIED.code)
