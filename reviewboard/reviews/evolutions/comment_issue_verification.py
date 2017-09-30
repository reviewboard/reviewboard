"""Evolution for adding issue verification."""

from __future__ import unicode_literals

from django_evolution.mutations import AddField
from djblets.db.fields import CounterField


MUTATIONS = [
    AddField('ReviewRequest', 'issue_verifying_count', CounterField,
             null=True),
]
