"""Upgrade custom overridden models from oauth2_provider from 0.9 to 1.6.3.

Version Added:
    5.0
"""

from django.db import models
from django.utils import timezone
from django_evolution.mutations import AddField, ChangeField


MUTATIONS = [
    AddField('Application', 'created', models.DateTimeField,
             initial=timezone.now),
    AddField('Application', 'updated', models.DateTimeField,
             initial=timezone.now),
    AddField('Application', 'algorithm', models.CharField,
             max_length=5, initial=''),
    ChangeField('Application', 'user', initial=None, null=True),
    ChangeField('Application', 'id', field_type=models.BigAutoField,
                primary_key=True),
]
