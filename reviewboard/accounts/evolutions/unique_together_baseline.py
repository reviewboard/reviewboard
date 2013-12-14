from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('ReviewRequestVisit', 'unique_together',
               [('user', 'review_request')]),
    ChangeMeta('LocalSiteProfile', 'unique_together',
               [('user', 'local_site'), ('profile', 'local_site')]),
]
