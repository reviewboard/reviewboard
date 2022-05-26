"""Add ChangeDescription.rich_text.

Version Added:
    2.0
"""

from django_evolution.mutations import AddField
from django.db import models

MUTATIONS = [
    AddField('ChangeDescription', 'rich_text', models.BooleanField,
             initial=False)
]
