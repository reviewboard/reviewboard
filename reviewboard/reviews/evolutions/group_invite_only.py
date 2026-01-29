"""Add Group.invite_only.

Version Added:
    1.6
"""

from __future__ import annotations

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Group', 'invite_only', models.BooleanField, initial=False),
]
