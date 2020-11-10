"""Diffviewer features."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from djblets.features import Feature, FeatureLevel


class FilterInterdiffsV2Feature(Feature):
    """A feature for the 2.0 version of interdiff filtering.

    This enables the interdiff filtering logic being made default in
    Review Board 4.0. Starting in Review Board 3.0.18, this can be enabled
    to beta test the new algorithm.
    """

    feature_id = 'diffviewer.filter_interdiffs_v2'
    name = _('Interdiff Filtering v2')
    level = FeatureLevel.EXPERIMENTAL
    summary = _("Support for Review Board 4.0's interdiff filtering logic.")


filter_interdiffs_v2_feature = FilterInterdiffsV2Feature()
