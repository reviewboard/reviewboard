"""Diffviewer features."""

from django.utils.translation import gettext_lazy as _
from djblets.features import Feature, FeatureLevel


class DVCSFeature(Feature):
    """A feature for DVCS support.

    With this enabled, the DVCS API is enabled and review requests can be
    created with multiple commits.
    """

    feature_id = 'diffviewer.dvcs'
    name = _('DVCS Support')
    level = FeatureLevel.STABLE
    summary = _('Support for reviewing multiple commits.')


dvcs_feature = DVCSFeature()
