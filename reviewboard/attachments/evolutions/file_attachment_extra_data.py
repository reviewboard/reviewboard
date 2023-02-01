"""Added FileAttachment.extra_data.

Version Added:
    6.0
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('FileAttachment', 'extra_data', JSONField, null=True),
]
