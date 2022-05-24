"""Add LocalSite.extra_data.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('LocalSite', 'extra_data', JSONField, null=True)
]
