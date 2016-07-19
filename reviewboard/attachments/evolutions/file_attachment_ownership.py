from __future__ import unicode_literals

from django_evolution.mutations import AddField, ChangeField
from django.db import models


MUTATIONS = [
    AddField('FileAttachment', 'user', models.ForeignKey, null=True,
             related_model='auth.User'),
    AddField('FileAttachment', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite'),
    ChangeField('FileAttachment', 'file', initial=None, null=True),
]
