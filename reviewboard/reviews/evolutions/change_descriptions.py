"""Add changedescs M2M fields to ReviewRequest and ReviewRequestDraft.

Version Added:
    1.0
"""

from django.db import models
from django_evolution.mutations import AddField


MUTATIONS = [
    AddField('ReviewRequest', 'changedescs', models.ManyToManyField,
             related_model='changedescs.ChangeDescription'),
    AddField('ReviewRequestDraft', 'changedesc', models.ForeignKey,
             initial=None, null=True,
             related_model='changedescs.ChangeDescription')
]
