from django_evolution.mutations import *
from django.db import models


MUTATIONS = [
    AddField('FileDiff', 'status', models.CharField, initial='M', max_length=1)
]

