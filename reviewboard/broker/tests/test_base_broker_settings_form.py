"""Unit tests for reviewboard.broker.base.forms.BaseBrokerSettingsForm.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django import forms
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.broker.base.backends import BaseBrokerBackend
from reviewboard.broker.base.forms import BaseBrokerSettingsForm
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from typing import Any

    from djblets.siteconfig.models import SiteConfigurationSettings


class _MyBrokerSettingsForm(BaseBrokerSettingsForm):
    host = forms.CharField()
    port = forms.IntegerField(required=False)


class _MyBrokerBackend(BaseBrokerBackend):
    broker_id = 'test-broker'
    name = 'Test Broker'
    settings_form = _MyBrokerSettingsForm


class _NestedBrokerSettingsForm(BaseBrokerSettingsForm):
    host = forms.CharField()

    def get_key_value(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.instance['connection'].get(key, default)

    def set_key_value(
        self,
        key: str,
        value: Any,
    ) -> None:
        self.instance['connection'][key] = value


class BaseBrokerSettingsFormTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseBrokerSettingsForm.

    Version Added:
        9.0
    """

    def test_full_clean_with_connection_check(self) -> None:
        """Testing BaseBrokerSettingsForm.full_clean checks the connection
        using the new settings
        """
        self.spy_on(
            _MyBrokerBackend.check_connection,
            owner=_MyBrokerBackend,
        )

        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'test-broker': {
                    'other': 'value',
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = _MyBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

        self.assertSpyCalledWith(
            _MyBrokerBackend.check_connection,
            {
                'host': 'broker.example.com',
                'other': 'value',
                'port': None,
            },
        )

    def test_full_clean_with_connection_check_error(self) -> None:
        """Testing BaseBrokerSettingsForm.full_clean with a connection check
        error
        """
        self.spy_on(
            _MyBrokerBackend.check_connection,
            owner=_MyBrokerBackend,
            op=kgb.SpyOpRaise(Exception('Oh no')),
        )

        form = _MyBrokerSettingsForm(
            broker_cls=_MyBrokerBackend,
            data={
                'host': 'broker.example.com',
            },
        )

        with self.assertLogs(level='ERROR'):
            self.assertFalse(form.is_valid())

        self.assertEqual(
            form.errors,
            {
                '__all__': [
                    'Unable to connect to the "Test Broker" broker: Oh no',
                ],
            },
        )

    def test_full_clean_without_connection_check_for_invalid_fields(
        self,
    ) -> None:
        """Testing BaseBrokerSettingsForm.full_clean without a connection
        check when fields are invalid
        """
        self.spy_on(
            _MyBrokerBackend.check_connection,
            owner=_MyBrokerBackend,
        )

        form = _MyBrokerSettingsForm(
            data={},
            broker_cls=_MyBrokerBackend,
        )

        self.assertFalse(form.is_valid())
        self.assertSpyNotCalled(_MyBrokerBackend.check_connection)

    def test_full_clean_without_connection_check_for_unbound(self) -> None:
        """Testing BaseBrokerSettingsForm.full_clean without a connection
        check when form data isn't provided
        """
        self.spy_on(
            _MyBrokerBackend.check_connection,
            owner=_MyBrokerBackend,
        )

        form = _MyBrokerSettingsForm(broker_cls=_MyBrokerBackend)
        form.full_clean()

        self.assertSpyNotCalled(_MyBrokerBackend.check_connection)

    def test_init_without_stored_settings(self) -> None:
        """Testing BaseBrokerSettingsForm.__init__ without stored settings
        doesn't add settings to the site configuration
        """
        with self.siteconfig_settings({'brokers': {}}):
            form = _MyBrokerSettingsForm(broker_cls=_MyBrokerBackend)

            siteconfig = SiteConfiguration.objects.get_current()

            self.assertEqual(form.instance, {})
            self.assertEqual(siteconfig.get('brokers'), {})

    def test_save_without_stored_settings(self) -> None:
        """Testing BaseBrokerSettingsForm.save without stored settings"""
        with self.siteconfig_settings({'brokers': {}}):
            form = _MyBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            siteconfig = SiteConfiguration.objects.get_current()

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

    def test_save_without_commit(self) -> None:
        """Testing BaseBrokerSettingsForm.save without commit doesn't save
        the site configuration
        """
        with self.siteconfig_settings({'brokers': {}}):
            form = _MyBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            siteconfig = SiteConfiguration.objects.get_current()

            self.spy_on(siteconfig.save)
            form.save(commit=False)

            self.assertSpyNotCalled(siteconfig.save)

            # The settings should be updated in memory, but not in the
            # database.
            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {
                        'host': 'broker.example.com',
                        'port': None,
                    },
                },
            )

            # Make sure the settings were written to the database. Fetch an
            # explicit copy instead of calling refresh_from_db() so we don't
            # touch the cached copy.
            siteconfig = SiteConfiguration.objects.get(pk=siteconfig.pk)

            self.assertEqual(siteconfig.get('brokers'), {})

    def test_get_pending_broker_settings_without_stored_settings(
        self,
    ) -> None:
        """Testing BaseBrokerSettingsForm.get_pending_broker_settings without
        stored settings
        """
        with self.siteconfig_settings({'brokers': {}}):
            form = _MyBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'broker.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            siteconfig = SiteConfiguration.objects.get_current()

            self.spy_on(siteconfig.save)

            self.assertEqual(
                form.get_pending_broker_settings(),
                {
                    'host': 'broker.example.com',
                    'port': None,
                },
            )

            # Nothing should have been stored.
            self.assertSpyNotCalled(siteconfig.save)
            self.assertEqual(siteconfig.get('brokers'), {})

    def test_get_pending_broker_settings_with_nested_settings(self) -> None:
        """Testing BaseBrokerSettingsForm.get_pending_broker_settings with
        nested settings
        """
        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'test-broker': {
                    'connection': {
                        'host': 'old.example.com',
                    },
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = _NestedBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'new.example.com',
                },
            )

            self.assertTrue(form.is_valid())

            siteconfig = SiteConfiguration.objects.get_current()

            self.spy_on(siteconfig.save)

            self.assertEqual(
                form.get_pending_broker_settings(),
                {
                    'connection': {
                        'host': 'new.example.com',
                    },
                },
            )

            # The stored settings should not have changed.
            self.assertSpyNotCalled(siteconfig.save)
            self.assertEqual(
                siteconfig.get('brokers')['test-broker'],
                {
                    'connection': {
                        'host': 'old.example.com',
                    },
                },
            )

    def test_get_pending_broker_settings(self) -> None:
        """Testing BaseBrokerSettingsForm.get_pending_broker_settings"""
        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'test-broker': {
                    'host': 'old.example.com',
                    'other': 'value',
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = _MyBrokerSettingsForm(
                broker_cls=_MyBrokerBackend,
                data={
                    'host': 'new.example.com',
                    'port': '5672',
                },
            )

            self.assertTrue(form.is_valid())

            siteconfig = SiteConfiguration.objects.get_current()

            self.spy_on(siteconfig.save)

            self.assertEqual(
                form.get_pending_broker_settings(),
                {
                    'host': 'new.example.com',
                    'other': 'value',
                    'port': 5672,
                },
            )

            # The stored settings should not have changed.
            self.assertSpyNotCalled(siteconfig.save)
            self.assertEqual(
                siteconfig.get('brokers')['test-broker'],
                {
                    'host': 'old.example.com',
                    'other': 'value',
                },
            )
            self.assertIsNot(form.instance,
                             siteconfig.settings['brokers']['test-broker'])
