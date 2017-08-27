"""Review Board feature checkers."""

from __future__ import unicode_literals

from djblets.features.checkers import SiteConfigFeatureChecker


class RBFeatureChecker(SiteConfigFeatureChecker):
    """Feature checker that checks against a LocalSite's configuration.

    Features can be enabled/disabled on a per-LocalSite basis by setting
    the specified feature ID to either ``True`` or ``False`` in the
    ``enabled_features`` key in that LocalSite's
    :py:attr:`~reviewboard.sites.models.LocalSite.extra_data`` field.

    If the key is absent, this checker will check against the site
    configuration (and then the Django settings) to see if it is enabled or
    disabled globally.
    """

    EXTRA_DATA_KEY = SiteConfigFeatureChecker.siteconfig_key

    def is_feature_enabled(self, feature_id, **kwargs):
        """Return whether a feature is enabled for a given ID.

        Args:
            feature_id (unicode):
                The unique identifier of the feature whose status is to be
                determined.

            **kwargs (dict):
                Additional keyword arguments.

        Keyword Args:
            request (django.http.HttpRequest):
                An optional request. If this request is made against a
                LocalSite, that LocalSite will be used to look up the feature.

                Either this argument or ``local_site`` must be provided to
                enable checking against a LocalSite.

            local_site (reviewboard.site.models.LocalSite):
                An optional local site. If provided, this LocalSite will be
                used to look up the status of the requested feature.

                Either this argument or ``request`` must be provided to enable
                checking against a LocalSite.

        Returns:
            bool:
            Whether or not the feature is enabled.
        """
        local_site = kwargs.get('local_site')
        request = kwargs.get('request')

        if (local_site is None and
            request is not None and
            hasattr(request, 'local_site')):
            local_site = request.local_site

        if local_site and local_site.extra_data:
            try:
                return local_site.extra_data[self.EXTRA_DATA_KEY][feature_id]
            except KeyError:
                pass

        return super(RBFeatureChecker, self).is_feature_enabled(feature_id,
                                                                **kwargs)
