from __future__ import unicode_literals

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('HostingServiceAccount', 'unique_together', []),
]
