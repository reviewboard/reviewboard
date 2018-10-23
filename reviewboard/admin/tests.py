from __future__ import unicode_literals

import os
import shutil
import tempfile

from django.conf import settings
from django.forms import ValidationError
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin import checks
from reviewboard.admin.forms import SearchSettingsForm
from reviewboard.admin.validation import validate_bug_tracker
from reviewboard.admin.widgets import (Widget,
                                       primary_widgets,
                                       register_admin_widget,
                                       secondary_widgets,
                                       unregister_admin_widget)
from reviewboard.search import search_backend_registry
from reviewboard.search.search_backends.base import (SearchBackend,
                                                     SearchBackendForm)
from reviewboard.search.search_backends.whoosh import WhooshBackend
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.ssh.client import SSHClient
from reviewboard.testing.testcase import TestCase


class UpdateTests(TestCase):
    """Tests for update required pages."""

    def setUp(self):
        """Set up this test case."""
        super(UpdateTests, self).setUp()

        self.old_media_root = settings.MEDIA_ROOT

    def tearDown(self):
        """Tear down this test case."""
        super(UpdateTests, self).tearDown()

        # Make sure we don't break further tests by resetting this fully.
        checks.reset_check_cache()

        # If test_manual_updates_bad_upload failed in the middle, it could
        # neglect to fix the MEDIA_ROOT, which will break a bunch of future
        # tests. Make sure it's always what we expect.
        settings.MEDIA_ROOT = self.old_media_root
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('site_media_root', self.old_media_root)
        siteconfig.save()

    def test_manual_updates(self):
        """Testing check_updates_required with valid configuration"""
        # NOTE: This is assuming the install is fine. It should be given
        #       that we set things like the uploaded path correctly to
        #       a known good directory before starting unit tests.
        updates_required = checks.check_updates_required()

        self.assertEqual(len(updates_required), 0)

    def test_manual_updates_bad_upload(self):
        """Testing check_updates_required with a bad upload directory"""
        siteconfig = SiteConfiguration.objects.get_current()

        siteconfig.set('site_media_root', '/')
        siteconfig.save()
        settings.MEDIA_ROOT = "/"
        checks.reset_check_cache()

        updates_required = checks.check_updates_required()
        self.assertEqual(len(updates_required), 2)

        url, data = updates_required[0]
        self.assertEqual(url, "admin/manual-updates/media-upload-dir.html")

        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/manual_updates_required.html")

        settings.MEDIA_ROOT = self.old_media_root
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('site_media_root', self.old_media_root)
        siteconfig.save()

        # Make sure that the site works again once the media root is fixed.
        response = self.client.get("/dashboard/")
        self.assertTemplateNotUsed(response,
                                   "admin/manual_updates_required.html")


class ValidatorTests(TestCase):
    """Unit tests for admin site validation methods."""

    def test_validate_bug_tracker(self):
        """Testing bug tracker url form field validation"""
        # Invalid - invalid format specification types
        self.assertRaises(ValidationError, validate_bug_tracker, "%20")
        self.assertRaises(ValidationError, validate_bug_tracker, "%d")

        # Invalid - too many format specification types
        self.assertRaises(ValidationError, validate_bug_tracker, "%s %s")

        # Invalid - no format specification types
        self.assertRaises(ValidationError, validate_bug_tracker, "www.a.com")

        # Valid - Escaped %'s, with a valid format specification type
        try:
            validate_bug_tracker("%%20%s")
        except ValidationError:
            self.assertFalse(True, "validate_bug_tracker() raised a "
                                   "ValidationError when no error was "
                                   "expected.")


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


