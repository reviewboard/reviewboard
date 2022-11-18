"""Root view for reviews."""

from django.views.generic.base import RedirectView

from reviewboard.accounts.mixins import (CheckLoginRequiredViewMixin,
                                         UserProfileRequiredViewMixin)
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


class RootView(CheckLoginRequiredViewMixin,
               UserProfileRequiredViewMixin,
               CheckLocalSiteAccessViewMixin,
               RedirectView):
    """Handles the root URL of Review Board or a Local Site.

    If the user is authenticated, this will redirect to their Dashboard.
    Otherwise, they'll be redirected to the All Review Requests page.

    Either page may then redirect for login or show a Permission Denied,
    depending on the settings.
    """

    permanent = False

    def get_redirect_url(
        self,
        *args,
        **kwargs,
    ) -> str:
        """Return the URL to redirect to.

        Args:
            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            str:
            The URL to redirect to. If the user is authenticated, this will
            return the dashboard's URL. Otherwise, it will return the
            All Review Request page's URL.
        """
        if self.request.user.is_authenticated:
            url_name = 'dashboard'
        else:
            url_name = 'all-review-requests'

        return local_site_reverse(url_name, local_site=self.local_site)
