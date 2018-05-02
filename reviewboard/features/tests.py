"""Tests for Review Board features."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.test.client import RequestFactory
from djblets.features import Feature, get_features_registry
from djblets.testing.decorators import add_fixtures

from reviewboard.features.checkers import RBFeatureChecker
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DummyFeature(Feature):
    """A dummy feature for testing."""

    feature_id = 'dummy.feature'
    name = 'Dummy feature'
    summary = 'A dummy feature for testing.'


class RBFeatureCheckerTests(TestCase):
    """Tests for the RBFeatureChecker."""

    fixtures = ['test_site']

    FEATURE_ENABLED_SETTINGS = {
        DummyFeature.feature_id: True,
    }

    FEATURE_DISABLED_SETTINGS = {
        DummyFeature.feature_id: False,
    }

    @classmethod
    def setUpClass(cls):
        super(RBFeatureCheckerTests, cls).setUpClass()

        cls.request_factory = RequestFactory()

    def setUp(self):
        super(RBFeatureCheckerTests, self).setUp()
        self.feature = DummyFeature()
        self.local_site = LocalSite.objects.get(name='local-site-1')

    def tearDown(self):
        super(RBFeatureCheckerTests, self).tearDown()
        registry = get_features_registry()
        registry.unregister(self.feature)

    def test_local_site_feature_enabled(self):
        """Testing RBFeatureChecker.is_feature_enabled for a feature enabled on
        a local site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_ENABLED_SETTINGS,
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_DISABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_disabled(self):
        """Testing RBFeatureChecker.is_feature_enabled for a feature disabled
        on a local site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_DISABLED_SETTINGS,
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_ENABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_fallback_enabled(self):
        """Testing RBFeatureChecker.is_feature_enabled for an unconfigured
        feature on a LocalSite that is enabled globally
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: {},
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_ENABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_fallback_disabled(self):
        """Testing RBFeatureChecker.is_feature_enabled for an unconfigured
        feature on a LocalSite that is disabled globally
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: {},
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_DISABLED_SETTINGS):
            self.assertFalse(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    @add_fixtures(['test_users'])
    def test_local_site_feature_enabled_on_global(self):
        """Testing RBFeatureChecker.is_feature_enabled for a feature enabled on
        a local site while not on a site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_ENABLED_SETTINGS,
        }
        self.local_site.save()

        request = self.request_factory.get('/')
        request.user = User.objects.get(username='doc')
        request.local_site = None

        with self.settings(ENABLED_FEATURES=self.FEATURE_DISABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id,
                request=request))

    @add_fixtures(['test_users'])
    def test_local_site_feature_disabled_on_global(self):
        """Testing RBFeatureChecker.is_feature_enabled for a feature disabled
        on a local site while not on a site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_DISABLED_SETTINGS,
        }
        self.local_site.save()

        request = self.request_factory.get('/')
        request.user = User.objects.get(username='doc')
        request.local_site = None

        with self.settings(ENABLED_FEATURES=self.FEATURE_ENABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id,
                request=request))

    @add_fixtures(['test_users'])
    def test_cache_localsite_queries(self):
        """Testing RBFeatureChecker.is_feature_enabled caches LocalSite
        membership to reduce query count
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_ENABLED_SETTINGS,
        }
        self.local_site.save()

        request = self.request_factory.get('/')
        request.user = User.objects.get(username='doc')

        with self.assertNumQueries(1):
            for _ in range(3):
                self.assertTrue(RBFeatureChecker().is_feature_enabled(
                    DummyFeature.feature_id,
                    request=request))

    def test_no_queries_anonymous(self):
        """Testing RBFeatureChecker.is_feature_enabled does not query when the
        user is anonymous
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: self.FEATURE_ENABLED_SETTINGS,
        }
        self.local_site.save()

        request = self.request_factory.get('/')
        request.user = AnonymousUser()

        with self.assertNumQueries(0):
            for _ in range(3):
                self.assertFalse(RBFeatureChecker().is_feature_enabled(
                    DummyFeature.feature_id,
                    request=request))
