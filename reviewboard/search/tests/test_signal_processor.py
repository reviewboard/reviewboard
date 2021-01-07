"""Unit tests for reviewboard.search.signal_processor.SignalProcessor."""

from __future__ import unicode_literals

import haystack
import kgb
from djblets.siteconfig.models import SiteConfiguration
from kgb import SpyAgency

from reviewboard.search.signal_processor import SignalProcessor
from reviewboard.testing.testcase import TestCase


class SignalProcessorTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.search.signal_processor.SignalProcessor."""

    def test_can_process_signals_with_siteconfig(self):
        """Testing SignalProcessor.can_process_signals with stored
        SiteConfiguration
        """
        self.assertIsNotNone(SiteConfiguration.objects.get_current())

        signal_processor = self._create_signal_processor()
        self.assertTrue(signal_processor.can_process_signals)

    def test_can_process_signals_without_siteconfig(self):
        """Testing SignalProcessor.can_process_signals without stored
        SiteConfiguration
        """
        self.spy_on(SiteConfiguration.objects.get_current,
                    op=kgb.SpyOpRaise(SiteConfiguration.DoesNotExist))

        signal_processor = self._create_signal_processor()
        self.assertFalse(signal_processor.can_process_signals)

        # Make sure it works once one has been created.
        SiteConfiguration.objects.get_current.unspy()
        self.assertTrue(signal_processor.can_process_signals)

    def _create_signal_processor(self):
        """Return a new instance of our Haystack signal processor.

        Returns:
            reviewboard.search.signal_processor.SignalProcessor:
            The new signal processor.
        """
        return SignalProcessor(haystack.connections,
                               haystack.connection_router)
