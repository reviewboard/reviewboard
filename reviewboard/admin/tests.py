from __future__ import unicode_literals

import os
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils.encoding import force_str
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin import checks
from reviewboard.admin.form_widgets import (RelatedGroupWidget,
                                            RelatedRepositoryWidget,
                                            RelatedUserWidget)
from reviewboard.admin.forms import SearchSettingsForm
from reviewboard.admin.validation import validate_bug_tracker
from reviewboard.admin.widgets import (Widget, primary_widgets,
                                       register_admin_widget,
                                       secondary_widgets,
                                       unregister_admin_widget)
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository
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
        os.environ[str('RBSSH_ALLOW_AGENT')] = str('0')
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
        os.environ[str('HOME')] = force_str(homedir)

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


class RelatedUserWidgetTestCase(TestCase):
    """Unit tests for RelatedUserWidget."""

    fixtures = ['test_users']

    class TestForm(forms.Form):
        """A Test Form with a field that contains a RelatedUserWidget."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=User.objects.filter(is_active=True),
            label=('Default users'),
            required=False,
            widget=RelatedUserWidget())

    class LocalSiteTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedUserWidget.

        The RelatedUserWidget is defined to have a local_site_name."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=User.objects.filter(is_active=True),
            label=('Default users'),
            required=False,
            widget=RelatedUserWidget(local_site_name='supertest'))

    class SingleValueTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedUserWidget.

        The RelatedUserWidget is defined as setting multivalued to False."""
        my_select_field = forms.ModelMultipleChoiceField(
            queryset=User.objects.filter(is_active=True),
            label=('Default users'),
            required=False,
            widget=RelatedUserWidget(multivalued=False))

    def test_render_empty(self):
        """Testing RelatedUserWidget.render with no initial data"""
        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [],
            {'id': 'default-users'})
        self.assertHTMLEqual(
            """<input id="default-users" name="Default users" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedUserSelectorView({
                    $input: $('#default\\u002Dusers'),
                    initialOptions: [],

                    useAvatars: true,
                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedUserWidget.render with initial data"""
        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [1, 2, 3],
            {'id': 'default-users'})
        self.assertHTMLEqual(
            """<input id="default-users" name="Default users"
            type="hidden" value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedUserSelectorView({
                    $input: $('#default\\u002Dusers'),
                    initialOptions: [{"username": "admin", "fullname":
                    "Admin User", "id": 1,
                    "avatarURL": "https://secure.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61?s=40\\u0026d=mm"},
                    {"username": "doc", "fullname": "Doc Dwarf", "id": 2,
                    "avatarURL": "https://secure.gravatar.com/avatar/b0f1ae4342591db2695fb11313114b3e?s=40\\u0026d=mm"},
                    {"username": "dopey", "fullname": "Dopey Dwarf", "id": 3,
                    "avatarURL": "https://secure.gravatar.com/avatar/1a0098e6600792ea4f714aa205bf3f2b?s=40\\u0026d=mm"}],

                    useAvatars: true,
                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedUserWidget.render with a local site defined"""
        my_form = self.LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [],
            {'id': 'default-users'})
        self.assertIn(
            "localSitePrefix: 's/supertest/',",
            html)

    def test_value_from_datadict(self):
        """Testing RelatedUserWidget.value_from_datadict"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'people': ['1', '2']},
                {},
                'people'))
        self.assertEqual(['1', '2'], value)

    def test_value_from_datadict_single_value(self):
        """Testing RelatedUserWidget.value_from_datadict with a single value"""
        my_form = self.SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'people': ['1']},
                {},
                'people'))
        self.assertEqual(['1'], value)

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedUserWidget.value_from_datadict with no data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'people': []},
                {},
                'people'))
        self.assertEqual([], value)

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedUserWidget.value_from_datadict with missing data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'people'))
        self.assertEqual(None, value)


class RelatedRepositoryWidgetTestCase(TestCase):
    """Unit tests for RelatedRepositoryWidget."""

    fixtures = ['test_scmtools']

    class TestForm(forms.Form):
        """A Test Form with a field that contains a RelatedRepositoryWidget."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=Repository.objects.filter(visible=True).order_by('name'),
            label=('Repositories'),
            required=False,
            widget=RelatedRepositoryWidget())

    class LocalSiteTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedRepositoryWidget.

        The RelatedRepositoryWidget is defined to have a local_site_name."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=Repository.objects.filter(visible=True).order_by('name'),
            label=('Repositories'),
            required=False,
            widget=RelatedRepositoryWidget(local_site_name='supertest'))

    class SingleValueTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedRepositoryWidget.

        RelatedRepositoryWidget is defined as setting multivalued to False."""
        my_select_field = forms.ModelMultipleChoiceField(
            queryset=Repository.objects.filter(visible=True).order_by('name'),
            label=('Repositories'),
            required=False,
            widget=RelatedRepositoryWidget(multivalued=False))

    def test_render_empty(self):
        """Testing RelatedRepositoryWidget.render with no initial data"""
        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [],
            {'id': 'repositories'})
        self.assertHTMLEqual(
            """<input id="repositories" name="Repositories" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedRepoSelectorView({
                    $input: $('#repositories'),
                    initialOptions: [],

                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedRepositoryWidget.render with initial data"""
        test_repo_1 = self.create_repository(name='repo1')
        test_repo_2 = self.create_repository(name='repo2')
        test_repo_3 = self.create_repository(name='repo3')

        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [test_repo_1.pk, test_repo_2.pk, test_repo_3.pk],
            {'id': 'repositories'})
        self.assertHTMLEqual(
            """<input id="repositories" name="Repositories" type="hidden" value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedRepoSelectorView({
                    $input: $('#repositories'),
                    initialOptions: [{"id": 1, "name": "repo1"},
                    {"id": 2, "name": "repo2"},
                    {"id": 3, "name": "repo3"}],

                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedRepositoryWidget.render with a local site defined"""
        my_form = self.LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [],
            {'id': 'repositories'})
        self.assertIn(
            "localSitePrefix: 's/supertest/',",
            html)

    def test_value_from_datadict(self):
        """Testing RelatedRepositoryWidget.value_from_datadict"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'repository': ['1', '2']},
                {},
                'repository'))
        self.assertEqual(['1', '2'], value)

    def test_value_from_datadict_single_value(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with a single
        value"""
        my_form = self.SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'repository': ['1']},
                {},
                'repository'))
        self.assertEqual(['1'], value)

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with no data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'repository': []},
                {},
                'repository'))
        self.assertEqual([], value)

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with missing
        data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'repository'))
        self.assertEqual(None, value)


class RelatedGroupWidgetTestCase(TestCase):
    """Unit tests for RelatedRepositoryWidget."""

    class TestForm(forms.Form):
        """A Test Form with a field that contains a RelatedGroupWidget."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=Group.objects.filter(visible=True).order_by('name'),
            label=('Default groups'),
            required=False,
            widget=RelatedGroupWidget())

    class LocalSiteTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedGroupWidget.

        The RelatedGroupWidget is defined to have a local_site_name."""
        my_multiselect_field = forms.ModelMultipleChoiceField(
            queryset=Group.objects.filter(visible=True).order_by('name'),
            label=('Default groups'),
            required=False,
            widget=RelatedGroupWidget(local_site_name='supertest'))

    class SingleValueTestForm(forms.Form):
        """A Test Form with a field that contains a RelatedGroupWidget.

        RelatedGroupWidget is defined as setting multivalued to False."""
        my_select_field = forms.ModelMultipleChoiceField(
            queryset=Group.objects.filter(visible=True).order_by('name'),
            label=('Default groups'),
            required=False,
            widget=RelatedGroupWidget(multivalued=False))

    def test_render_empty(self):
        """Testing RelatedGroupWidget.render with no initial data"""
        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [],
            {'id': 'groups'})
        self.assertHTMLEqual(
            """<input id="groups" name="Default groups" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedGroupSelectorView({
                    $input: $('#groups'),
                    initialOptions: [],

                    multivalued: true,
                    inviteOnly: false
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedGroupWidget.render with initial data"""
        test_group_1 = self.create_review_group(name='group1')
        test_group_2 = self.create_review_group(name='group2')
        test_group_3 = self.create_review_group(name='group3')

        my_form = self.TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [test_group_1.pk, test_group_2.pk, test_group_3.pk],
            {'id': 'groups'})
        self.assertHTMLEqual(
            """<input id="groups" name="Default groups" type="hidden" value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedGroupSelectorView({
                    $input: $('#groups'),
                    initialOptions:
                    [{"display_name": "", "name": "group1", "id": 1},
                    {"display_name": "", "name": "group2", "id": 2},
                    {"display_name": "", "name": "group3", "id": 3}],

                    multivalued: true,
                    inviteOnly: false
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedGroupWidget.render with a local site defined"""
        my_form = self.LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [],
            {'id': 'groups'})
        self.assertIn(
            "localSitePrefix: 's/supertest/',",
            html)

    def test_value_from_datadict(self):
        """Testing RelatedGroupWidget.value_from_datadict"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'groups': ['1', '2']},
                {},
                'groups'))
        self.assertEqual(['1', '2'], value)

    def test_value_from_datadict_single_value(self):
        """Testing RelatedGroupWidget.value_from_datadict with single value"""
        my_form = self.SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'groups': ['1']},
                {},
                'groups'))
        self.assertEqual(['1'], value)

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedGroupWidget.value_from_datadict with no data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'groups': []},
                {},
                'groups'))
        self.assertEqual([], value)

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedGroupWidget.value_from_datadict with missing data"""
        my_form = self.TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'groups'))
        self.assertEqual(None, value)
