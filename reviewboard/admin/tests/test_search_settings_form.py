"""Unit tests for reviewboard.admin.forms.SearchSettingsForm."""

import shutil
import tempfile

from django.forms import ValidationError
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.forms.search_settings import SearchSettingsForm
from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.search import search_backend_registry
from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)
from reviewboard.search.search_backends.whoosh import WhooshBackend
from reviewboard.testing.testcase import TestCase


class SearchSettingsFormTests(TestCase):
    """Unit tests for reviewboard.admin.forms.SearchSettingsForm."""

    def test_init(self):
        """Testing SearchSettingsForm.__init__"""
        siteconfig = SiteConfiguration.objects.get_current()
        form = SearchSettingsForm(siteconfig)
        subforms = form.search_backend_forms

        self.assertFalse(subforms['elasticsearch'].is_bound)
        self.assertFalse(subforms['whoosh'].is_bound)

    def test_init_with_data(self):
        """Testing SearchSettingsForm.__init__ with POST data"""
        siteconfig = SiteConfiguration.objects.get_current()
        form = SearchSettingsForm(siteconfig, data={
            'search_backend_id': 'whoosh',
        })
        subforms = form.search_backend_forms

        self.assertFalse(subforms['elasticsearch'].is_bound)
        self.assertTrue(subforms['whoosh'].is_bound)

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

    def test_clean_with_backend_validate_fail(self):
        """Testing SearchSettingsForm.clean when the backend doesn't pass
        validation
        """
        class InvalidSearchBackendForm(SearchBackendForm):
            pass

        class InvalidSearchBackend(SearchBackend):
            search_backend_id = 'invalid'
            config_form_class = InvalidSearchBackendForm

            def validate(self, **kwargs):
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
            self.assertEqual(form.errors['search_backend_id'],
                             ['This backend is invalid.'])
        finally:
            search_backend_registry.unregister(backend)

    def test_clean_with_backend_validate_legacy_fail(self):
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

            message = (
                'InvalidSearchBackend.validate() must accept keyword '
                'arguments. This will be required in Review Board 6.0.'
            )

            with self.assertWarns(RemovedInReviewBoard60Warning, message):
                self.assertFalse(form.is_valid())

            self.assertIn('search_backend_id', form.errors)
            self.assertEqual(form.errors['search_backend_id'],
                             ['This backend is invalid.'])
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