class SSHSettingsFormTestCase(TestCase):
    """Unit tests for SSHSettingsForm in /admin/forms.py."""

    fixtures = ['test_users']

    def setUp(self):
        """Set up this test case."""
        super(SSHSettingsFormTestCase, self).setUp()

        # Setup temp directory to prevent the original ssh related
        # configurations been overwritten.
        self.old_home = os.getenv('HOME')
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')
        os.environ[b'RBSSH_ALLOW_AGENT'] = b'0'
        self._set_home(self.tempdir)

        self.ssh_client = SSHClient()

    def tearDown(self):
        """Tear down this test case."""
        super(SSHSettingsFormTestCase, self).tearDown()

        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def _set_home(self, homedir):
        """Set the $HOME environment variable."""
        os.environ[b'HOME'] = homedir.encode('utf-8')

    def test_generate_key(self):
        """Testing SSHSettingsForm POST with generate_key=1"""
        # Should have no ssh key at this point.
        self.assertEqual(self.ssh_client.get_user_key(), None)

        # Send post request with 'generate_key' = 1.
        self.client.login(username='admin', password='admin')
        response = self.client.post(local_site_reverse('settings-ssh'), {
            'generate_key': 1,
        })

        # On success, the form returns HTTP 302 (redirect).
        self.assertEqual(response.status_code, 302)

        # Check whether the key has been created.
        self.assertNotEqual(self.ssh_client.get_user_key(), None)

    def test_delete_key(self):
        """Testing SSHSettingsForm POST with delete_key=1"""
        # Should have no ssh key at this point, generate one.
        self.assertEqual(self.ssh_client.get_user_key(), None)
        self.ssh_client.generate_user_key()
        self.assertNotEqual(self.ssh_client.get_user_key(), None)

        # Send post request with 'delete_key' = 1.
        self.client.login(username='admin', password='admin')
        response = self.client.post(local_site_reverse('settings-ssh'), {
            'delete_key': 1,
        })

        # On success, the form returns HTTP 302 (redirect).
        self.assertEqual(response.status_code, 302)

        # Check whether the key has been deleted.
        self.assertEqual(self.ssh_client.get_user_key(), None)


class WidgetTests(TestCase):
    """Tests for administrator dashboard widgets."""

    fixtures = ['test_users']

    def setUp(self):
        """Set up this test case."""
        super(WidgetTests, self).setUp()

    def tearDown(self):
        """Tear down this test case."""
        super(WidgetTests, self).tearDown()

    def test_new_widget_render(self):
        """Testing that a new widget renders in the admin dashboard"""
        self.client.login(username='admin', password='admin')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        total_inital_widgets = (
            len(response.context['selected_secondary_widgets']) +
            len(response.context['selected_primary_widgets']))

        # Since admin/views.py widget_select() does not get run in testing,
        # we must do this instead to set up the data.
        profile = response.context['user'].get_profile()
        profile.extra_data.update({
            'primary_widget_selections': {
                widget.widget_id: '1'
                for widget in primary_widgets
            },
            'secondary_widget_selections': {
                widget.widget_id: '1'
                for widget in secondary_widgets
            },
            'primary_widget_positions': {
                widget.widget_id: i
                for i, widget in enumerate(primary_widgets)
            },
            'secondary_widget_positions': {
                widget.widget_id: i
                for i, widget in enumerate(secondary_widgets)
            },
        })
        profile.save(update_fields=('extra_data',))

        class TestPrimaryWidget(Widget):
            widget_id = 'test-primary-widget'

        class TestSecondaryWidget(Widget):
            widget_id = 'test-secondary-widget'

        # If either new widget doesn't render correctly, the page will break.
        try:
            register_admin_widget(TestPrimaryWidget, True)
            register_admin_widget(TestSecondaryWidget)

            # We must also add TestPrimaryWidget to primary_widget_selections
            # and TestSecondaryWidget to secondary_widget_selections, so that
            # they are selected to display on the page, but have no position.
            primary_selections = (
                profile.extra_data['primary_widget_selections'])
            secondary_selections = (
                profile.extra_data['secondary_widget_selections'])
            primary_selections[TestPrimaryWidget.widget_id] = '1'
            secondary_selections[TestSecondaryWidget.widget_id] = '1'
            profile.save(update_fields=('extra_data',))

            response = self.client.get('/admin/')
            self.assertEqual(response.status_code, 200)
            total_tested_widgets = (
                len(response.context['selected_secondary_widgets']) +
                len(response.context['selected_primary_widgets']))
            self.assertTrue(total_tested_widgets == total_inital_widgets + 2)
            self.assertIn(TestPrimaryWidget,
                          response.context['selected_primary_widgets'])
            self.assertIn(TestSecondaryWidget,
                          response.context['selected_secondary_widgets'])

        finally:
            # If an error was encountered above, the widgets will not be
            # registered. Ignore any errors in that case.
            try:
                unregister_admin_widget(TestPrimaryWidget)
            except KeyError:
                pass

            try:
                unregister_admin_widget(TestSecondaryWidget)
            except KeyError:
                pass
