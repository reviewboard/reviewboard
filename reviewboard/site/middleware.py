"""Middleware for Local Sites."""

from __future__ import unicode_literals

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
                The view being called. This is unused.

            view_args (tuple):
                The positional arguments passed to the view. This is unused.

            view_kwargs (dict):
                The keyword arguments passed to the view.
        """
        local_site_name = view_kwargs.get('local_site_name')
        request._local_site_name = local_site_name

        if request._local_site_name:
            request.local_site = SimpleLazyObject(
                lambda: get_object_or_none(LocalSite, name=local_site_name))
        else:
            request.local_site = None
