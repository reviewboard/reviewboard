"""Added FileAttachment.uuid.

Version Added:
    2.5
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('FileAttachment', 'uuid', models.CharField, max_length=255,
             initial=''),
]
