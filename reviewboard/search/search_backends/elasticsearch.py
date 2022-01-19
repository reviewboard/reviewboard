"""A backend for the Elasticsearch search engine."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _
from djblets.util.humanize import humanize_list

from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)

try:
    import elasticsearch
    es_version = elasticsearch.VERSION
except Exception:
    es_version = None


# NOTE: When updating the versions below, make sure you've also updated
#       the documentation in docs/manual/admin/sites/search-indexing.rst.


#: The supported major versions of Elasticsearch.
#:
#: There must be a backend class available for each version in this list.
#:
#: Type:
#:     tuple
SUPPORTED_ES_MAJOR_VERSIONS = (7, 5, 2, 1)

#: The latest supported major version of Elasticsearch.
#:
#: Type:
#:     int
LATEST_ES_MAJOR_VERSION = SUPPORTED_ES_MAJOR_VERSIONS[0]

#: Whether the installed version of the elasticsearch module is supported.
#:
#: Type:
#:     bool
ES_VERSION_SUPPORTED = (es_version is not None and
                        es_version[0] in SUPPORTED_ES_MAJOR_VERSIONS)


# Determine the module name for the Haystack Elasticsearch backend.
if ES_VERSION_SUPPORTED and es_version[0] > 1:
    _engine_class_version = es_version[0]
else:
    _engine_class_version = ''


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

    class Meta:
        if ES_VERSION_SUPPORTED:
            title = _('Elasticsearch %s.x') % es_version[0]
        else:
            title = _('Elasticsearch')

        fieldsets = (
            (None, {
                'description': _(
                    'Elasticsearch support requires a version of the '
                    '<a href="%(elasticsearch_url)s" target="_blank">'
                    'elasticsearch</a> Python package that both matches your '
                    'version of the Elasticsearch server and is compatible '
                    'with Review Board.'
                    '\n'
                    'We provide convenient packages for each supported major '
                    'version of Elasticsearch. For example, for Elasticsearch '
                    '%(major_version)s.x, install '
                    '<code>ReviewBoard[elasticsearch%(major_version)s]</code> '
                    'and then restart your web server:'
                    '\n'
                    '<code><strong>$</strong> pip install '
                    '"ReviewBoard[elasticsearch%(major_version)s]"</code>'
                    '\n'
                    '%(supported_versions)s are supported.'
                ) % {
                    'elasticsearch_url':
                        'https://pypi.org/project/elasticsearch/',
                    'major_version': LATEST_ES_MAJOR_VERSION,
                    'supported_versions': humanize_list([
                        '%s.x' % _major_version
                        for _major_version in SUPPORTED_ES_MAJOR_VERSIONS
                    ]),
                },
                'fields': ('url', 'index_name'),
            }),
        )


class ElasticsearchBackend(SearchBackend):
    """A search backend for integrating with Elasticsearch"""

    search_backend_id = 'elasticsearch'
    name = _('Elasticsearch')
    haystack_backend_name = (
        'reviewboard.search.search_backends.haystack_backports.'
        'elasticsearch%(version)s_backend.Elasticsearch%(version)sSearchEngine'
        % {
            'version': _engine_class_version,
        }
    )
    default_settings = {
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'reviewboard',
    }
    config_form_class = ElasticsearchConfigForm
    form_field_map = {
        'url': 'URL',
        'index_name': 'INDEX_NAME',
    }

    def validate(self, **kwargs):
        """Ensure that the elasticsearch Python module is installed.

        Raises:
            django.core.exceptions.ValidationError:
                Raised if the ``elasticsearch`` module is not installed or
                the version is incompatible.
        """
        # Check whether there's a supported version of the module available.
        # Note that technically, elasticsearch 1.x is supported, but it's
        # pretty old. If we're going to reference a version, we want to
        # reference 2.x.
        if not ES_VERSION_SUPPORTED:
            raise ValidationError(gettext(
                'You need to install a supported version of the '
                'elasticsearch module.'))

        super(ElasticsearchBackend, self).validate(**kwargs)
