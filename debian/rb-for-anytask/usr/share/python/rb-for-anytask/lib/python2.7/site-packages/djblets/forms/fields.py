from __future__ import unicode_literals

from django import forms
import pytz


TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))


class TimeZoneField(forms.ChoiceField):
    """A form field that only allows pytz common timezones as the choices."""
    def __init__(self, choices=TIMEZONE_CHOICES, *args, **kwargs):
        super(TimeZoneField, self).__init__(choices, *args, **kwargs)
