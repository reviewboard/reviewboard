from __future__ import unicode_literals

from django.utils.translation import get_language
from django.views.i18n import javascript_catalog

from djblets.cache.backend import cache_memoize
from djblets.cache.serials import generate_locale_serial


locale_serials = {}


def cached_javascript_catalog(request, domain='djangojs', packages=None):
    """A cached version of javascript_catalog."""
    global locale_serials

    package_str = '_'.join(packages)
    try:
        serial = locale_serials[package_str]
    except KeyError:
        serial = generate_locale_serial(packages)
        locale_serials[package_str] = serial

    return cache_memoize(
        'jsi18n-%s-%s-%s-%d' % (domain, package_str, get_language(), serial),
        lambda: javascript_catalog(request, domain, packages),
        large_data=True,
        compress_large_data=True)
