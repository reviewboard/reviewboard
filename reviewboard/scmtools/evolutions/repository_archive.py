"""Add Repository archive fields.

This adds ``archived``, ``archived_timestamp``, and includes a new
``unique_together`` constraint.

Version Added:
    2.0.3
"""

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
