#
# reviewboard/admin/checks.py -- Dependency checks for items which are used in
#                                the admin UI. For the most part, when one of
#                                these fails, some piece of UI is disabled with
#                                the returned error message.
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

import getpass
import os
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError
from django.utils.translation import ugettext as _
from djblets.util.filesystem import is_exe_in_path
from djblets.siteconfig.models import SiteConfiguration

import reviewboard
from reviewboard import get_version_string
from reviewboard.admin.import_utils import has_module


_install_fine = False


def check_updates_required():
    """Checks if there are manual updates required.

    Sometimes, especially in developer installs, some things need to be tweaked
    by hand before Review Board can be used on this server.
    """
    global _install_fine

    updates_required = []

    if not _install_fine:
        site_dir = os.path.dirname(settings.HTDOCS_ROOT)
        devel_install = (os.path.exists(os.path.join(settings.LOCAL_ROOT,
                                                     'manage.py')))
        siteconfig = None

        # Check if we can access a SiteConfiguration. There should always
        # be one, unless the user has erased stuff by hand.
        #
        # This also checks for any sort of errors in talking to the database.
        # This could be due to the database being down, or corrupt, or
        # tables locked, or an empty database, or other cases. We want to
        # catch this before getting the point where plain 500 Internal Server
        # Errors appear.
        try:
            siteconfig = SiteConfiguration.objects.get_current()
        except (DatabaseError, SiteConfiguration.DoesNotExist) as e:
            updates_required.append((
                'admin/manual-updates/database-error.html', {
                    'error': e,
                }
            ))

        # Check if the version running matches the last stored version.
        # Only do this for non-debug installs, as it's really annoying on
        # a developer install.:
        cur_version = get_version_string()

        if siteconfig and siteconfig.version != cur_version:
            updates_required.append((
                'admin/manual-updates/version-mismatch.html', {
                    'current_version': cur_version,
                    'stored_version': siteconfig.version,
                    'site_dir': site_dir,
                    'devel_install': devel_install,
                    'python_ver': '%s.%s.%s' % sys.version_info[:3],
                    'package_path': os.path.dirname(reviewboard.__file__),
                }
            ))

        # Check if the site has moved and the old media directory no longer
        # exists.
        if siteconfig and not os.path.exists(settings.STATIC_ROOT):
            new_static_root = os.path.join(settings.HTDOCS_ROOT, 'static')

            if os.path.exists(new_static_root):
                siteconfig.set('site_static_root', new_static_root)
                settings.STATIC_ROOT = new_static_root

        # Check if the site has moved and the old media directory no longer
        # exists.
        if siteconfig and not os.path.exists(settings.MEDIA_ROOT):
            new_media_root = os.path.join(settings.HTDOCS_ROOT, 'media')

            if os.path.exists(new_media_root):
                siteconfig.set('site_media_root', new_media_root)
                settings.MEDIA_ROOT = new_media_root

        # Check if the user has any pending static media configuration
        # changes they need to make.
        if siteconfig and 'manual-updates' in siteconfig.settings:
            stored_updates = siteconfig.settings['manual-updates']

            if not stored_updates.get('static-media', False):
                updates_required.append((
                    'admin/manual-updates/server-static-config.html', {
                        'STATIC_ROOT': settings.STATIC_ROOT,
                        'SITE_ROOT': settings.SITE_ROOT,
                        'SITE_DIR': settings.LOCAL_ROOT,
                    }
                ))

        # Check if there's a media/uploaded/images directory. If not, this is
        # either a new install or is using the old-style media setup and needs
        # to be manually upgraded.
        uploaded_dir = os.path.join(settings.MEDIA_ROOT, "uploaded")

        if not os.path.isdir(uploaded_dir) or \
           not os.path.isdir(os.path.join(uploaded_dir, "images")):
            updates_required.append((
                "admin/manual-updates/media-upload-dir.html", {
                    'MEDIA_ROOT': settings.MEDIA_ROOT
                }
            ))

        try:
            username = getpass.getuser()
        except ImportError:
            # This will happen if running on Windows (which doesn't have
            # the pwd module) and if %LOGNAME%, %USER%, %LNAME% and
            # %USERNAME% are all undefined.
            username = "<server username>"

        # Check if the data directory (should be $HOME) is writable by us.
        data_dir = os.environ.get('HOME', '')

        if (not data_dir or
                not os.path.isdir(data_dir) or
                not os.access(data_dir, os.W_OK)):
            try:
                username = getpass.getuser()
            except ImportError:
                # This will happen if running on Windows (which doesn't have
                # the pwd module) and if %LOGNAME%, %USER%, %LNAME% and
                # %USERNAME% are all undefined.
                username = "<server username>"

            updates_required.append((
                'admin/manual-updates/data-dir.html', {
                    'data_dir': data_dir,
                    'writable': os.access(data_dir, os.W_OK),
                    'server_user': username,
                    'expected_data_dir': os.path.join(site_dir, 'data'),
                }
            ))

        # Check if the the legacy htdocs and modern static extension
        # directories exist and are writable by us.
        ext_roots = [settings.MEDIA_ROOT]

        if not settings.DEBUG:
            ext_roots.append(settings.STATIC_ROOT)

        for root in ext_roots:
            ext_dir = os.path.join(root, 'ext')

            if not os.path.isdir(ext_dir) or not os.access(ext_dir, os.W_OK):
                updates_required.append((
                    'admin/manual-updates/ext-dir.html', {
                        'ext_dir': ext_dir,
                        'writable': os.access(ext_dir, os.W_OK),
                        'server_user': username,
                    }
                ))

        if not is_exe_in_path('patch'):
            if sys.platform == 'win32':
                binaryname = 'patch.exe'
            else:
                binaryname = 'patch'

            updates_required.append((
                "admin/manual-updates/install-patch.html", {
                    'platform': sys.platform,
                    'binaryname': binaryname,
                    'search_path': os.getenv('PATH'),
                }
            ))

        #
        # NOTE: Add new checks above this.
        #

        _install_fine = not updates_required

    return updates_required


def reset_check_cache():
    """Resets the cached data of all checks.

    This is mainly useful during unit tests.
    """
    global _install_fine

    _install_fine = False


def get_can_enable_ldap():
    """Checks whether LDAP authentication can be enabled."""
    if has_module('ldap'):
        return (True, None)
    else:
        return (False, _(
            'LDAP authentication requires the python-ldap library, which '
            'is not installed.'
        ))


def get_can_enable_dns():
    """Checks whether we can query DNS to find the domain controller to use."""
    if has_module('DNS'):
        return (True, None)
    else:
        return (False, _(
            'PyDNS, which is required to find the domain controller, '
            'is not installed.'
        ))


def get_can_use_amazon_s3():
    """Checks whether django-storages (Amazon S3 backend) is installed."""
    try:
        if has_module('storages.backends.s3boto', members=['S3BotoStorage']):
            return (True, None)
        else:
            return (False, _(
                'Amazon S3 depends on django-storages, which is not installed'
            ))
    except ImproperlyConfigured as e:
        return (False, _('Amazon S3 backend failed to load: %s') % e)


def get_can_use_couchdb():
    """Checks whether django-storages (CouchDB backend) is installed."""
    if has_module('storages.backends.couchdb', members=['CouchDBStorage']):
        return (True, None)
    else:
        return (False, _(
            'CouchDB depends on django-storages, which is not installed'
        ))
