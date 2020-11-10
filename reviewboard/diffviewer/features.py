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


class FilterInterdiffsV2Feature(Feature):
    """A feature for the 2.0 version of interdiff filtering.

    This enables the interdiff filtering logic being made default in
    Review Board 4.0. Starting in Review Board 3.0.18, this can be enabled
    to beta test the new algorithm.
    """

    feature_id = 'diffviewer.filter_interdiffs_v2'
    name = _('Interdiff Filtering v2')
    level = FeatureLevel.STABLE
    summary = _("Support for Review Board 4.0's interdiff filtering logic.")


dvcs_feature = DVCSFeature()
filter_interdiffs_v2_feature = FilterInterdiffsV2Feature()
