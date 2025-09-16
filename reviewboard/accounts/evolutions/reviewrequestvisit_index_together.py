"""Move from Meta.index_together to Meta.indexes for ReviewRequestVisit."""

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('ReviewRequestVisit', 'indexes',
               [{'fields': ['user', 'visibility']}]),
    ChangeMeta('ReviewRequestVisit', 'index_together', []),
]
