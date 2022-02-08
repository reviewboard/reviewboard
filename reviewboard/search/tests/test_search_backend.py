"""Unit tests for reviewboard.search.search_backends.base.SearchBackend."""

import kgb
from django.core.exceptions import ValidationError
from djblets.siteconfig.models import SiteConfiguration

from haystack.backends.simple_backend import SimpleSearchBackend
from reviewboard.search.search_backends.base import SearchBackend
from reviewboard.testing.testcase import TestCase


class TestSimpleSearchBackend(SearchBackend):
    search_backend_id = 'simple'
    name = 'Simple Engine'
    haystack_backend_name = \
        'haystack.backends.simple_backend.SimpleEngine'
    default_settings = {
        'setting1': 'value1',
        'setting2': 42,
        'setting3': [1, 2, 3],
    }


class SearchBackend(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.search.search_backends.base.SearchBackend."""

    def setUp(self):
        super(SearchBackend, self).setUp()

        self.backend = TestSimpleSearchBackend()

    def test_configuration_getter_with_settings(self):
        """Testing SearchBackend.configuration getter with existing settings"""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('search_backend_settings', {
            'simple': {
                'setting1': 'new value',
                'setting3': [4, 5, 6],
            },
        })
        siteconfig.save(update_fields=('settings',))

        self.assertEqual(
            self.backend.configuration,
            {
                'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
                'setting1': 'new value',
                'setting2': 42,
                'setting3': [4, 5, 6],
            })

    def test_configuration_getter_without_settings(self):
        """Testing SearchBackend.configuration getter without any existing
        settings
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('search_backend_settings', {})
        siteconfig.save(update_fields=('settings',))

        self.assertEqual(
            self.backend.configuration,
            {
                'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
                'setting1': 'value1',
                'setting2': 42,
                'setting3': [1, 2, 3],
            })

        self.assertEqual(siteconfig.get('search_backend_settings'), {})

    def test_configuration_setter_with_existing_settings(self):
        """Testing SearchBackend.configuration setter with existing settings"""
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('search_backend_settings', {
            'simple': {
                'setting1': 'new value',
                'setting3': [4, 5, 6],
            },
        })
        siteconfig.save(update_fields=('settings',))

        self.backend.configuration = {
            'setting2': 100,
            'setting4': 'new',
        }

        # Explicitly fetch a new instance, rather than reloading the cached
        # version.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

        self.assertEqual(
            siteconfig.get('search_backend_settings'),
            {
                'simple': {
                    'setting1': 'new value',
                    'setting2': 100,
                    'setting3': [4, 5, 6],
                },
            })

    def test_configuration_setter_without_existing_settings(self):
        """Testing SearchBackend.configuration setter without existing
        settings
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('search_backend_settings', {})
        siteconfig.save(update_fields=('settings',))

        self.backend.configuration = {
            'setting2': 100,
            'setting4': 'new',
        }

        # Explicitly fetch a new instance, rather than reloading the cached
        # version.
        siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

        self.assertEqual(
            siteconfig.get('search_backend_settings'),
            {
                'simple': {
                    'setting2': 100,
                },
            })

    def test_validate(self):
        """Testing SearchBackend.validate"""
        self.backend.validate(configuration={
            'setting1': 'new value',
            'setting3': [4, 5, 6],
        })

    def test_validate_with_failure(self):
        """Testing SearchBackend.validate with failure"""
        self.spy_on(SimpleSearchBackend.search,
                    owner=SimpleSearchBackend,
                    func_name='search',
                    op=kgb.SpyOpRaise(Exception('Things went broken.')))

        message = (
            'Performing a test query failed. Make sure your configuration is '
            'correct. The error we received from the search backend was: '
            'Things went broken.'
        )

        with self.assertRaisesMessage(ValidationError, message):
            self.backend.validate(configuration={
                'setting1': 'new value',
                'setting3': [4, 5, 6],
            })
