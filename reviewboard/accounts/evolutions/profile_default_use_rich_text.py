"""Add Profile.default_use_rich_text.

Version Added:
    2.0.12
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Profile', 'default_use_rich_text', models.NullBooleanField,
             initial=None, null=True),
]
