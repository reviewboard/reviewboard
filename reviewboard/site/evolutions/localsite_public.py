"""Add LocalSite.public.

Version Added:
    1.7.21
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('LocalSite', 'public', models.BooleanField, initial=False)
]
