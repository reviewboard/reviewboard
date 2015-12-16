from __future__ import unicode_literals

import logging
from pkg_resources import iter_entry_points

from django.utils.translation import ugettext as _
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import (DEFAULT_ERRORS as DJBLETS_ERRORS,
                                         Registry as DjbletsRegistry)


LOAD_ENTRY_POINT = 'load_entry_point'


DEFAULT_ERRORS = DJBLETS_ERRORS.copy()
DEFAULT_ERRORS.update({
    LOAD_ENTRY_POINT: _(
        'Could not load entry point %(entry_point)s: %(error)s'
    ),
})


class Registry(DjbletsRegistry):
    """A registry that does not throw exceptions for failed lookups."""

    def get(self, attr_name, attr_value):
        """Return the requested registered item.

        Args:
            attr_name (unicode):
                The attribute name.

            attr_value (object):
                The attribute value.

        Returns:
            object:
            The matching registered item, if found. Otherwise, ``None`` is
            returned.
        """
        try:
            return super(Registry, self).get(attr_name, attr_value)
        except ItemLookupError:
            return None


class EntryPointRegistry(Registry):
    """A registry that auto-populates from an entry-point."""

    #: The entry point name.
    entry_point = None

    default_errors = DEFAULT_ERRORS

    def get_defaults(self):
        """Yield the values from the given entry point.

        Yields:
            object:
            The object from the entry point.
        """
        if self.entry_point is not None:
            entry_points = iter_entry_points(self.entry_point)

            for ep in entry_points:
                try:
                    yield self.process_value_from_entry_point(ep)
                except Exception as e:
                    logging.exception(self.format_error(LOAD_ENTRY_POINT,
                                                        entry_point=ep.name,
                                                        error=e))

    def process_value_from_entry_point(self, entry_point):
        """Return the item to register from the entry point.

        By default, this returns the loaded entry point.

        Args:
            entry_point (pkg_resources.EntryPoint):
                The entry point.

        Returns:
            object:
            The processed entry point value.
        """
        return entry_point.load()
