"""Base test case support for extension hook tests."""

from __future__ import unicode_literals

from djblets.extensions.manager import ExtensionManager
from djblets.extensions.models import RegisteredExtension

from reviewboard.extensions.base import Extension


class ExtensionManagerMixin(object):
    """Mixin used to setup a default ExtensionManager for tests."""

    def setUp(self):
        super(ExtensionManagerMixin, self).setUp()
        self.manager = ExtensionManager('')


class DummyExtension(Extension):
    registration = RegisteredExtension()
