"""Switch Profile.default_use_rich_text to a BooleanField.

This is required for Django 3.2, which no longer provides the old
:py:class:`django.db.models.BooleanField`.

Version Added:
    5.0
"""

from django.db import models
from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Profile', 'default_use_rich_text',
                field_type=models.BooleanField,
                null=True),
]
