"""Search-related testing utilities."""

from __future__ import unicode_literals

from contextlib import contextmanager

from django.core.management import call_command
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.siteconfig import load_site_config


def reindex_search():
    """Rebuild the search index."""
    call_command('rebuild_index', interactive=False)


@contextmanager
def search_enabled(on_the_fly_indexing=False):
    """Temporarily enable indexed search.

    Args:
        on_the_fly_indexing (bool, optional):
            Whether or not to enable on-the-fly indexing.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if on_the_fly_indexing:
        siteconfig.set('search_on_the_fly_indexing', True)

    siteconfig.set('search_enable', True)
    siteconfig.save()
    load_site_config()

    try:
        yield
    finally:
        if on_the_fly_indexing:
            siteconfig.set('search_on_the_fly_indexing', False)

        siteconfig.set('search_enable', False)
        siteconfig.save()

        load_site_config()
