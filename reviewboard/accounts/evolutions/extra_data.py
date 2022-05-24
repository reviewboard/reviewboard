"""Added Profile.extra_data.

Version Added:
    1.7.8
"""

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('Profile', 'extra_data', JSONField, null=True)
]
