from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Repository', 'local_site', models.ForeignKey,
             null=True, related_model='site.LocalSite')
]
