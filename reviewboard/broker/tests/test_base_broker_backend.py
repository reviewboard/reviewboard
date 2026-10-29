"""Unit tests for reviewboard.broker.base.backends.BaseBrokerBackend.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.broker.base.backends import (
    BaseBrokerBackend,
    logger as backends_logger,
)
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from typelets.json import JSONDictImmutable


class _MyBrokerBackend(BaseBrokerBackend):
    broker_id = 'test-broker'
    name = 'Test Broker'


class BaseBrokerBackendTests(TestCase):
    """Unit tests for BaseBrokerBackend.

    Version Added:
        9.0
    """

    def test_check_connection(self) -> None:
        """Testing BaseBrokerBackend.check_connection does nothing by
        default
        """
        broker = _MyBrokerBackend()

        # This should not raise.
        broker.check_connection({})

    def test_get_broker_settings(self) -> None:
        """Testing BaseBrokerBackend.get_broker_settings"""
        siteconfig_settings: JSONDictImmutable = {
            'brokers': {
                'test-broker': {
                    'key1': 'value1',
                    'key2': 123,
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            broker = _MyBrokerBackend()

            with self.assertNoLogs(logger=backends_logger):
                broker_settings = broker.get_broker_settings()

            self.assertEqual(
                broker_settings,
                {
                    'key1': 'value1',
                    'key2': 123,
                })

            siteconfig = SiteConfiguration.objects.get_current()
            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {
                        'key1': 'value1',
                        'key2': 123,
                    },
                })
            self.assertIs(siteconfig.settings['brokers']['test-broker'],
                          broker_settings)

    def test_get_broker_settings_with_unset(self) -> None:
        """Testing BaseBrokerBackend.get_broker_settings not set in siteconfig
        """
        # Temporarily override brokers so we can delete it and have it
        # restored after the test.
        with self.siteconfig_settings({'brokers': {}}):
            siteconfig = SiteConfiguration.objects.get_current()
            del siteconfig.settings['brokers']

            broker = _MyBrokerBackend()

            with self.assertNoLogs(logger=backends_logger):
                broker_settings = broker.get_broker_settings()

            self.assertEqual(broker_settings, {})

            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {},
                })
            self.assertIs(siteconfig.settings['brokers']['test-broker'],
                          broker_settings)

    def test_get_broker_settings_with_corrupt_broker_settings(self) -> None:
        """Testing BaseBrokerBackend.get_broker_settings with corrupt broker
        settings
        """
        siteconfig_settings: JSONDictImmutable = {
            'brokers': {
                'test-broker': [123],
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            broker = _MyBrokerBackend()

            with self.assertLogs(logger=backends_logger) as logs:
                broker_settings = broker.get_broker_settings()

            self.assertEqual(broker_settings, {})
            self.assertEqual(len(logs.output), 1)
            self.assertEqual(
                logs.records[0].message,
                "The configuration for broker 'test-broker' was corrupt and "
                "had to be reset. You may need to reconfigure your broker "
                "in Admin UI -> Background Tasks.")

            siteconfig = SiteConfiguration.objects.get_current()
            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {},
                })
            self.assertIs(siteconfig.settings['brokers']['test-broker'],
                          broker_settings)

    def test_get_broker_settings_with_corrupt_toplevel_settings(self) -> None:
        """Testing BaseBrokerBackend.get_broker_settings with corrupt top-level
        "broker" key settings
        """
        siteconfig_settings: JSONDictImmutable = {
            'brokers': [123],
        }

        with self.siteconfig_settings(siteconfig_settings):
            broker = _MyBrokerBackend()

            with self.assertLogs(logger=backends_logger) as logs:
                broker_settings = broker.get_broker_settings()

            self.assertEqual(broker_settings, {})
            self.assertEqual(len(logs.output), 1)
            self.assertEqual(
                logs.records[0].message,
                "The configuration for broker 'test-broker' was corrupt and "
                "had to be reset. You may need to reconfigure your broker "
                "in Admin UI -> Background Tasks.")

            siteconfig = SiteConfiguration.objects.get_current()
            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'test-broker': {},
                })
            self.assertIs(siteconfig.settings['brokers']['test-broker'],
                          broker_settings)
