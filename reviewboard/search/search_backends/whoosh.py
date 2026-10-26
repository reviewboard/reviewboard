"""A backend for the Whoosh search engine."""

import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from haystack.backends.whoosh_backend import WhooshEngine, WhooshSearchBackend
from whoosh.qparser import FuzzyTermPlugin

from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)


class WhooshConfigForm(SearchBackendForm):
    """A form for configuring the Whoosh search backend."""

    search_index_file = forms.CharField(
        label=_("Search index directory"),
        help_text=_("The directory that search index data should be stored "
                    "in."),
        widget=forms.TextInput(attrs={'size': '80'}))

    def clean_search_index_file(self):
        """Clear the search_index_file field.

        This ensures the value is an absolute path and is writable.
        """
        index_file = self.cleaned_data['search_index_file'].strip()

        if index_file:
            if not os.path.isabs(index_file):
                raise ValidationError(
                    _("The search index path must be absolute."))

            if (os.path.exists(index_file) and
                    not os.access(index_file, os.W_OK)):
                raise ValidationError(
                    _('The search index path is not writable. Make sure the '
                      'web server has write access to it and its parent '
                      'directory.'))

        return index_file


class RBWhooshSearchBackend(WhooshSearchBackend):
    """A Haystack Whoosh backend without fuzzy term searches.

    Haystack turns on fuzzy terms (such as ``word~3``) in the Whoosh query
    parser. The cost of these grows very quickly with the number of edits,
    so a single query can run for minutes and use gigabytes of memory.
    This backend turns them off.

    Version Added:
        8.1.1
    """

    def setup(self) -> None:
        """Set up the backend.

        This removes fuzzy term support from the query parser.
        """
        super().setup()

        self.parser.remove_plugin_class(FuzzyTermPlugin)


class RBWhooshEngine(WhooshEngine):
    """A Haystack Whoosh engine that uses RBWhooshSearchBackend.

    Version Added:
        8.1.1
    """

    backend = RBWhooshSearchBackend


class WhooshBackend(SearchBackend):
    """The Whoosh search backend."""

    search_backend_id = 'whoosh'
    name = _('Whoosh')
    haystack_backend_name = \
        'reviewboard.search.search_backends.whoosh.RBWhooshEngine'
    config_form_class = WhooshConfigForm
    form_field_map = {
        'search_index_file': 'PATH',
    }

    @property
    def default_settings(self):
        """The default settings for the backend.

        This is dynamic, in order to account for a change to
        ``SITE_DATA_DIR``. In production, this value shouldn't change, but
        it does in unit tests.
        """
        return {
            'PATH': os.path.join(settings.SITE_DATA_DIR, 'search-index'),
            'STORAGE': 'file',
        }
