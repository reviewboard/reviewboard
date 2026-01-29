"""Add Repository.unique_together state for Django Evolution 0.7.

Version Added:
    2.0
"""

from __future__ import annotations

from django_evolution.mutations import ChangeMeta


MUTATIONS = [
    ChangeMeta('HostingServiceAccount', 'unique_together', []),
]
