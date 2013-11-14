from __future__ import unicode_literals

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DefaultReviewer', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite')
]
