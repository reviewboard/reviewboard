"""Evolution to add the scmtool_id field to Repository.

Version Added:
    5.0
"""

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('Repository', 'scmtool_id', models.CharField, max_length=255,
             null=True),
]
