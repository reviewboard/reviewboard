import base64
import time
from datetime import datetime
from hashlib import sha1

from django.conf import settings
from django.contrib.auth.models import User
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import get_package_version


def get_install_key():
    """Returns the installation key for this server."""
    return sha1(settings.SECRET_KEY).hexdigest()


def get_support_url(request):
    """Returns the URL for the configured support page."""
    siteconfig = SiteConfiguration.objects.get_current()

    support_url = siteconfig.get('support_url')

    if not support_url:
        support_data = base64.b64encode('\t'.join([
            get_install_key(),
            str(int(request.user.is_staff)),
            siteconfig.site.domain,
            siteconfig.get('site_admin_name'),
            siteconfig.get('site_admin_email'),
            get_package_version(),
            str(User.objects.filter(is_active=True).count()),
            str(int(time.mktime(datetime.now().timetuple()))),
        ]))

        support_url = settings.DEFAULT_SUPPORT_URL % {
            'support_data': support_data,
        }

    return support_url
