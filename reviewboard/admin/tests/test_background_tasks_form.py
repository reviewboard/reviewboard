"""Unit tests for reviewboard.admin.forms.background_tasks.

Version Added:
    9.0
"""

from __future__ import annotations

import shutil
import tempfile
from typing import TYPE_CHECKING

import kgb
from django import forms
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.forms.background_tasks import BackgroundTasksForm
from reviewboard.broker.backends.local import LocalBrokerBackend
from reviewboard.broker.base.backends import BaseBrokerBackend
from reviewboard.broker.base.forms import BaseBrokerSettingsForm
from reviewboard.broker.registry import broker_registry
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from djblets.siteconfig.models import SiteConfigurationSettings


class _TestBrokerSettingsForm(BaseBrokerSettingsForm):
    host = forms.CharField(required=True)
    port = forms.IntegerField(required=False)


class _TestBrokerBackend(BaseBrokerBackend):
    broker_id = 'test-broker'
    name = 'Test Broker'
    settings_form = _TestBrokerSettingsForm


class _BrokenBrokerSettingsForm(BaseBrokerSettingsForm):
    def __init__(self, *args, **kwargs) -> None:
        raise Exception('Oh no')


class _BrokenBrokerBackend(BaseBrokerBackend):
    broker_id = 'broken-broker'
    name = 'Broken Broker'
    settings_form = _BrokenBrokerSettingsForm


class _NoFormBrokerBackend(BaseBrokerBackend):
    broker_id = 'no-form-broker'
    name = 'No Form Broker'


