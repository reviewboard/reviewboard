"""Add Profile.open_an_issue.

Version Added:
    1.7
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Profile', 'open_an_issue', models.BooleanField, initial=True)
]
