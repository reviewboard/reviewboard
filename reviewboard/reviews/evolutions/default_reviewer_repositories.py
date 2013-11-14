from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DefaultReviewer', 'repository', models.ManyToManyField,
             related_model='scmtools.Repository')
]
