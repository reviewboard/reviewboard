from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Review', 'general_comments', models.ManyToManyField,
             related_model='reviews.GeneralComment'),
]
