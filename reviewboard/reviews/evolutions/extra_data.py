from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('ReviewRequest', 'extra_data', JSONField, null=True),
    AddField('Group', 'extra_data', JSONField, null=True),
    AddField('Review', 'extra_data', JSONField, null=True),
    AddField('ReviewRequestDraft', 'extra_data', JSONField, null=True),
]
