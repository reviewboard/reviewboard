from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('LocalSite', 'public', models.BooleanField, initial=False)
]
