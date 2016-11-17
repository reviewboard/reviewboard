"""Tests for Review Board features."""

from __future__ import unicode_literals

from djblets.features import Feature, get_features_registry

from reviewboard.features.checkers import RBFeatureChecker
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DummyFeature(Feature):
    """A dummy feature for testing."""

    feature_id = 'dummy.feature'
    name = 'Dummy feature'
    summary = 'A dummy feature for testing.'


class RBFeatureCheckerTests(TestCase):
    """Tests for the LocalSiteFeatureChecker."""

    fixtures = ['test_site']

    FEATURE_ENABLED_FEATURES = {
        DummyFeature.feature_id: True,
    }

    FEATURE_DISABLED_SETTINGS = {
        DummyFeature.feature_id: False,
    }

    def setUp(self):
        super(RBFeatureCheckerTests, self).setUp()
        self.feature = DummyFeature()
        self.local_site = LocalSite.objects.get(name='local-site-1')

    def tearDown(self):
        super(RBFeatureCheckerTests, self).tearDown()
        registry = get_features_registry()
        registry.unregister(self.feature)

    def test_local_site_feature_enabled(self):
        """Testing LocalSiteFeatureChecker.is_feature_enabled for a feature
        enabled on a local site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY:
                self.FEATURE_ENABLED_FEATURES,
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_DISABLED_SETTINGS):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_disabled(self):
        """Testing LocalSiteFeatureChecker.is_feature_enabled for a feature
        disabled on a local site
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY:
                self.FEATURE_DISABLED_SETTINGS,
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_ENABLED_FEATURES):
            self.assertFalse(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_fallback_enabled(self):
        """Testing LocalSiteFeatureChecker.is_feature_enabled for an
        unconfigured feature on a LocalSite that is enabled globally
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: {},
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_ENABLED_FEATURES):
            self.assertTrue(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))

    def test_local_site_feature_fallback_disabled(self):
        """Testing LocalSiteFeatureChecker.is_feature_enabled for an
        unconfigured feature on a LocalSite that is disabled globally
        """
        self.local_site.extra_data = {
            RBFeatureChecker.EXTRA_DATA_KEY: {},
        }

        with self.settings(ENABLED_FEATURES=self.FEATURE_DISABLED_SETTINGS):
            self.assertFalse(RBFeatureChecker().is_feature_enabled(
                DummyFeature.feature_id, local_site=self.local_site))
