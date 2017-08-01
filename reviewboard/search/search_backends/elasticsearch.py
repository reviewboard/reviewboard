"""A backend for the Elasticsearch search engine."""

from __future__ import unicode_literals

from importlib import import_module

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)


class ElasticsearchConfigForm(SearchBackendForm):
    """A form for configuring the Elasticsearch search backend."""

    url = forms.URLField(
        label=_('Elasticsearch URL'),
        help_text=_('The URL of the Elasticsearch server.'),
        widget=forms.TextInput(attrs={'size': 80}))

    index_name = forms.CharField(
        label=_('Elasticsearch index name'),
        help_text=_('The name of the Elasticsearch index.'),
        widget=forms.TextInput(attrs={'size': 40}))


class ElasticsearchBackend(SearchBackend):
    """A search backend for integrating with Elasticsearch"""

    search_backend_id = 'elasticsearch'
    name = _('Elasticsearch')
    haystack_backend_name = ('haystack.backends.elasticsearch_backend.'
                             'ElasticsearchSearchEngine')
    default_settings = {
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'reviewboard',
    }
    config_form_class = ElasticsearchConfigForm
    form_field_map = {
        'url': 'URL',
        'index_name': 'INDEX_NAME',
    }

    def validate(self):
        """Ensure that the elasticsearch Python module is installed.

        Raises:
            django.core.exceptions.ValidationError:
                Raised if the ``elasticsearch`` module is not installed.
        """
        try:
            import_module('elasticsearch')
        except ImportError:
            raise ValidationError(ugettext(
                'The "elasticsearch" module is required to use the '
                'Elasticsearch search engine.'
            ))
