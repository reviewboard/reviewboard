"""Local Site-specfic initialization."""

from __future__ import unicode_literals

from reviewboard.signals import initializing


def _on_initializing(**kwargs):
    """Set up signal handlers for Local Sites."""
    from django.db.models.signals import m2m_changed

    from reviewboard.site.models import LocalSite
    from reviewboard.site.signal_handlers import on_users_changed

    m2m_changed.connect(on_users_changed, sender=LocalSite.users.through)


initializing.connect(_on_initializing)
