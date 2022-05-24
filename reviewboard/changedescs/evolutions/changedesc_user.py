"""Add ChangeDescription.user.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('ChangeDescription', 'user', models.ForeignKey, null=True,
             related_model='auth.User'),
]
