"""Unit tests for reviewboard.search.search_backends.elasticsearch.

Version Added:
    5.0.4
"""

from __future__ import annotations

import kgb
from django.core.exceptions import ValidationError

from reviewboard.search.search_backends.base import SearchBackend
from reviewboard.search.search_backends.elasticsearch import (
    ElasticsearchBackend)
from reviewboard.testing import TestCase


class ElasticsearchBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for ElasticsearchBackend.

    Version Added:
        5.0.4
    """

    def setUp(self):
        # Don't let the default validation logic happen, since it'll be more
        # dependent on package/version availability.
        self.spy_on(SearchBackend.validate,
                    owner=SearchBackend,
                    call_original=False)

    def test_validate(self):
        """Testing ElasticsearchBackend.validate"""
        backend = ElasticsearchBackend()
        backend._ES_VERSION_SUPPORTED = True
        backend._es_version = [7, 0, 0]

        # This should not raise an exception.
        backend.validate(configuration={})

    def test_validate_with_no_dep_installed(self):
        """Testing ElasticsearchBackend.validate with elasticsearch dependency
        not installed
        """
        backend = ElasticsearchBackend()
        backend._ES_VERSION_SUPPORTED = False
        backend._es_version = None

        message = (
            'You need to install a supported version of the elasticsearch '
            'module. Compatible packages are: ReviewBoard[elasticsearch7], '
            'ReviewBoard[elasticsearch5], ReviewBoard[elasticsearch2]'
            'ReviewBoard[elasticsearch1]'
        )

        with self.assertRaises(ValidationError) as e:
            backend.validate(configuration={})

            self.assertEqual(e.errors, [message])

    def test_validate_with_incompatible_version_installed(self):
        """Testing ElasticsearchBackend.validate with incompatible
        elasticsearch dependency version
        """
        backend = ElasticsearchBackend()
        backend._ES_VERSION_SUPPORTED = False
        backend._es_version = [4, 1, 2]

        message = (
            'You need to install a supported version of the elasticsearch '
            'module. version 4.1.2 is not supported. Compatible packages are: '
            'ReviewBoard[elasticsearch7], ReviewBoard[elasticsearch5], '
            'ReviewBoard[elasticsearch2], ReviewBoard[elasticsearch1]'
        )

        with self.assertRaises(ValidationError) as e:
            backend.validate(configuration={})

            self.assertEqual(e.errors, [message])
