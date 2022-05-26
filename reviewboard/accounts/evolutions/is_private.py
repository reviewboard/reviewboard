"""Add Profile.is_private.

Version Added:
    1.6
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'is_private', models.BooleanField, initial=False)
]
