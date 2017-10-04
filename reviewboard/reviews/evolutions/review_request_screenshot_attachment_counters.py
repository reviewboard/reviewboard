from __future__ import unicode_literals

from django_evolution.mutations import AddField
from djblets.db.fields import RelationCounterField


MUTATIONS = [
    AddField('ReviewRequest', 'inactive_file_attachments_count',
             RelationCounterField, null=True),
    AddField('ReviewRequest', 'file_attachments_count', RelationCounterField,
             null=True),
    AddField('ReviewRequest', 'inactive_screenshots_count',
             RelationCounterField, null=True),
    AddField('ReviewRequest', 'screenshots_count', RelationCounterField,
             null=True),
    AddField('ReviewRequestDraft', 'inactive_file_attachments_count',
             RelationCounterField, null=True),
    AddField('ReviewRequestDraft', 'file_attachments_count',
             RelationCounterField, null=True),
    AddField('ReviewRequestDraft', 'inactive_screenshots_count',
             RelationCounterField, null=True),
    AddField('ReviewRequestDraft', 'screenshots_count',
             RelationCounterField, null=True),
]
