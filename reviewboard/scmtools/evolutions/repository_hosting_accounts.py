from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('Repository', 'extra_data', JSONField, null=True),
    AddField('Repository', 'hosting_account',
             models.ForeignKey, null=True,
             related_model='hostingsvcs.HostingServiceAccount')
]
