"""Add DefaultReviewer.repository field

Version Added:
    1.0.2
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DefaultReviewer', 'repository', models.ManyToManyField,
             related_model='scmtools.Repository')
]
