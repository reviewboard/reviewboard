"""Add LocalSiteProfile.permissions.

Version Added:
    1.7.17
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('LocalSiteProfile', 'permissions', JSONField, null=True)
]
