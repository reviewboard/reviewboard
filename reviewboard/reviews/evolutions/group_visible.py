from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Group', 'visible', models.BooleanField, initial=True)
]
