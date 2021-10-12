from django_evolution.mutations import AddField, ChangeMeta
from django.db import models


MUTATIONS = [
    AddField('Repository', 'hooks_uuid', models.CharField, max_length=32,
             null=True),
    ChangeMeta('Repository', 'unique_together',
               (('name', 'local_site'),
                ('archived_timestamp', 'path', 'local_site'),
                ('hooks_uuid', 'local_site'))),
]
