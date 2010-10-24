from django_evolution.mutations import *
from django.db import models

MUTATIONS = [
    AddField('ReviewRequest', 'local_site', models.ForeignKey, null=True, related_model='site.LocalSite'),
    AddField('ReviewRequest', 'local_id', models.IntegerField, initial=None, null=True),
    AddField('Group', 'local_site', models.ForeignKey, null=True, related_model='site.LocalSite')
]
