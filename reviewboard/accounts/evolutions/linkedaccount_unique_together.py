"""Set unique_together for LinkedAccount.

Version Added:
    5.0
"""

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('LinkedAccount', 'unique_together',
               [('service_user_id', 'service_id')]),
]
