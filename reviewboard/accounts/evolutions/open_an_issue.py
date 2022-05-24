"""Add Profile.open_an_issue.

Version Added:
    1.7
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'open_an_issue', models.BooleanField, initial=True)
]
