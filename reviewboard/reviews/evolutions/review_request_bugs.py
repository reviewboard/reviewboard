"""Add bugs relations to ReviewRequest and ReviewRequestDraft.

Version Added:
    9.0
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


# Bug has a ForeignKey to the new ConfiguredBugTracker model in hostingsvcs.
# Make sure that app's models are created before these relations are added.
AFTER_EVOLUTIONS = [
    'hostingsvcs',
]


MUTATIONS = [
    AddField('ReviewRequest', 'bugs', models.ManyToManyField,
             related_model='reviews.Bug'),
    AddField('ReviewRequestDraft', 'bugs', models.ManyToManyField,
             related_model='reviews.Bug'),
]
