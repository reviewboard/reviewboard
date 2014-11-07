from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'default_use_rich_text', models.NullBooleanField,
             initial=None, null=True),
]
