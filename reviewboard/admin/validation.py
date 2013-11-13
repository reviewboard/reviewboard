from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def validate_bug_tracker(input_url):
    """
    Validates that an issue tracker URI string contains one `%s` Python format
    specification type (no other types are supported).
    """
    try:
        # Ignore escaped `%`'s
        test_url = input_url.replace('%%', '')

        if test_url.find('%s') == -1:
            raise TypeError

        # Ensure an arbitrary value can be inserted into the URL string
        test_url = test_url % 1
    except (TypeError, ValueError):
        raise ValidationError([
            _("%s has invalid format specification type(s). Use only one "
              "'%%s' to mark the location of the bug id. If the URI contains "
              "encoded values (e.g. '%%20'), prepend the encoded values with "
              "an additional '%%'.") % input_url])
