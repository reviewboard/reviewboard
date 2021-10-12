from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('StatusUpdate', 'timeout', models.IntegerField, null=True)
]
