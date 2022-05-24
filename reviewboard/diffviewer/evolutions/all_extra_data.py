"""Add extra_data field to DiffSet, DiffSetHistory, and FileDiff.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('DiffSet', 'extra_data', JSONField, null=True),
    AddField('DiffSetHistory', 'extra_data', JSONField, null=True),
    AddField('FileDiff', 'extra_data', JSONField, null=True),
]
