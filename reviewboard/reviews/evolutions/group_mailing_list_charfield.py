from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Group', 'mailing_list', initial=None, max_length=254)
]
