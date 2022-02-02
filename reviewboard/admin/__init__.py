"""Review Board's Administration UI."""

from django.dispatch import receiver
from django.utils.functional import SimpleLazyObject

from reviewboard.admin.model_admin import ModelAdmin
from reviewboard.signals import initializing


def _get_admin_site():
    """Return the AdminSite used for Review Board.

    Returns:
        reviewboard.admin.admin_sites.AdminSite:
        The main AdminSite instance.
    """
    from reviewboard.admin.admin_sites import admin_site

    return admin_site


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


#: The main instance for the Review Board administration site.
#:
#: Version Added:
#:     4.0
admin_site = SimpleLazyObject(_get_admin_site)


__all__ = [
    'ModelAdmin',
    'admin_site',
]
