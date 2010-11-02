from django_evolution.mutations import *
from django.db import models


MUTATIONS = [
    AddField('Group', 'invite_only', models.BooleanField, initial=False),
]
