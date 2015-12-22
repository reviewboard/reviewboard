from __future__ import unicode_literals

from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.registries.registry import (
    EntryPointRegistry as DjbletsEntryPointRegistry,
    OrderedRegistry as DjbletsOrderedRegistry,
    Registry as DjbletsRegistry)


class Registry(ExceptionFreeGetterMixin, DjbletsRegistry):
    """A registry that does not throw exceptions for failed lookups."""


class EntryPointRegistry(ExceptionFreeGetterMixin, DjbletsEntryPointRegistry):
    """A registry that auto-populates from an entry-point."""


class OrderedRegistry(ExceptionFreeGetterMixin, DjbletsOrderedRegistry):
    """A registry that keeps track of registration order."""
