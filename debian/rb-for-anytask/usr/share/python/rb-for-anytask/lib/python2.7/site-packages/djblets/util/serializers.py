import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import force_text
from django.utils.functional import Promise


class DjbletsJSONEncoder(DjangoJSONEncoder):
    """Encodes data into JSON-compatible structures.

    This is a specialization of DjangoJSONEncoder that converts
    lazily ugettext strings to real strings, and chops off the milliseconds
    and microseconds of datetimes.
    """
    def default(self, obj):
        if isinstance(obj, Promise):
            # Handles initializing lazily created ugettext messages.
            return force_text(obj)
        elif isinstance(obj, datetime.datetime):
            # This is like DjangoJSONEncoder's datetime encoding
            # implementation, except that it filters out the milliseconds
            # in addition to microseconds. This ensures consistency between
            # database-stored timestamps and serialized objects.
            r = obj.isoformat()

            if obj.microsecond:
                r = r[:19] + r[26:]

            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'

            return r

        return super(DjbletsJSONEncoder, self).default(obj)
