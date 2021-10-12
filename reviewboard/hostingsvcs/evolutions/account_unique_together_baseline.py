from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('HostingServiceAccount', 'unique_together', []),
]
