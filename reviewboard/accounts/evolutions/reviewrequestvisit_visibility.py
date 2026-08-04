"""Add ReviewRequestVisit.visibility and add to index_together.

Version Added:
    2.5
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField, ChangeMeta


MUTATIONS = [
    AddField('ReviewRequestVisit', 'visibility', models.CharField,
             initial='V', max_length=1),
    ChangeMeta('ReviewRequestVisit', 'index_together',
               [('user', 'visibility')])
]
