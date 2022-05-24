"""Add Group.email_list_only.

Version Added:
    2.5
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Group', 'email_list_only', models.BooleanField, initial=True)
]
