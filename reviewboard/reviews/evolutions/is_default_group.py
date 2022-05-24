"""Add Group.is_default_group.

Version Added:
    2.5
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Group', 'is_default_group', models.BooleanField, initial=False)
]
