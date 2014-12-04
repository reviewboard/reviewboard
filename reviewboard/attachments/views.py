from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect

from reviewboard.attachments.models import FileAttachment
from reviewboard.site.decorators import check_local_site_access


@check_local_site_access
def user_file_attachment(request,
                         file_attachment_uuid,
                         username,
                         local_site=None):
    """Redirects to the file attachment's URL given its UUID."""
    user = get_object_or_404(User, username=username)

    file_attachment = get_object_or_404(FileAttachment,
                                        uuid=file_attachment_uuid,
                                        user=user,
                                        local_site=local_site,
                                        file__isnull=False)

    return redirect(file_attachment)
