from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('ReviewRequest', 'depends_on', initial=None, null=False),
    ChangeField('ReviewRequestDraft', 'depends_on', initial=None, null=False),
]