class BackgroundTasksFormTests(kgb.SpyAgency, TestCase):
    """Unit tests for BackgroundTasksForm.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The temporary directory used for the local queue path.
    queue_dir: str

    def setUp(self) -> None:
        """Set up state for a test.

        This will register a test broker backend with a settings form and
        create a temporary directory for the local queue path.
        """
        super().setUp()

        broker_registry.register(_TestBrokerBackend)
        self.queue_dir = tempfile.mkdtemp(prefix='rb-tests-')

    def tearDown(self) -> None:
        """Tear down state for a test.

        This will unregister the test broker backend and remove the
        temporary directory.
        """
        broker_registry.unregister(_TestBrokerBackend)
        shutil.rmtree(self.queue_dir)

        super().tearDown()

    def test_init(self) -> None:
        """Testing BackgroundTasksForm.__init__"""
        siteconfig = SiteConfiguration.objects.get_current()

        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'local': {
                    'queue_path': '/xxx/queue',
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = BackgroundTasksForm(siteconfig=siteconfig)

        self.assertEqual(
            form.fields['broker_id'].choices,
            [
                ('local', 'Local (filesystem)'),
                ('memory', 'Memory (testing only)'),
                ('test-broker', 'Test Broker'),
            ],
        )
        broker_backend_forms = form.broker_backend_forms

        self.assertEqual(set(broker_backend_forms),
                         {'local', 'test-broker'})
        self.assertIsInstance(broker_backend_forms['test-broker'],
                              _TestBrokerSettingsForm)

        local_form = broker_backend_forms['local']
        assert local_form is not None

        self.assertEqual(local_form.fields['queue_path'].initial, '/xxx/queue')

    def test_init_with_data_and_selected_broker(self) -> None:
        """Testing BackgroundTasksForm.__init__ with data binds the selected
        broker's subform
        """
        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'test-broker',
                'test-broker-host': 'broker.int.example.com',
                'test-broker-port': 12345,
            },
        )

        subform = form.broker_backend_forms['test-broker']
        self.assertTrue(subform.is_bound)
        self.assertTrue(subform.is_valid())

        cleaned_data = subform.clean()
        assert cleaned_data is not None

        self.assertEqual(cleaned_data['host'], 'broker.int.example.com')
        self.assertEqual(cleaned_data['port'], 12345)

    def test_init_with_data_and_unselected_broker(self) -> None:
        """Testing BackgroundTasksForm.__init__ with data does not bind
        unselected brokers' subforms
        """
        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'local',
                'test-broker-host': 'broker.int.example.com',
                'test-broker-port': 12345,
            },
        )

        subform = form.broker_backend_forms['test-broker']
        self.assertFalse(subform.is_bound)
        self.assertIsNone(subform['host'].data)
        self.assertIsNone(subform.fields['host'].initial)
        self.assertIsNone(subform['port'].data)
        self.assertIsNone(subform.fields['port'].initial)

    def test_init_with_data_and_selected_local_broker(self) -> None:
        """Testing BackgroundTasksForm.__init__ with data binds the local
        broker's subform when selected
        """
        queue_dir = self.queue_dir
        siteconfig = SiteConfiguration.objects.get_current()

        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'local',
                'local-queue_path': queue_dir,
            },
        )

        local_form = form.broker_backend_forms['local']
        assert local_form is not None

        self.assertTrue(local_form.is_bound)
        self.assertTrue(local_form.is_valid())

        cleaned_data = local_form.clean()
        assert cleaned_data is not None

        self.assertEqual(cleaned_data['queue_path'], queue_dir)

    def test_is_valid_with_invalid_broker_form(self) -> None:
        """Testing BackgroundTasksForm.is_valid with invalid form data for
        selected broker form
        """
        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'test-broker',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.broker_backend_forms['test-broker'].errors,
            {
                'host': ['This field is required.'],
            },
        )

    def test_is_valid_with_invalid_unselected_broker_form(self) -> None:
        """Testing BackgroundTasksForm.is_valid with invalid form data for
        unselected broker form
        """
        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'local',
            },
        )

        # The "host" field shouldn't be triggering a "This field is required"
        # error this time.
        self.assertTrue(form.is_valid())

    def test_is_valid_with_connection_check(self) -> None:
        """Testing BackgroundTasksForm.is_valid checks the connection using
        the new broker settings
        """
        self.spy_on(_TestBrokerBackend.check_connection,
                    owner=_TestBrokerBackend)

        with self.siteconfig_settings({'brokers': {}}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'test-broker',
                    'test-broker-host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            self.assertSpyCalledWith(
                _TestBrokerBackend.check_connection,
                {
                    'host': 'broker.example.com',
                    'port': None,
                },
            )

            # The new settings should not have been stored yet.
            self.assertNotIn('test-broker', siteconfig.get('brokers'))

    def test_is_valid_with_connection_check_error(self) -> None:
        """Testing BackgroundTasksForm.is_valid with a connection check
        error
        """
        self.spy_on(
            _TestBrokerBackend.check_connection,
            owner=_TestBrokerBackend,
            op=kgb.SpyOpRaise(Exception('Oh no')),
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'test-broker',
                'test-broker-host': 'broker.example.com',
            },
        )

        with self.assertLogs(level='ERROR'):
            self.assertFalse(form.is_valid())

        self.assertEqual(form.errors, {})
        self.assertEqual(
            form.broker_backend_forms['test-broker'].non_field_errors(),
            [
                'Unable to connect to the "Test Broker" broker: Oh no',
            ],
        )

    def test_is_valid_with_unselected_local_broker(self) -> None:
        """Testing BackgroundTasksForm.is_valid with the local broker
        unselected doesn't check the local broker's connection
        """
        self.spy_on(
            LocalBrokerBackend.check_connection,
            owner=LocalBrokerBackend,
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'test-broker',
                'test-broker-host': 'broker.example.com',
            },
        )

        self.assertTrue(form.is_valid())
        self.assertSpyNotCalled(LocalBrokerBackend.check_connection)

    def test_is_valid_with_local_connection_check_error(self) -> None:
        """Testing BackgroundTasksForm.is_valid with a local broker check
        error
        """
        self.spy_on(
            LocalBrokerBackend.check_connection,
            owner=LocalBrokerBackend,
            op=kgb.SpyOpRaise(ValueError('Oh no')),
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'local',
                'local-queue_path': self.queue_dir,
            },
        )

        with self.assertLogs(level='ERROR'):
            self.assertFalse(form.is_valid())

        local_form = form.broker_backend_forms['local']
        assert local_form is not None

        self.assertEqual(
            local_form.non_field_errors(),
            [
                'Unable to connect to the "Local (filesystem)" broker: '
                'Oh no',
            ],
        )

    def test_is_valid_with_connection_check_for_local_broker(self) -> None:
        """Testing BackgroundTasksForm.is_valid checks the local broker only
        once when it's the selected broker
        """
        self.spy_on(
            LocalBrokerBackend.check_connection,
            owner=LocalBrokerBackend,
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'local',
                'local-queue_path': self.queue_dir,
            },
        )

        self.assertTrue(form.is_valid())
        self.assertSpyCallCount(LocalBrokerBackend.check_connection, 1)

    def test_is_valid_without_connection_check_for_invalid_form(
        self,
    ) -> None:
        """Testing BackgroundTasksForm.is_valid without a connection check
        when the broker's settings are invalid
        """
        self.spy_on(
            _TestBrokerBackend.check_connection,
            owner=_TestBrokerBackend,
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'test-broker',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertSpyNotCalled(_TestBrokerBackend.check_connection)

    def test_is_valid_with_invalid_broker_id(self) -> None:
        """Testing BackgroundTasksForm.is_valid with an invalid broker ID"""
        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'xxx',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'broker_id': [
                    'Select a valid choice. xxx is not one of the available '
                    'choices.',
                ],
            },
        )

    def test_is_valid_with_unavailable_stored_broker_id(self) -> None:
        """Testing BackgroundTasksForm.is_valid with a stored broker ID that's
        no longer registered
        """
        with self.siteconfig_settings({'broker_id': 'old-broker'}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'old-broker',
                },
            )

            self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors,
            {
                'broker_id': [
                    'The broker "old-broker" is no longer available. '
                    'Please choose a different broker.',
                ],
            })

    def test_init_with_unavailable_stored_broker_id(self) -> None:
        """Testing BackgroundTasksForm.__init__ with a stored broker ID that's
        no longer registered
        """
        with self.siteconfig_settings({'broker_id': 'old-broker'}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(siteconfig=siteconfig)

        self.assertEqual(form.fields['broker_id'].initial, 'old-broker')
        self.assertEqual(
            form.fields['broker_id'].choices,
            [
                ('local', 'Local (filesystem)'),
                ('memory', 'Memory (testing only)'),
                ('test-broker', 'Test Broker'),
                ('old-broker', 'old-broker (no longer available)'),
            ],
        )

    def test_init_without_storing_broker_settings(self) -> None:
        """Testing BackgroundTasksForm.__init__ without adding settings for
        brokers to the site configuration
        """
        with self.siteconfig_settings({'brokers': {}}):
            siteconfig = SiteConfiguration.objects.get_current()
            BackgroundTasksForm(siteconfig=siteconfig)

            self.assertEqual(siteconfig.get('brokers'), {})

    def test_init_with_broken_broker_form(self) -> None:
        """Testing BackgroundTasksForm.__init__ with a broker settings form
        that fails to load
        """
        broker_registry.register(_BrokenBrokerBackend)
        self.addCleanup(
            lambda: broker_registry.unregister(_BrokenBrokerBackend),
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(siteconfig=siteconfig)

        self.assertIn(
            ('broken-broker', 'Broken Broker'),
            form.fields['broker_id'].choices,
        )
        self.assertIn('broken-broker', form.broker_backend_forms)
        self.assertIsNone(form.broker_backend_forms['broken-broker'])

    def test_is_valid_with_broken_broker_form(self) -> None:
        """Testing BackgroundTasksForm.is_valid with a selected broker whose
        settings form fails to load
        """
        broker_registry.register(_BrokenBrokerBackend)
        self.addCleanup(
            lambda: broker_registry.unregister(_BrokenBrokerBackend),
        )

        siteconfig = SiteConfiguration.objects.get_current()

        with self.assertLogs(level='ERROR'):
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'broken-broker',
                },
            )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'broker_id': [
                    'The settings for broker "Broken Broker" could not '
                    'be loaded. Check the Review Board log for details.',
                ],
            },
        )

    def test_is_valid_without_broker_settings_form(self) -> None:
        """Testing BackgroundTasksForm.is_valid with a selected broker that
        doesn't provide a settings form
        """
        broker_registry.register(_NoFormBrokerBackend)
        self.addCleanup(
            lambda: broker_registry.unregister(_NoFormBrokerBackend),
        )

        siteconfig = SiteConfiguration.objects.get_current()
        form = BackgroundTasksForm(
            siteconfig=siteconfig,
            data={
                'broker_id': 'no-form-broker',
            },
        )

        self.assertTrue(form.is_valid())

    def test_save_with_local(self) -> None:
        """Testing BackgroundTasksForm.save with local broker"""
        queue_dir = self.queue_dir

        with self.siteconfig_settings({'brokers': {}}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'local',
                    'local-queue_path': queue_dir,
                },
            )

            self.assertTrue(form.is_valid())

            self.spy_on(siteconfig.save)
            form.save()

            self.assertSpyCallCount(siteconfig.save, 1)

            # Make sure the settings were written to the database. Fetch an
            # explicit copy instead of calling refresh_from_db() so we don't
            # touch the cached copy.
            siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

            self.assertEqual(
                siteconfig.get('brokers').get('local'),
                {
                    'queue_path': queue_dir,
                },
            )

    def test_save_with_siteconfig_writes(self) -> None:
        """Testing BackgroundTasksForm.save writes the site configuration once
        """
        with self.siteconfig_settings({'brokers': {}}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'test-broker',
                    'test-broker-host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            self.spy_on(siteconfig.save)
            form.save()

            self.assertSpyCallCount(siteconfig.save, 1)

            # Make sure the settings were written to the database. Fetch an
            # explicit copy instead of calling refresh_from_db() so we don't
            # touch the cached copy.
            siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {
                        'host': 'broker.example.com',
                        'port': None,
                    },
                },
            )

    def test_save_with_non_local_broker(self) -> None:
        """Testing BackgroundTasksForm.save with non-local broker"""
        with self.siteconfig_settings({'broker_id': 'local'}):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'test-broker',
                    'test-broker-host': 'broker.example.com',
                    'test-broker-port': 12345,
                },
            )

            self.assertTrue(form.is_valid())

            self.spy_on(siteconfig.save)
            form.save()

            self.assertSpyCallCount(siteconfig.save, 1)

            # Make sure the settings were written to the database. Fetch an
            # explicit copy instead of calling refresh_from_db() so we don't
            # touch the cached copy.
            siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

            self.assertEqual(siteconfig.get('broker_id'), 'test-broker')
            self.assertEqual(
                siteconfig.get('brokers').get('test-broker'),
                {
                    'host': 'broker.example.com',
                    'port': 12345,
                },
            )

    def test_save_with_existing_unselected_broker_settings(self) -> None:
        """Testing BackgroundTasksForm.save preserves existing settings for an
        unselected broker
        """
        siteconfig_settings: SiteConfigurationSettings = {
            'broker_id': 'test-broker',
            'brokers': {
                'test-broker': {
                    'host': 'broker.example.com',
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            siteconfig = SiteConfiguration.objects.get_current()
            form = BackgroundTasksForm(
                siteconfig=siteconfig,
                data={
                    'broker_id': 'local',
                },
            )

            self.assertTrue(form.is_valid())

            self.spy_on(siteconfig.save)
            form.save()

            self.assertSpyCallCount(siteconfig.save, 1)

            # Make sure the settings were written to the database. Fetch an
            # explicit copy instead of calling refresh_from_db() so we don't
            # touch the cached copy.
            siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

            self.assertEqual(siteconfig.get('broker_id'), 'local')
            self.assertEqual(
                siteconfig.get('brokers').get('test-broker'),
                {
                    'host': 'broker.example.com',
                },
            )
