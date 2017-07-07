"""Mixins for LocalSite-related views."""

from __future__ import unicode_literals

from django.utils.decorators import method_decorator

from reviewboard.site.decorators import check_local_site_access


class CheckLocalSiteAccessViewMixin(object):
    """Generic view mixin to check if a user has access to the Local Site.

    It's important to note that this does not check for login access.
    This is just a convenience around using the
    :py:func:`@check_local_site_access
    <reviewboard.site.decorators.check_local_site_access>` decorator for
    generic views.

    The :py:attr:`local_site` attribute will be set on the class for use in
    the view.

    Attributes:
        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed, or ``None``.
    """

    @method_decorator(check_local_site_access)
    def dispatch(self, request, local_site=None, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site being accessed, if any.

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        self.local_site = local_site

        return super(CheckLocalSiteAccessViewMixin, self).dispatch(
            request, *args, **kwargs)
