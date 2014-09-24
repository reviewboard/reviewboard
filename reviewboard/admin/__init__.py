from __future__ import unicode_literals

from django.dispatch import receiver

from reviewboard.signals import initializing


@receiver(initializing)
def _on_initializing(*args, **kwargs):
    """Handler for when Review Board is initializing.

    This will begin listening for save/delete events on Group and
    Repository, invalidating the widget caches when changed.

    We do this during the initializing process instead of when the module
    is loaded in order to avoid any circular imports caused by
    reviewboard.reviews.models.
    """
    from reviewboard.admin.widgets import init_widgets

    init_widgets()
