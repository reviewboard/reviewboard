"""Configures pytest and Django environment setup for Review Board.

.. important::

   Do not define plugins in this file! Plugins must be in a different
   package (such as in tests/). pytest overrides importers for plugins and
   all modules descending from that module level, which will cause extension
   importers to fail, breaking unit tests.

Version Added:
    5.0
"""

import os
import sys

import django
import djblets

import reviewboard


sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


pytest_plugins = ['reviewboard.testing.pytest_fixtures']


def pytest_report_header(config):
    """Return information for the report header.

    This will log the version of Django.

    Args:
        config (object):
            The pytest configuration object.

    Returns:
        list of unicode:
        The report header entries to log.
    """
    return [
        'Review Board: %s' % reviewboard.get_version_string(),
        'Djblets: %s' % djblets.get_version_string(),
        'Django: %s' % django.get_version(),
    ]
