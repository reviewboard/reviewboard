from __future__ import unicode_literals

from django_evolution.mutations import MoveToDjangoMigrations


MUTATIONS = [
    MoveToDjangoMigrations(mark_applied=['0001_initial', '0002_08_updates']),
]
