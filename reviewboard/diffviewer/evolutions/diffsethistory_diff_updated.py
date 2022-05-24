"""Add DiffSetHistory.last_diff_updated.

Version Added:
    1.7
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DiffSetHistory', 'last_diff_updated', models.DateTimeField,
             null=True)
]
