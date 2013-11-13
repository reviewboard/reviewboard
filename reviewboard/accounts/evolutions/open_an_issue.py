from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'open_an_issue', models.BooleanField, initial=True)
]
