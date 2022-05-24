"""Add DefaultReviewer.local_site.

Version Added:
    1.6
"""

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('DefaultReviewer', 'local_site', models.ForeignKey, null=True,
             related_model='site.LocalSite')
]
