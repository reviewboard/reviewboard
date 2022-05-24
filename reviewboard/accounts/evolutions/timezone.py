"""Add Profile.timezone.

Version Added:
    1.7
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'timezone', models.CharField, initial='UTC',
             max_length=20)
]
