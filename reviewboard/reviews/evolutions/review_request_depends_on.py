from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'depends_on', models.ManyToManyField, null=True,
             related_model='reviews.ReviewRequest'),
    AddField('ReviewRequestDraft', 'depends_on', models.ManyToManyField,
             null=True, related_model='reviews.ReviewRequest')
]
