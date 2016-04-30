from __future__ import print_function, unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import get_version_string
from reviewboard.admin.siteconfig import settings_map, defaults


def init_siteconfig(app, created_models, verbosity, db=None, **kwargs):
    """Initialize the site configuration.

    This will create a SiteConfiguration object if one does not exist, or
    update the existing one with the current version number.
    """
    try:
        site = Site.objects.get_current()
    except Site.DoesNotExist:
        # This is an initial syncdb and we got called before Site's post_syncdb
        # handler did, so invoke it directly.
        from django.contrib.sites.management import create_default_site
        create_default_site(app, created_models, verbosity, db=db)
        site = Site.objects.get_current()

    siteconfig, is_new = SiteConfiguration.objects.get_or_create(site=site)

    new_version = get_version_string()

    if is_new:
        # Check the Site to see if this is a brand new installation. If so,
        # don't talk to the user about upgrades or other such nonsense.
        if Site not in created_models:
            print("*** Migrating settings from settings_local.py to the "
                  "database.")

        migrate_settings(siteconfig)

        if Site not in created_models:
            print("*** If you have previously configured Review Board "
                  "through a ")
            print("*** settings_local.py file, please ensure that the "
                  "migration ")
            print("*** was successful by verifying your settings at")
            print("*** %s://%s%sadmin/settings/" %
                  (siteconfig.get("site_domain_method"),
                   site.domain,
                   settings.SITE_ROOT))

        siteconfig.version = new_version
        siteconfig.save()
    elif siteconfig.version != new_version:
        print("Upgrading Review Board from %s to %s" % (siteconfig.version,
                                                        new_version))
        siteconfig.version = new_version
        siteconfig.save()


migration_table = {
    # new settings key                   # old settings key
    'auth_require_sitewide_login':       'REQUIRE_SITEWIDE_LOGIN',
    'diffviewer_context_num_lines':      'DIFF_CONTEXT_NUM_LINES',
    'diffviewer_include_space_patterns': 'DIFF_INCLUDE_SPACE_PATTERNS',
    'diffviewer_paginate_by':            'DIFFVIEWER_PAGINATE_BY',
    'diffviewer_paginate_orphans':       'DIFFVIEWER_PAGINATE_ORPHANS',
    'diffviewer_syntax_highlighting':    'DIFF_SYNTAX_HIGHLIGHTING',
    'mail_send_review_mail':             'SEND_REVIEW_MAIL',
    'search_enable':                     'ENABLE_SEARCH',
    'search_index_file':                 'SEARCH_INDEX',
}
migration_table.update(settings_map)

auth_backend_map = {
    'django.contrib.auth.backends.ModelBackend':       'builtin',
    'reviewboard.accounts.backends.NISBackend':        'nis',
    'reviewboard.accounts.backends.LDAPBackend':       'ldap',
    'reviewboard.accounts.backends.HTTPDigestBackend': 'digest',
}


def migrate_settings(siteconfig):
    """Migrate any settings we want in the database from the settings file."""
    # Convert everything in the table.
    for siteconfig_key, setting_data in six.iteritems(migration_table):
        if isinstance(setting_data, dict):
            setting_key = setting_data['key']
            serialize_func = setting_data.get('serialize_func', None)
        else:
            setting_key = setting_data
            serialize_func = None

        default = defaults.get(siteconfig_key, None)
        value = getattr(settings, setting_key, default)

        if serialize_func and six.callable(serialize_func):
            value = serialize_func(value)

        siteconfig.set(siteconfig_key, value)

    # This may be a tuple in a tuple, or it may just be a tuple.
    if type(settings.ADMINS[0]) == tuple:
        admin = settings.ADMINS[0]
    else:
        admin = settings.ADMINS

    siteconfig.set('site_admin_name', admin[0])
    siteconfig.set('site_admin_email', admin[1])

    # Try to transform the authentication backend
    remaining_backends = []
    known_backends = []

    for auth_backend in settings.AUTHENTICATION_BACKENDS:
        if auth_backend in auth_backend_map:
            known_backends.append(auth_backend)
        else:
            remaining_backends.append(auth_backend)

    if remaining_backends or len(known_backends) > 1:
        # The user has some custom backend set. Just set the entire list
        siteconfig.set('auth_backend', 'custom')
        siteconfig.set('auth_custom_backends',
                       settings.AUTHENTICATION_BACKENDS)
    elif len(known_backends) == 1:
        siteconfig.set('auth_backend', auth_backend_map[known_backends[0]])
    else:
        siteconfig.set('auth_backend', 'builtin')
