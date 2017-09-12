"""Views for serving up attachments."""

from __future__ import unicode_literals

from django.views.static import serve


def serve_safe(*args, **kwargs):
    """Safely serve an uploaded file to the client.

    This is a wrapper around :py:func:`django.views.static.serve`, intended
    only for use in DEBUG mode, that will serve files to the client using the
    security rules recommended for production use. All files will be returned
    with a ``Content-Disposition: attachment`` header, ensuring that the
    browser will download the file instead of attempting to open it inline.

    Args:
        *args (tuple):
            Additional positional arguments.

        **kwargs (dict):
            Additional keyword arguments.

    Returns:
        django.http.HttpResponse:
        The HTTP response for the file.
    """
    response = serve(*args, **kwargs)

    if response.status_code == 200:
        response['Content-Disposition'] = 'attachment'

    return response
