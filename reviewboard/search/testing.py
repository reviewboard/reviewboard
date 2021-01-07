"""Search-related testing utilities."""

from __future__ import unicode_literals

import tempfile
import time
from contextlib import contextmanager

import haystack
from django.conf import settings
from django.core.management import call_command
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.siteconfig import load_site_config


def reindex_search():
    """Rebuild the search index."""
    call_command('rebuild_index', interactive=False)

    # On Whoosh, the above is asynchronous, and we can end up trying to read
    # before we end up writing, occasionally breaking tests. We need to
    # introduce just a bit of a delay.
    #
    # Yeah, this is still sketchy, but we can't turn off the async behavior
    # or receive notification that the write has completed.
    time.sleep(0.1)


@contextmanager
def search_enabled(on_the_fly_indexing=False, backend_id='whoosh'):
    """Temporarily enable indexed search.

    Args:
        on_the_fly_indexing (bool, optional):
            Whether or not to enable on-the-fly indexing.

        backend_id (unicode, optional):
            The search backend to enable. Valid options are "whoosh" (default)
            and "elasticsearch".
    """
    siteconfig = SiteConfiguration.objects.get_current()

    old_backend_id = siteconfig.get('search_backend_id')
    old_backend_settings = siteconfig.get('search_backend_settings')

    if backend_id == 'whoosh':
        backend_settings = {
            'PATH': tempfile.mkdtemp(suffix='search-index',
                                     dir=settings.SITE_DATA_DIR),
            'STORAGE': 'file',
        }
    elif backend_id == 'elasticsearch':
        backend_settings = {
            'INDEX_NAME': 'reviewboard-tests',
            'URL': 'http://es.example.com:9200/',
        }
    else:
        raise NotImplementedError('Unexpected backend ID "%s"' % backend_id)

    siteconfig.settings.update({
        'search_enable': True,
        'search_backend_id': backend_id,
        'search_backend_settings': {
            backend_id: backend_settings,
        },
        'search_on_the_fly_indexing': on_the_fly_indexing,
    })
    siteconfig.save(update_fields=('settings',))

    load_site_config()

    try:
        yield

        haystack.connections['default'].reset_sessions()
    finally:
        siteconfig.settings.update({
            'search_enable': False,
            'search_backend_id': old_backend_id,
            'search_backend_settings': old_backend_settings,
            'search_on_the_fly_indexing': False,
        })
        siteconfig.save(update_fields=('settings',))

        load_site_config()
