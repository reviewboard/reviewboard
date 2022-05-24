"""Add depends_on field to ReviewRequest and ReviewRequestDraft.

Version Added:
    1.7.8
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'depends_on', models.ManyToManyField, null=True,
             related_model='reviews.ReviewRequest'),
    AddField('ReviewRequestDraft', 'depends_on', models.ManyToManyField,
             null=True, related_model='reviews.ReviewRequest')
]
