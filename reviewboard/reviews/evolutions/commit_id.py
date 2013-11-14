from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'commit_id', models.CharField, max_length=64,
             null=True, db_index=True)
]
