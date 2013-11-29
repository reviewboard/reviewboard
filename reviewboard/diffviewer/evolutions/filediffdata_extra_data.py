from __future__ import unicode_literals

from django_evolution.mutations import AddField, DeleteField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('FileDiffData', 'extra_data', JSONField, null=True),
    DeleteField('FileDiffData', 'insert_count'),
    DeleteField('FileDiffData', 'delete_count'),
]
