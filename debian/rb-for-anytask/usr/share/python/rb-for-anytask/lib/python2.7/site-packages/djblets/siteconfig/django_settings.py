#
# djblets/siteconfig/django_settings.py
#
# Copyright (c) 2008  Christian Hammond
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

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.utils import six, timezone

from djblets.cache.backend_compat import normalize_cache_backend
from djblets.cache.forwarding_backend import (DEFAULT_FORWARD_CACHE_ALIAS,
                                              ForwardingCacheBackend)


def _set_cache_backend(settings, key, value):
    settings.CACHES.update({
        DEFAULT_FORWARD_CACHE_ALIAS: (
            normalize_cache_backend(value, DEFAULT_FORWARD_CACHE_ALIAS) or
            normalize_cache_backend(value)),
        DEFAULT_CACHE_ALIAS: {
            'BACKEND': '%s.%s' % (ForwardingCacheBackend.__module__,
                                  ForwardingCacheBackend.__name__),
            'LOCATION': DEFAULT_FORWARD_CACHE_ALIAS,
        },
    })

    from django.core.cache import cache

    if isinstance(cache, ForwardingCacheBackend):
        cache.reset_backend()


def _set_static_url(settings, key, value):
    settings.STATIC_URL = value
    staticfiles_storage.base_url = value


def _set_timezone(settings, key, value):
    settings.TIME_ZONE = value

    # Internally, Django will also set os.environ['TZ'] to this value
    # and call time.tzset() when initially loading settings. We don't do
    # that, because it can have consequences.
    #
    # You can think of the timezone being set initially by Django as being
    # the core timezone that will be used for anything outside of a request.
    # What we set here is the timezone that Django will use in its own
    # timezone-related functions (for DateTimeFields and the like).
    #
    # That does mean that time.localtime and other functions will not
    # produce reliable dates. However, we need to ensure that any date/time
    # code is timezone-aware anyway, and works with our setting.
    #
    # To see how using os.environ['TZ'] would cause us problems, read
    # http://blog.chipx86.com/2013/01/26/weird-bugs-django-timezones-and-importing-from-eggs/
    timezone.activate(settings.TIME_ZONE)


locale_settings_map = {
    'locale_timezone':             {'key': 'TIME_ZONE',
                                    'deserialize_func': str,
                                    'setter': _set_timezone},
    'locale_language_code':        'LANGUAGE_CODE',
    'locale_date_format':          'DATE_FORMAT',
    'locale_datetime_format':      'DATETIME_FORMAT',
    'locale_default_charset':      {'key': 'DEFAULT_CHARSET',
                                    'deserialize_func': str},
    'locale_language_code':        'LANGUAGE_CODE',
    'locale_month_day_format':     'MONTH_DAY_FORMAT',
    'locale_time_format':          'TIME_FORMAT',
    'locale_year_month_format':    'YEAR_MONTH_FORMAT',
}

mail_settings_map = {
    'mail_server_address':         'SERVER_EMAIL',
    'mail_default_from':           'DEFAULT_FROM_EMAIL',
    'mail_host':                   'EMAIL_HOST',
    'mail_port':                   'EMAIL_PORT',
    'mail_host_user':              {'key': 'EMAIL_HOST_USER',
                                    'deserialize_func': bytes},
    'mail_host_password':          {'key': 'EMAIL_HOST_PASSWORD',
                                    'deserialize_func': bytes},
    'mail_use_tls':                'EMAIL_USE_TLS',
}

site_settings_map = {
    'site_media_root':             'MEDIA_ROOT',
    'site_media_url':              'MEDIA_URL',
    'site_static_root':            'STATIC_ROOT',
    'site_static_url':             {'key': 'STATIC_URL',
                                    'setter': _set_static_url},
    'site_prepend_www':            'PREPEND_WWW',
    'site_upload_temp_dir':        'FILE_UPLOAD_TEMP_DIR',
    'site_upload_max_memory_size': 'FILE_UPLOAD_MAX_MEMORY_SIZE',
}

cache_settings_map = {
    'cache_backend':               {'key': 'CACHES',
                                    'setter': _set_cache_backend},
    'cache_expiration_time':       'CACHE_EXPIRATION_TIME',
}


# Don't build unless we need it.
_django_settings_map = {}


def get_django_settings_map():
    """
    Returns the settings map for all Django settings that users may need
    to customize.
    """
    if not _django_settings_map:
        _django_settings_map.update(locale_settings_map)
        _django_settings_map.update(mail_settings_map)
        _django_settings_map.update(site_settings_map)
        _django_settings_map.update(cache_settings_map)

    return _django_settings_map


def generate_defaults(settings_map):
    """
    Utility function to generate a defaults mapping.
    """
    defaults = {}

    for siteconfig_key, setting_data in six.iteritems(settings_map):
        if isinstance(setting_data, dict):
            setting_key = setting_data['key']
        else:
            setting_key = setting_data

        if hasattr(settings, setting_key):
            defaults[siteconfig_key] = getattr(settings, setting_key)

    return defaults


def get_locale_defaults():
    """
    Returns the locale-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(locale_settings_map)


def get_mail_defaults():
    """
    Returns the mail-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(mail_settings_map)


def get_site_defaults():
    """
    Returns the site-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(site_settings_map)


def get_cache_defaults():
    """
    Returns the cache-related Django defaults that projects may want to
    let users customize.
    """
    return generate_defaults(cache_settings_map)


def get_django_defaults():
    """
    Returns all Django defaults that projects may want to let users customize.
    """
    return generate_defaults(get_django_settings_map())


def apply_django_settings(siteconfig, settings_map=None):
    """
    Applies all settings from the site configuration to the Django settings
    object.
    """
    if settings_map is None:
        settings_map = get_django_settings_map()

    for key, setting_data in six.iteritems(settings_map):
        if key in siteconfig.settings:
            value = siteconfig.get(key)
            setter = setattr

            if isinstance(setting_data, dict):
                setting_key = setting_data['key']

                if 'setter' in setting_data:
                    setter = setting_data['setter']

                if ('deserialize_func' in setting_data and
                    six.callable(setting_data['deserialize_func'])):
                    value = setting_data['deserialize_func'](value)
            else:
                setting_key = setting_data

            setter(settings, setting_key, value)
