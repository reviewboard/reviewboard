"""Add Profile.should_send_own_updates.

Version Added:
    2.0.9
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Profile', 'should_send_own_updates', models.BooleanField,
             initial=True)
]
