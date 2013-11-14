from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileDiffData', 'insert_count', models.IntegerField, null=True),
    AddField('FileDiffData', 'delete_count', models.IntegerField, null=True)
]
