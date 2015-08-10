from __future__ import unicode_literals
import json

from django.core.exceptions import ValidationError
from django.utils import six


def validate_json(value):
    """Validates content going into a JSONField.

    This will raise a ValidationError if the value is a string
    (representing a serialized JSON payload, possibly from the admin UI)
    and cannot be loaded properly.
    """
    if isinstance(value, six.string_types):
        try:
            json.loads(value)
        except ValueError as e:
            raise ValidationError(six.text_type(e), code='invalid')
