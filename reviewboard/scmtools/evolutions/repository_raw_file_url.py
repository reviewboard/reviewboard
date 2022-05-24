"""Add Repository.raw_file_url.

Version Added:
    1.1
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Repository', 'raw_file_url', models.CharField, initial='',
             max_length=128)
]
