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

        Features are strictly additive. That is, if a feature is enabled
        globally (e.g., via
        :py:class:`~djblets.siteconfig.models.SiteConfiguration` or via
        :file:`settings_local.py`), disabling it for a
        :py:class:`~reviewboard.site.models.LocalSite` will still result in the
        feature being available (i.e., this function will return ``True``).

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

                If provided, it will be used to cache the results of the
                :py:class:`~reviewboard.site.models.LocalSite` lookup.

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

        local_sites = []

        if local_site:
            local_sites.append(local_site)
        elif request is not None:
            if getattr(request, 'local_site', None):
                local_sites.append(request.local_site)

            if request.user.is_authenticated():
                if not hasattr(request, '_user_local_sites_cache'):
                    if request.user.is_authenticated():
                        local_sites.extend(request.user.local_site.all())

                    request._user_local_sites_cache = local_sites
                else:
                    local_sites = request._user_local_sites_cache

        for local_site in local_sites:
            if (local_site.extra_data and
                local_site.extra_data.get(self.EXTRA_DATA_KEY,
                                          {}).get(feature_id)):
                return True

        return super(RBFeatureChecker, self).is_feature_enabled(feature_id,
                                                                **kwargs)
