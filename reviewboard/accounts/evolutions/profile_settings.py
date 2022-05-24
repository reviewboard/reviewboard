"""Add Profile.settings.

Version Added:
    3.0
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('Profile', 'settings', JSONField, null=True),
]
