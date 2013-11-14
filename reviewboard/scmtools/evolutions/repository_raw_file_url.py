from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Repository', 'raw_file_url', models.CharField, initial='',
             max_length=128)
]
