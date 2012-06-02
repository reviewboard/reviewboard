from django_evolution.mutations import AddField
from django.db import models
from djblets.util.fields import JSONField


MUTATIONS = [
    AddField('Repository', 'extra_data', JSONField, initial=u'{}'),
    AddField('Repository', 'hosting_account',
             models.ForeignKey, null=True,
             related_model='hostingsvcs.HostingServiceAccount')
]
