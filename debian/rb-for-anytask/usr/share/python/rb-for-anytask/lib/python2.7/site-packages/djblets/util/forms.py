from __future__ import unicode_literals
import warnings

from djblets.forms.fields import TIMEZONE_CHOICES, TimeZoneField


warnings.warn('djblets.util.forms is deprecated. Use '
              'djblets.forms.fields instead.', DeprecationWarning)


__all__ = [
    'TIMEZONE_CHOICES',
    'TimeZoneField',
]
