"""Add Profile.is_private.

Version Added:
    1.6
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Profile', 'is_private', models.BooleanField, initial=False)
]
