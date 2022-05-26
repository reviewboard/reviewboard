"""Added FileAttachment.uuid.

Version Added:
    2.5
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'uuid', models.CharField, max_length=255,
             initial=''),
]
