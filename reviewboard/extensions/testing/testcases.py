"""Base test case support for extension unit tests."""

from __future__ import unicode_literals

from djblets.extensions.testing import ExtensionTestCaseMixin

from reviewboard.extensions.base import get_extension_manager
from reviewboard.testing import TestCase


class ExtensionTestCase(ExtensionTestCaseMixin, TestCase):
    """Base class for Review Board extension unit tests.

    Extension authors can subclass this to help write unit tests for their
    extensions, ensuring their functionality works as expected.

    See :ref:`testing-extensions` for information on how to write unit tests
    for extensions, and
    :py:class:`~djblets.extensions.testing.testcases.ExtensionTestCaseMixin`
    for the details on how this class works.
    """

    def get_extension_manager(self):
        """Return the extension manager used for these extensions.

        Subclasses don't need to override this unless they're doing something
        highly specialized.

        Returns:
            djblets.extensions.manager.ExtensionManager:
            The extension manager used for the unit tests.
        """
        return get_extension_manager()
