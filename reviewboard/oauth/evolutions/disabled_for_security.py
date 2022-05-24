"""Add enabled and original_user fields to Application.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Application', 'enabled', models.BooleanField, initial=True),
    AddField('Application', 'original_user', models.ForeignKey, null=True,
             related_model='auth.User'),
]
