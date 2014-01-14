from __future__ import unicode_literals

from django_evolution.mutations import AddField
from djblets.db.fields import CounterField


MUTATIONS = [
    AddField('ReviewRequest', 'issue_dropped_count', CounterField, null=True),
    AddField('ReviewRequest', 'issue_resolved_count', CounterField, null=True),
    AddField('ReviewRequest', 'issue_open_count', CounterField, null=True),
]
