"""Base test case support for extension hook tests."""

from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.testing.testcases import ExtensionTestCaseMixin

from reviewboard.extensions.base import Extension
from reviewboard.testing.testcase import TestCase


class DummyExtension(Extension):
    registration = RegisteredExtension()


class ExtensionHookTestCaseMixin(ExtensionTestCaseMixin):
    """Mixin for extension hook unit tests.

    Version Added:
        3.0.24
    """

    extension_class = DummyExtension

    def get_extension_manager(self):
        """Return an extension manager for the test.

        The result will always be a new, un-keyed extension manager.

        Returns:
            djblets.extensions.manager.ExtensionManager:
            The new extension manager.
        """
        return ExtensionManager('')


class BaseExtensionHookTestCase(ExtensionHookTestCaseMixin, TestCase):
    """Base class for extension hook unit tests.

    Version Added:
        3.0.24
    """
