"""Licensing feature flags.

Version Added:
    7.1
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from djblets.features import Feature, FeatureLevel


class LicensingFeature(Feature):
    """A feature for enabling license management.

    When enabled, licensed product information will appear in the
    Administration UI and in banners when necessary.

    Version Added:
        7.1
    """

    feature_id = 'licensing'
    name = _('Licensing Support')
    level = FeatureLevel.EXPERIMENTAL
    summary = _('Support for managing licensed Review Board products.')


#: Feature flag for license management.
#:
#: Version Added:
#:     7.1
licensing_feature = LicensingFeature()
