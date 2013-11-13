from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models

MUTATIONS = [
    AddField('ChangeDescription', 'rich_text', models.BooleanField,
             initial=False)
]
