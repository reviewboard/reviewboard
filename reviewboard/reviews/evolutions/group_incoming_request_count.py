from __future__ import unicode_literals

from django_evolution.mutations import AddField
from djblets.db.fields import CounterField


MUTATIONS = [
    AddField('Group', 'incoming_request_count', CounterField, null=True,
             initial=None),
]
