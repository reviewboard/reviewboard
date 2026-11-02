"""A backend for the Whoosh search engine."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from haystack.backends.whoosh_backend import WhooshEngine, WhooshSearchBackend
from whoosh.fields import KEYWORD
from whoosh.qparser import QueryParser
from whoosh.query import Every, NullQuery, Prefix, Query, TermRange, Wildcard

from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)

if TYPE_CHECKING:
    from typing import ClassVar


class WhooshConfigForm(SearchBackendForm):
    """A form for configuring the Whoosh search backend."""

    search_index_file = forms.CharField(
        label=_('Search index directory'),
        help_text=_('The directory that search index data should be stored '
                    'in.'),
        widget=forms.TextInput(attrs={'size': '80'}))

    def clean_search_index_file(self):
        """Clear the search_index_file field.

        This ensures the value is an absolute path and is writable.
        """
        index_file = self.cleaned_data['search_index_file'].strip()

        if index_file:
            if not os.path.isabs(index_file):
                raise ValidationError(
                    _('The search index path must be absolute.'))

            if (os.path.exists(index_file) and
                    not os.access(index_file, os.W_OK)):
                raise ValidationError(
                    _('The search index path is not writable. Make sure the '
                      'web server has write access to it and its parent '
                      'directory.'))

        return index_file


class RBWhooshQueryParser(QueryParser):
    """A Whoosh query parser that limits expensive term patterns.

    Wildcard, prefix, and range searches match every term in the index that
    fits the pattern. A short pattern can match a large part of the index,
    which takes a lot of time and memory.

    This parser ignores wildcard terms with fewer than
    :py:attr:`min_wildcard_prefix_len` characters before the first wildcard. It
    also ignores ranges over text. A bare ``*`` is turned into a cheaper search
    that matches everything.

    Keyword fields are left alone. Review Board uses them for access checks,
    which search them with wildcards. They only hold a few short values.

    Version Added:
        8.1.1
    """

    #: The fewest characters allowed before the first wildcard in a term.
    min_wildcard_prefix_len: ClassVar[int] = 3

    def parse(
        self,
        text: str,
        normalize: bool = True,
        debug: bool = False,
    ) -> Query:
        """Parse a query string.

        Args:
            text (str):
                The query string to parse.

            normalize (bool, optional):
                Whether to normalize the resulting query.

            debug (bool, optional):
                Whether to print debug output while parsing.

        Returns:
            whoosh.query.Query:
            The parsed query.
        """
        query = super().parse(text, normalize=normalize, debug=debug)
        query = query.accept(self._limit_term_patterns)

        if normalize:
            # This drops any terms that were replaced with NullQuery.
            query = query.normalize()

        return query

    def _limit_term_patterns(
        self,
        query: Query,
    ) -> Query:
        """Replace an expensive term pattern with a cheaper query.

        Args:
            query (whoosh.query.Query):
                The query to check.

        Returns:
            whoosh.query.Query:
            The query to use in its place.
        """
        fieldname = getattr(query, 'fieldname', None)

        if (fieldname is None or
            fieldname not in self.schema or
            isinstance(self.schema[fieldname], KEYWORD)):
            return query

        if isinstance(query, Every):
            return Every()

        if isinstance(query, TermRange):
            return NullQuery

        if isinstance(query, Prefix):
            literal = query.text
        elif isinstance(query, Wildcard):
            literal = re.split(r'[*?]', query.text, maxsplit=1)[0]
        else:
            return query

        if len(literal) < self.min_wildcard_prefix_len:
            return NullQuery

        return query


class RBWhooshSearchBackend(WhooshSearchBackend):
    """A Haystack Whoosh backend that limits expensive searches.

    Haystack turns on fuzzy terms (such as ``word~3``) in the Whoosh query
    parser. The cost of these grows very quickly with the number of edits, so
    a single query can run for minutes and use gigabytes of memory. This
    backend turns them off.

    It also uses :py:class:`RBWhooshQueryParser` to limit wildcard and range
    searches.

    Version Added:
        8.1.1
    """

    def setup(self) -> None:
        """Set up the backend.

        This replaces Haystack's query parser with one that leaves out fuzzy
        term support and limits wildcard and range searches.
        """
        super().setup()

        # Whoosh's default plugins don't include fuzzy terms.
        self.parser = RBWhooshQueryParser(self.content_field_name,
                                          schema=self.schema)


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
