"""Unit tests for reviewboard.search.signal_processor.SignalProcessor."""

from __future__ import unicode_literals

import haystack
import kgb
from djblets.siteconfig.models import SiteConfiguration
from haystack.signals import BaseSignalProcessor

from reviewboard.search.signal_processor import SignalProcessor, logger
from reviewboard.testing.testcase import TestCase


class SignalProcessorTests(kgb.SpyAgency, TestCase):
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

    def test_handle_delete_with_error(self):
        """Testing SignalProcessor.handle_delete with error"""
        exception = Exception('kaboom!')

        self.spy_on(BaseSignalProcessor.handle_delete,
                    owner=BaseSignalProcessor,
                    op=kgb.SpyOpRaise(exception))
        self.spy_on(logger.error)

        signal_processor = self._create_signal_processor()

        # This should not raise an exception.
        #
        # We'll use some garbage values.
        signal_processor.handle_delete(sender=None,
                                       instance=None)

        self.assertSpyCalled(BaseSignalProcessor.handle_delete)
        self.assertSpyCalledWith(
            logger.error,
            ('Error updating the search index. Check to make sure the '
             'search backend is running and configured correctly, and then '
             'rebuild the search index. Error: %s'),
            exception)

    def test_handle_save_with_error(self):
        """Testing SignalProcessor.handle_save with error"""
        exception = Exception('kaboom!')

        self.spy_on(BaseSignalProcessor.handle_save,
                    owner=BaseSignalProcessor,
                    op=kgb.SpyOpRaise(exception))
        self.spy_on(logger.error)

        signal_processor = self._create_signal_processor()

        # This should not raise an exception.
        #
        # We'll use some garbage values.
        signal_processor.handle_save(sender=None,
                                     instance=None)

        self.assertSpyCalled(BaseSignalProcessor.handle_save)
        self.assertSpyCalledWith(
            logger.error,
            ('Error updating the search index. Check to make sure the '
             'search backend is running and configured correctly, and then '
             'rebuild the search index. Error: %s'),
            exception)

    def _create_signal_processor(self):
        """Return a new instance of our Haystack signal processor.

        Returns:
            reviewboard.search.signal_processor.SignalProcessor:
            The new signal processor.
        """
        return SignalProcessor(haystack.connections,
                               haystack.connection_router)
