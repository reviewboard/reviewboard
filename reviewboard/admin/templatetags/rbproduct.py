"""Template tags pertaining to the product as a whole."""

from __future__ import unicode_literals

from django import template
from django.conf import settings
from djblets.util.templatetags.djblets_js import json_dumps

from reviewboard import (VERSION, get_manual_url, get_version_string,
                         is_release)


register = template.Library()

_product_info_str = None


@register.simple_tag
def js_product_info():
    """Return JSON-serialized information on the product.

    This will include the product name, version (human-readable and raw
    version information), release status, and the URL to the manual, in a
    form that can be directly embedded into a template's JavaScript section.

    Since the data won't change between calls without performing an upgrade
    and restart, result is cached in the process. Repeated calls will return
    the cached information.

    Returns:
        django.utils.safestring.SafeText:
        The JSON-serialized product information.
    """
    global _product_info_str

    # We're caching the results, since this isn't going to ever change
    # between requests while the process is still running.
    if _product_info_str is None:
        _product_info_str = json_dumps({
            'isRelease': is_release(),
            'manualURL': get_manual_url(),
            'name': settings.PRODUCT_NAME,
            'version': get_version_string(),
            'versionInfo': VERSION[:-1],
        })

    return _product_info_str
