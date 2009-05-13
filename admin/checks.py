import imp
import os

from django.conf import settings
from django.utils.translation import gettext as _


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
        # Check if the site has moved and the old media directory no longer
        # exists.
        if not os.path.exists(settings.MEDIA_ROOT):
            new_media_root = os.path.join(settings.HTDOCS_ROOT, "media")

            if os.path.exists(new_media_root):
                from djblets.siteconfig.models import SiteConfiguration

                siteconfig = SiteConfiguration.objects.get_current()
                siteconfig.set("site_media_root", new_media_root)
                settings.MEDIA_ROOT = new_media_root


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

        try:
            from reviewboard.changedescs.models import ChangeDescription
            ChangeDescription.objects.count()
        except:
            # We were unable to load this, so it's likely that the user
            # hasn't run syncdb yet.
            _updates_required.append((
                "admin/manual-updates/run-syncdb.html", {}
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


def get_can_enable_search():
    """
    Checks whether the search functionality can be enabled.
    """
    try:
        imp.find_module("lucene")
        return (True, None)
    except ImportError:
        return (False, _(
            'PyLucene (with JCC) is required to enable search. See the '
            '<a href="%(url)s">documentation</a> for instructions.'
        ) % {'url': "http://www.review-board.org/wiki/SettingUpSearch"})


def get_can_enable_syntax_highlighting():
    """
    Checks whether syntax highlighting can be enabled.
    """
    try:
        import pygments

        version = pygments.__version__.split(".")

        if int(version[0]) > 0 or int(version[1]) >= 9:
            return (True, None)
        else:
            return (False, _(
                'Pygments %(cur_version)s is installed, but '
                '%(required_version)s or higher is required '
                'to use syntax highlighting.'
            ) % {'cur_version': pygments.__version__,
                 'required_version': "0.9"})
    except ImportError:
        return (False, _(
            'Syntax highlighting requires the <a href="%(url)s">Pygments</a> '
            'library, which is not installed.'
        ) % {'url': "http://www.pygments.org/"})


def get_can_enable_ldap():
    """
    Checks whether LDAP authentication can be enabled.
    """
    try:
        imp.find_module("ldap")
        return (True, None)
    except ImportError:
        return (False, _(
            'LDAP authentication requires the python-ldap library, which '
            'is not installed.'
        ))

def get_can_enable_dns():
    """
    Checks whether we can query DNS to find the domain controller to use.
    """
    try:
        # XXX for reasons I don't understand imp.find_module doesn't work
        #imp.find_module("DNS")
        import DNS
        return (True, None)
    except ImportError:
        return (False, _(
            'PyDNS, which is required to find the domain controller, '
            'is not installed.'
            ))
