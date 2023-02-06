from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.registries.registry import (
    EntryPointRegistry as DjbletsEntryPointRegistry,
    OrderedRegistry as DjbletsOrderedRegistry,
    Registry as DjbletsRegistry,
    RegistryItemType)


class Registry(ExceptionFreeGetterMixin[RegistryItemType],
               DjbletsRegistry[RegistryItemType]):
    """A registry that does not throw exceptions for failed lookups."""


class EntryPointRegistry(ExceptionFreeGetterMixin[RegistryItemType],
                         DjbletsEntryPointRegistry[RegistryItemType]):
    """A registry that auto-populates from an entry-point."""


class OrderedRegistry(ExceptionFreeGetterMixin[RegistryItemType],
                      DjbletsOrderedRegistry[RegistryItemType]):
    """A registry that keeps track of registration order."""
