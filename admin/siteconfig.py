import os.path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from djblets.log import siteconfig as log_siteconfig
from djblets.siteconfig.django_settings import apply_django_settings, \
                                               get_django_defaults, \
                                               get_django_settings_map
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.checks import get_can_enable_search, \
                                     get_can_enable_syntax_highlighting


# A mapping of our supported authentication backend names to backend class
# paths.
auth_backend_map = {
    'builtin': 'django.contrib.auth.backends.ModelBackend',
    'nis':     'reviewboard.accounts.backends.NISBackend',
    'ldap':    'reviewboard.accounts.backends.LDAPBackend',
}


# A mapping of siteconfig setting names to Django settings.py names.
# This also contains all the djblets-provided mappings as well.
settings_map = {
    'auth_ldap_anon_bind_uid':    'LDAP_ANON_BIND_UID',
    'auth_ldap_anon_bind_passwd': 'LDAP_ANON_BIND_PASSWD',
    'auth_ldap_email_domain':     'LDAP_EMAIL_DOMAIN',
    'auth_ldap_email_attribute':  'LDAP_EMAIL_ATTRIBUTE',
    'auth_ldap_tls':              'LDAP_TLS',
    'auth_ldap_base_dn':          'LDAP_BASE_DN',
    'auth_ldap_uid_mask':         'LDAP_UID_MASK',
    'auth_ldap_uri':              'LDAP_URI',
    'auth_nis_email_domain':      'NIS_EMAIL_DOMAIN',
    'site_domain_method':         'DOMAIN_METHOD',
}
settings_map.update(get_django_settings_map())
settings_map.update(log_siteconfig.settings_map)


# All the default values for settings.
defaults = get_django_defaults()
defaults.update(log_siteconfig.defaults)
defaults.update({
    'auth_ldap_anon_bind_uid':             '',
    'auth_ldap_anon_bind_passwd':          '',
    'auth_ldap_email_domain':              '',
    'auth_ldap_tls':                       False,
    'auth_ldap_uid_mask':                  '',
    'auth_ldap_uri':                       '',
    'auth_nis_email_domain':               '',
    'auth_require_sitewide_login':         False,
    'auth_custom_backends':                [],
    'diffviewer_context_num_lines':        5,
    'diffviewer_include_space_patterns':   [],
    'diffviewer_paginate_by':              20,
    'diffviewer_paginate_orphans':         10,
    'diffviewer_syntax_highlighting':      True,
    'diffviewer_show_trailing_whitespace': True,
    'mail_send_review_mail':               False,
    'search_enable':                       False,
    'site_domain_method':                  'http',

    # TODO: Allow relative paths for the index file later on.
    'search_index_file': os.path.join(settings.REVIEWBOARD_ROOT,
                                      'search-index'),

    # Overwrite this.
    'site_media_url': settings.SITE_ROOT + "media/"
})


def load_site_config():
    """
    Loads any stored site configuration settings and populates the Django
    settings object with any that need to be there.
    """
    def apply_setting(settings_key, db_key, default=None):
        db_value = siteconfig.settings.get(db_key)

        if db_value:
            setattr(settings, settings_key, db_value)
        elif default:
            setattr(settings, settings_key, default)


    try:
        siteconfig = SiteConfiguration.objects.get_current()
    except SiteConfiguration.DoesNotExist:
        raise ImproperlyConfigured, \
            "The site configuration entry does not exist in the database. " \
            "Re-run `./manage.py` syncdb to fix this."
    except:
        # We got something else. Likely, this doesn't exist yet and we're
        # doing a syncdb or something, so silently ignore.
        return


    # Populate defaults if they weren't already set.
    if not siteconfig.get_defaults():
        siteconfig.add_defaults(defaults)


    # Populate the settings object with anything relevant from the siteconfig.
    apply_django_settings(siteconfig, settings_map)


    # Now for some more complicated stuff...

    # Do some dependency checks and disable things if we don't support them.
    if not get_can_enable_search()[0]:
        siteconfig.set('search_enable', False)

    if not get_can_enable_syntax_highlighting()[0]:
        siteconfig.set('diffviewer_syntax_highlighting', False)


    # Site administrator settings
    apply_setting("ADMINS", None, (
        (siteconfig.get("site_admin_name", ""),
         siteconfig.get("site_admin_email", "")),
    ))

    apply_setting("MANAGERS", None, settings.ADMINS)

    # Explicitly base this off the MEDIA_URL
    apply_setting("ADMIN_MEDIA_PREFIX", None, settings.MEDIA_URL + "admin/")


    # Set the auth backends
    auth_backend = siteconfig.settings.get("auth_backend", "builtin")
    builtin_backend = auth_backend_map['builtin']

    if auth_backend == "custom":
        custom_backends = siteconfig.settings.get("auth_custom_backends")

        if isinstance(custom_backends, basestring):
            custom_backends = (custom_backends,)
        elif isinstance(custom_backends, list):
            custom_backends = tuple(custom_backends)

        settings.AUTHENTICATION_BACKENDS = custom_backends

        if builtin_backend not in custom_backends:
            settings.AUTHENTICATION_BACKENDS += (builtin_backend,)
    elif auth_backend != "builtin" and auth_backend in auth_backend_map:
        settings.AUTHENTICATION_BACKENDS = \
            (auth_backend_map[auth_backend], builtin_backend)
    else:
        settings.AUTHENTICATION_BACKENDS = (builtin_backend,)
