"""Add FileDiffData.delete_count and insert_count.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileDiffData', 'insert_count', models.IntegerField, null=True),
    AddField('FileDiffData', 'delete_count', models.IntegerField, null=True)
]
