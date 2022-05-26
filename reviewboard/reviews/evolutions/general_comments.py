"""Add Review.general_comments field.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Review', 'general_comments', models.ManyToManyField,
             related_model='reviews.GeneralComment'),
]
