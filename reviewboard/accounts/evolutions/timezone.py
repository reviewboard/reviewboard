from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'timezone', models.CharField, initial='UTC',
             max_length=20)
]
