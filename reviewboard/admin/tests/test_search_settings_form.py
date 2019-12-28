"""Unit tests for reviewboard.admin.forms.SearchSettingsForm."""

from __future__ import unicode_literals

import shutil
import tempfile

from django.forms import ValidationError
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.forms.search_settings import SearchSettingsForm
from reviewboard.search import search_backend_registry
from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)
from reviewboard.search.search_backends.whoosh import WhooshBackend
from reviewboard.testing.testcase import TestCase


class SearchSettingsFormTests(TestCase):
    """Unit tests for reviewboard.admin.forms.SearchSettingsForm."""

    def test_clean(self):
        """Testing SearchSettingsForm.clean"""
        index_dir = tempfile.mkdtemp()

        try:
            siteconfig = SiteConfiguration.objects.get_current()
            form = SearchSettingsForm(siteconfig, data={
                'search_enable': True,
                'search_backend_id': WhooshBackend.search_backend_id,
                'whoosh-search_index_file': index_dir,
            })

            self.assertTrue(form.is_valid())
        finally:
            shutil.rmtree(index_dir)

    def test_clean_invalid_backend(self):
        """Testing SearchSettingsForm.clean when the backend doesn't pass
        validation
        """
        class InvalidSearchBackendForm(SearchBackendForm):
            pass

        class InvalidSearchBackend(SearchBackend):
            search_backend_id = 'invalid'
            config_form_class = InvalidSearchBackendForm

            def validate(self):
                raise ValidationError('This backend is invalid.')

        backend = InvalidSearchBackend()
        search_backend_registry.register(backend)

        try:
            siteconfig = SiteConfiguration.objects.get_current()
            form = SearchSettingsForm(siteconfig, data={
                'search_enable': True,
                'search_backend_id': backend.search_backend_id,
            })

            self.assertFalse(form.is_valid())
            self.assertIn('search_backend_id', form.errors)
        finally:
            search_backend_registry.unregister(backend)

    def test_clean_missing_backend(self):
        """Testing SearchSettingsForm.clean when the backend doesn't exist"""
        siteconfig = SiteConfiguration.objects.get_current()
        form = SearchSettingsForm(siteconfig, data={
            'search_enable': True,
            'search_backend_id': 'non-existant',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('search_backend_id', form.errors)
