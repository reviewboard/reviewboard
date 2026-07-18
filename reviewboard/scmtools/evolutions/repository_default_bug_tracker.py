"""Add Repository.default_bug_tracker.

Version Added:
    9.0
"""

from __future__ import annotations

from django.db import models
from django_evolution.mutations import AddField


# ConfiguredBugTracker is a new model in hostingsvcs. Make sure that app's
# models are created before this ForeignKey is added.
AFTER_EVOLUTIONS = [
    'hostingsvcs',
]


MUTATIONS = [
    AddField('Repository', 'default_bug_tracker', models.ForeignKey,
             null=True, related_model='hostingsvcs.ConfiguredBugTracker'),
]
