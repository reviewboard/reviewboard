import os

from django.conf import settings


_updates_required = []
_install_fine = False


def check_updates_required():
    """
    Checks if there are manual updates required before Review Board can be
    used on this server.
    """
    global _updates_required
    global _install_fine

    if not _updates_required and not _install_fine:
        # Check if there's a media/uploaded/images directory. If not, this is
        # either a new install or is using the old-style media setup and needs
        # to be manually upgraded.
        uploaded_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")

        if not os.path.isdir(uploaded_dir) or \
           not os.path.isdir(os.path.join(uploaded_dir, "images")):
            _updates_required.append((
                "admin/manual-updates/media-upload-dir.html", {
                    'MEDIA_ROOT': settings.MEDIA_ROOT
                }
            ))


        #
        # NOTE: Add new checks above this.
        #


        _install_fine = not _updates_required


    return _updates_required


def reset_check_cache():
    """
    Resets the cached data of all checks. This is mainly useful during
    unit tests.
    """
    global _updates_required
    global _install_fine

    _updates_required = []
    _install_fine = False
