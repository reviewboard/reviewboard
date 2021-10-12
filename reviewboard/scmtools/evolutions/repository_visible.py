from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Repository', 'visible', models.BooleanField, initial=True)
]
