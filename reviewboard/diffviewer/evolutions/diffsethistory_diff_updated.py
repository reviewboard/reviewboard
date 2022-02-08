from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DiffSetHistory', 'last_diff_updated', models.DateTimeField,
             null=True)
]
