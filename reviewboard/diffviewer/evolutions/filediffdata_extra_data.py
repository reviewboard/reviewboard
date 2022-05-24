"""Add FileDiffData.extra_data and remove delete_count and insert_count.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField, DeleteField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('FileDiffData', 'extra_data', JSONField, null=True),
    DeleteField('FileDiffData', 'insert_count'),
    DeleteField('FileDiffData', 'delete_count'),
]
