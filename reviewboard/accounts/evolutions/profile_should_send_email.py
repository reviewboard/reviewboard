"""Add Profile.should_send_email.

Version Added:
    2.0.2
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'should_send_email', models.BooleanField, initial=True)
]
