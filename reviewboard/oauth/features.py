"""Feature definitions for OAuth2 integration."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from djblets.features.feature import Feature, FeatureLevel


class OAuth2ServiceFeature(Feature):
    """A feature for OAuth2 integration."""

    feature_id = 'oauth.service'
    name = _('OAuth2 Service Integration')
    level = FeatureLevel.STABLE
    summary = _('Allow Review Board to act as an OAuth2 authentication '
                'service for third-party apps.')


oauth2_service_feature = OAuth2ServiceFeature()
