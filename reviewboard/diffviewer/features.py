"""Diffviewer features."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
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
