"""Middleware for Local Sites."""

from django.utils.functional import SimpleLazyObject
from djblets.db.query import get_object_or_none

from reviewboard.site.models import LocalSite


class LocalSiteMiddleware(object):
    """Middleware that handles storing information on the Local Site in use.

    This adds a new ``local_site`` attribute to the
    :py:class:`~django.http.HttpRequest` that, when first accessed, will fetch
    and cache the matching :py:class:`~reviewboard.site.models.LocalSite`. If
    there's no Local Site for this given request, this will store ``None``
    instead.
    """

    def __init__(self, get_response):
        """Initialize the middleware.

        Args:
            get_response (callable):
                The method to execute the view.
        """
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process the request before calling the view.

        This sets up a ``local_site`` attribute on the request to fetch the
        :py:class:`~reviewboard.site.models.LocalSite` used for this view,
        if any. This is based on the ``local_site_name`` key in
        ``view_kwargs``.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            view_func (callable):
                The view callable.

            view_args (tuple):
                Positional arguments passed in to the view.

            view_kwargs (dict):
                Keyword argument passed in to the view

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        local_site_name = view_kwargs.get('local_site_name')
        request._local_site_name = local_site_name

        if request._local_site_name:
            request.local_site = SimpleLazyObject(
                lambda: get_object_or_none(LocalSite, name=local_site_name))
        else:
            request.local_site = None

        return None

    def __call__(self, request):
        """Run the middleware.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The response object.
        """
        return self.get_response(request)
