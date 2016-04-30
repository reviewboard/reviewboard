from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def validate_bug_tracker(input_url):
    """Validate a bug tracker URL.

    This checks that the given URL string contains one (and only one) `%s`
    Python format specification type (no other types are supported).
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
              "'%%s' to mark the location of the bug id. If the URL contains "
              "encoded values (e.g. '%%20'), prepend the encoded values with "
              "an additional '%%'.") % input_url])


def validate_bug_tracker_base_hosting_url(input_url):
    """Check that hosting service bug URLs don't contain %s."""
    # Try formatting the URL using an empty tuple to verify that it
    # doesn't contain any format characters.
    try:
        input_url % ()
    except TypeError:
        raise ValidationError([
            _("The URL '%s' is not valid because it contains a format "
              "character. For bug trackers other than 'Custom Bug Tracker', "
              "use the base URL of the server. If you need a '%%' character, "
              "prepend it with an additional '%%'.") % input_url])
