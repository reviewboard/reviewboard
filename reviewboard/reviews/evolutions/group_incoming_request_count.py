"""Add Group.incoming_request_count.

Version Added:
    1.6
"""

from __future__ import annotations

from django_evolution.mutations import AddField
from djblets.db.fields import CounterField


MUTATIONS = [
    AddField('Group', 'incoming_request_count', CounterField, null=True,
             initial=None),
]
