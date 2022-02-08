from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('FileAttachmentComment', 'extra_data', JSONField, null=True)
]
