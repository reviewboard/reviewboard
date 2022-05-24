"""Add DiffSet.base_commit_id.

Version Added:
    1.7.13
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DiffSet', 'base_commit_id', models.CharField, max_length=64,
             null=True, db_index=True)
]
