from __future__ import unicode_literals


class LocalSiteMiddleware(object):
    """Middleware that handles storing information on the LocalSite in use."""
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._local_site_name = view_kwargs.get('local_site_name', None)

        return None
