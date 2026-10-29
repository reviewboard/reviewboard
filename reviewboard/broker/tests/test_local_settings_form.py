"""Unit tests for reviewboard.broker.backends.local.LocalBrokerSettingsForm.

Version Added:
    9.0
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import TYPE_CHECKING

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.broker.backends.local import (
    LocalBrokerBackend,
    LocalBrokerSettingsForm,
)
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from djblets.siteconfig.models import SiteConfigurationSettings


class LocalBrokerSettingsFormTests(TestCase):
    """Unit tests for LocalBrokerSettingsForm.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: A temporary directory for queue paths.
    tempdir: str

    def setUp(self) -> None:
        """Set up state for a test.

        This will create a temporary directory for queue paths.
        """
        super().setUp()

        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-')

    def tearDown(self) -> None:
        """Tear down state for a test.

        This will remove the temporary directory.
        """
        # Restore permissions in case a test removed them.
        tempdir = self.tempdir

        os.chmod(tempdir, 0o700)
        shutil.rmtree(tempdir)

        super().tearDown()

    def test_load_with_queue_path(self) -> None:
        """Testing LocalBrokerSettingsForm.load with a stored queue path"""
        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'local': {
                    'queue_path': self.tempdir
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = LocalBrokerSettingsForm(broker_cls=LocalBrokerBackend)

            self.assertEqual(form.fields['queue_path'].initial, self.tempdir)

    def test_load_without_queue_path(self) -> None:
        """Testing LocalBrokerSettingsForm.load without a stored queue path"""
        with self.siteconfig_settings({'brokers': {}}):
            form = LocalBrokerSettingsForm(broker_cls=LocalBrokerBackend)

            self.assertIsNone(form.fields['queue_path'].initial)

    def test_save_with_queue_path(self) -> None:
        """Testing LocalBrokerSettingsForm.save with a queue path"""
        tempdir = self.tempdir

        with self.siteconfig_settings({'brokers': {}}):
            form = LocalBrokerSettingsForm(
                broker_cls=LocalBrokerBackend,
                data={
                    'queue_path': tempdir,
                },
            )

            self.assertTrue(form.is_valid())
            form.save()

            siteconfig = SiteConfiguration.objects.get_current()

            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'local': {
                        'queue_path': tempdir,
                    },
                },
            )

    def test_save_without_queue_path(self) -> None:
        """Testing LocalBrokerSettingsForm.save without a queue path"""
        siteconfig_settings: SiteConfigurationSettings = {
            'brokers': {
                'local': {
                    'queue_path': self.tempdir,
                },
            },
        }

        with self.siteconfig_settings(siteconfig_settings):
            form = LocalBrokerSettingsForm(
                broker_cls=LocalBrokerBackend,
                data={
                    'queue_path': '',
                },
            )

            self.assertTrue(form.is_valid())
            form.save()

            siteconfig = SiteConfiguration.objects.get_current()

            self.assertEqual(
                siteconfig.get('brokers'),
                {
                    'local': {
                        'queue_path': '',
                    },
                },
            )
