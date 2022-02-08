from django_evolution.mutations import AddField, ChangeMeta
from django.db import models


MUTATIONS = [
    AddField('ReviewRequestVisit', 'visibility', models.CharField,
             initial='V', max_length=1),
    ChangeMeta('ReviewRequestVisit', 'index_together',
               [('user', 'visibility')])
]
