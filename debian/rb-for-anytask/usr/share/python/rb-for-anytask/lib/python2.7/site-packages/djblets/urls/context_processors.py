from __future__ import unicode_literals

from django.conf import settings


def site_root(request):
    """
    Exposes a SITE_ROOT variable in templates. This assumes that the
    project has been configured with a SITE_ROOT settings variable and
    proper support for basing the installation in a subdirectory.
    """
    return {'SITE_ROOT': settings.SITE_ROOT}
