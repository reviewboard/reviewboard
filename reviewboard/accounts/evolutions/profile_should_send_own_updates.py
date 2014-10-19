from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'should_send_own_updates', models.BooleanField,
             initial=True)
]
