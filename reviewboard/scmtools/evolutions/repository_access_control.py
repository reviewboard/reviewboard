"""Add Repository.public, review_groups, and users fields.

Version Added:
    1.6
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Repository', 'review_groups', models.ManyToManyField,
             related_model='reviews.Group'),
    AddField('Repository', 'public', models.BooleanField, initial=True),
    AddField('Repository', 'users', models.ManyToManyField,
             related_model='auth.User')
]
