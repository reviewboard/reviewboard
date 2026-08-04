"""Add Profile.timezone.

Version Added:
    1.7
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Profile', 'timezone', models.CharField, initial='UTC',
             max_length=20)
]
