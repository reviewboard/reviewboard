"""Views for serving up attachments."""

from __future__ import unicode_literals

from django.shortcuts import get_object_or_404, redirect
from django.views.static import serve

from reviewboard.attachments.models import FileAttachment
from reviewboard.site.decorators import check_local_site_access


@check_local_site_access
def user_file_attachment(request, file_attachment_uuid, username,
                         local_site=None):
    """Redirect to the file attachment's URL given its UUID.

    Args:
        request (django.http.HttpRequest):
            The request.

        file_attachment_uuid (unicode):
            The UUID of the file attachment.

        username (unicode):
            The username of the user who uploaded the file.

        local_site (reviewboard.site.models.LocalSite, optional):
            The local site, if any.

    Returns:
        django.http.HttpResponseRedirect:
        The response to send back to the browser.
    """
    file_attachment = get_object_or_404(FileAttachment,
                                        uuid=file_attachment_uuid,
                                        user__username=username,
                                        local_site=local_site,
                                        file__isnull=False)

    return redirect(file_attachment)


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
