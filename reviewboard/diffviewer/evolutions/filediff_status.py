from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileDiff', 'status', models.CharField, initial='M', max_length=1)
]
