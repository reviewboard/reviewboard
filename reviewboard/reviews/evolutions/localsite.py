from __future__ import unicode_literals

from django_evolution.mutations import AddField, ChangeField
from django.db import models


MUTATIONS = [
    AddField('ReviewRequest', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite'),
    AddField('ReviewRequest', 'local_id', models.IntegerField, initial=None,
             null=True),
    AddField('Group', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite'),
    ChangeField('Group', 'name', initial=None, unique=False)
]
