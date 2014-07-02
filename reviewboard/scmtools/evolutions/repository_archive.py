from __future__ import unicode_literals

from django_evolution.mutations import AddField, ChangeMeta
from django.db import models


MUTATIONS = [
    AddField('Repository', 'archived', models.BooleanField, initial=False),
    AddField('Repository', 'archived_timestamp', models.DateTimeField,
             null=True),
    ChangeMeta('Repository', 'unique_together',
               (('name', 'local_site'),
                ('archived_timestamp', 'path', 'local_site'))),
]
