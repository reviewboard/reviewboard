from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'uuid', models.CharField, max_length=255,
             initial=''),
]
