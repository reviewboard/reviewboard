#
# reviewboard/admin/siteconfig.py -- Siteconfig definitions for the admin app in
#                                    Review Board. This expands on
#                                    djblets.siteconfig to let administrators
#                                    configure special authentication and
#                                    storage methods, as well as all our
#                                    reviewboard-specific settings.
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


import os.path

from django.conf import settings, global_settings
from django.core.exceptions import ImproperlyConfigured
from djblets.log import siteconfig as log_siteconfig
from djblets.siteconfig.django_settings import apply_django_settings, \
                                               get_django_defaults, \
                                               get_django_settings_map
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import get_registered_auth_backends
from reviewboard.admin.checks import get_can_enable_search, \
                                     get_can_enable_syntax_highlighting


# A mapping of our supported storage backend names to backend class paths.
storage_backend_map = {
    'builtin': 'django.core.files.storage.FileSystemStorage',
    's3':      'storages.backends.s3.S3Storage',
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
    'auth_ad_domain_name':        'AD_DOMAIN_NAME',
    'auth_ad_use_tls':            'AD_USE_TLS',
    'auth_ad_find_dc_from_dns':   'AD_FIND_DC_FROM_DNS',
    'auth_ad_domain_controller':  'AD_DOMAIN_CONTROLLER',
    'auth_ad_ou_name':            'AD_OU_NAME',
    'auth_ad_group_name':         'AD_GROUP_NAME',
    'auth_ad_search_root':        'AD_SEARCH_ROOT',
    'auth_ad_recursion_depth':    'AD_RECURSION_DEPTH',
    'auth_x509_username_field':   'X509_USERNAME_FIELD',
    'auth_x509_username_regex':   'X509_USERNAME_REGEX',
    'auth_x509_autocreate_users': 'X509_AUTOCREATE_USERS',
    'auth_nis_email_domain':      'NIS_EMAIL_DOMAIN',
    'site_domain_method':         'DOMAIN_METHOD',
}
settings_map.update(get_django_settings_map())
settings_map.update(log_siteconfig.settings_map)

# Settings for django-storages
settings_map.update({
    'aws_access_key_id':       'AWS_ACCESS_KEY_ID',
    'aws_secret_access_key':   'AWS_SECRET_ACCESS_KEY',
    'aws_headers':             'AWS_HEADERS',
    'aws_calling_format':      'AWS_CALLING_FORMAT',
    'aws_default_acl':         'AWS_DEFAULT_ACL',
    'aws_querystring_active':  'AWS_QUERYSTRING_ACTIVE',
    'aws_querystring_expire':  'AWS_QUERYSTRING_EXPIRE',
    'aws_s3_secure_urls':      'AWS_S3_SECURE_URLS',
    'aws_s3_bucket_name':      'AWS_STORAGE_BUCKET_NAME',
    'couchdb_default_server':  'COUCHDB_DEFAULT_SERVER',
    'couchdb_storage_options': 'COUCHDB_STORAGE_OPTIONS',
})


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
    'auth_enable_registration':            True,
    'auth_x509_username_field':            'SSL_CLIENT_S_DN_CN',
    'auth_x509_username_regex':            '',
    'auth_x509_autocreate_users':          False,
    'diffviewer_context_num_lines':        5,
    'diffviewer_include_space_patterns':   [],
    'diffviewer_paginate_by':              20,
    'diffviewer_paginate_orphans':         10,
    'diffviewer_syntax_highlighting':      True,
    'diffviewer_syntax_highlighting_threshold': 0,
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

defaults.update({
    'aws_access_key_id':       '',
    'aws_secret_access_key':   '',
    'aws_headers':             {},
    'aws_calling_format':      2,
    'aws_default_acl':         'public-read',
    'aws_querystring_active':  False,
    'aws_querystring_expire':  60,
    'aws_s3_secure_urls':      False,
    'aws_s3_bucket_name':      '',
    'couchdb_default_server':  '',
    'couchdb_storage_options': {},
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

    # The default value for DEFAULT_EMAIL_FROM (webmaster@localhost)
    # is less than good, so use a better one if it's set to that or if
    # we haven't yet set this value in siteconfig.
    mail_default_from = \
        siteconfig.settings.get('mail_default_from',
                                global_settings.DEFAULT_FROM_EMAIL)

    if (not mail_default_from or
        mail_default_from == global_settings.DEFAULT_FROM_EMAIL):
        domain = siteconfig.site.domain.split(':')[0]
        siteconfig.set('mail_default_from', 'noreply@' + domain)


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
    auth_backend_map = dict(get_registered_auth_backends())
    auth_backend_id = siteconfig.settings.get("auth_backend", "builtin")
    builtin_backend_obj = auth_backend_map['builtin']
    builtin_backend = "%s.%s" % (builtin_backend_obj.__module__,
                                 builtin_backend_obj.__name__)

    if auth_backend_id == "custom":
        custom_backends = siteconfig.settings.get("auth_custom_backends")

        if isinstance(custom_backends, basestring):
            custom_backends = (custom_backends,)
        elif isinstance(custom_backends, list):
            custom_backends = tuple(custom_backends)

        settings.AUTHENTICATION_BACKENDS = custom_backends

        if builtin_backend not in custom_backends:
            settings.AUTHENTICATION_BACKENDS += (builtin_backend,)
    elif auth_backend_id != "builtin" and auth_backend_id in auth_backend_map:
        backend = auth_backend_map[auth_backend_id]

        settings.AUTHENTICATION_BACKENDS = \
            ("%s.%s" % (backend.__module__, backend.__name__),
             builtin_backend)
    else:
        settings.AUTHENTICATION_BACKENDS = (builtin_backend,)

    # Set the storage backend
    storage_backend = siteconfig.settings.get('storage_backend', 'builtin')

    if storage_backend in storage_backend_map:
        settings.DEFAULT_FILE_STORAGE = storage_backend_map[storage_backend]
    else:
        settings.DEFAULT_FILE_STORAGE = storage_backend_map['builtin']

    # These blow up if they're not the perfectly right types
    settings.AWS_ACCESS_KEY_ID = str(siteconfig.get('aws_access_key_id'))
    settings.AWS_SECRET_ACCESS_KEY = str(siteconfig.get('aws_secret_access_key'))
    settings.AWS_STORAGE_BUCKET_NAME = str(siteconfig.get('aws_s3_bucket_name'))
    try:
        settings.AWS_CALLING_FORMAT = int(siteconfig.get('aws_calling_format'))
    except ValueError:
        settings.AWS_CALLING_FORMAT = 0
