"""Registry for SCMTools.

Version Added:
    5.0
"""

import logging
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED)

from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.registries.registry import EntryPointRegistry
from reviewboard.scmtools.models import Tool


logger = logging.getLogger(__file__)


class SCMToolRegistry(EntryPointRegistry):
    """A registry for managing SCMTools.

    Version Added:
        5.0
    """

    entry_point = 'reviewboard.scmtools'

    lookup_attrs = [
        'class_name',
        'name',
        'scmtool_id',
    ]
    errors = {
        ALREADY_REGISTERED: _('"%(item)s" is already a registered SCMTool.'),
        LOAD_ENTRY_POINT: _(
            'Unable to load SCMTool %(entry_point)s: %(error)s'),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered SCMTool.'),
    }

    def __init__(self):
        """Initialize the registry."""
        super(SCMToolRegistry, self).__init__()

        self._initial_populate_done = False

    def populate(self):
        """Ensure the registry is populated.

        Calling this method when the registry is populated will have no effect.
        """
        if self._populated:
            return

        super(SCMToolRegistry, self).populate()

        if not self._initial_populate_done:
            # If there are any tools present that don't exist in the Tool
            # table, create those now. This obsoletes the old registerscmtools
            # management command.
            tools = list(Tool.objects.all())
            registered_tools = set(tool.class_name for tool in tools)

            new_tools = [
                Tool(name=scmtool_class.name,
                     class_name=scmtool_class.class_name)
                for scmtool_class in self
                if scmtool_class.class_name not in registered_tools
            ]

            if new_tools:
                Tool.objects.bulk_create(new_tools)

            # Look to see if anything exists in the database but does not exist
            # in entry points.
            for tool in tools:
                if self.get_by_class_name(tool.class_name) is None:
                    try:
                        self.register(tool.get_scmtool_class())
                        RemovedInReviewBoard60Warning.warn(
                            'SCMTool %s was found in the Tool table in the '
                            'database, but not in an entry point. The Tool '
                            'table will be removed in Review Board 6.0. To '
                            'continue using this tool, it must be manually '
                            'added by calling the register() method on the '
                            'SCMTools registry.'
                            % tool.class_name)
                    except ImproperlyConfigured as e:
                        logger.warning(
                            'SCMTool %s in the Tool table could not be '
                            'loaded: %s'
                            % (tool.class_name, e))

            self._initial_populate_done = True

    def get_defaults(self):
        """Yield to built-in SCMTools.

        Yields:
            type:
            The :py:class:`~reviewboard.scmtools.core.SCMTool` subclasses.
        """
        for _module, _scmtool_class_name in (
                ('bzr', 'BZRTool'),
                ('clearcase', 'ClearCaseTool'),
                ('cvs', 'CVSTool'),
                ('git', 'GitTool'),
                ('hg', 'HgTool'),
                ('perforce', 'PerforceTool'),
                ('plastic', 'PlasticTool'),
                ('svn', 'SVNTool'),
            ):
            mod = import_module('reviewboard.scmtools.%s' % _module)
            yield getattr(mod, _scmtool_class_name)

        for value in super(SCMToolRegistry, self).get_defaults():
            yield value

    def process_value_from_entry_point(self, entry_point):
        """Load the class from the entry point.

        The ``scmtool_id`` attribute will be set on the class from the entry
        point's name.

        Args:
            entry_point (pkg_resources.EntryPoint):
                The entry point.

        Returns:
            type:
            The :py:class:`~reviewboard.scmtools.core.SCMTool` subclass.
        """
        cls = entry_point.load()
        cls.scmtool_id = entry_point.name
        return cls

    def register(self, scmtool_class):
        """Register an SCMTool.

        If the tool does not have an existing Tool model instance in the
        database, this will create it.

        Args:
            scmtool_class (type):
                The :py:class:`~reviewboard.scmtools.core.SCMTool` subclass.
        """
        class_name = '%s.%s' % (scmtool_class.__module__,
                                scmtool_class.__name__)
        scmtool_class.class_name = class_name

        super(SCMToolRegistry, self).register(scmtool_class)

        if self._initial_populate_done:
            # Make sure the new tool exists in the Tool table as well.
            if not Tool.objects.filter(class_name=class_name).exists():
                Tool.objects.create(name=scmtool_class.name,
                                    class_name=class_name)

    def get_by_id(self, scmtool_id):
        """Return the SCMTool with the given ID.

        Args:
            scmtool_id (str):
                The ID of the SCMTool to fetch.

        Returns:
            reviewboard.scmtools.core.SCMTool:
            The SCMTool subclass.

        Raises:
            djblets.registries.errors.ItemLookupError:
                When a lookup is attempted with an unsupported attribute, or
                the item cannot be found, this exception is raised.
        """
        return self.get('scmtool_id', scmtool_id)

    def get_by_name(self, name):
        """Return the SCMTool with the given name.

        Args:
            name (str):
                The name of the SCMTool to fetch.

        Returns:
            reviewboard.scmtools.core.SCMTool:
            The SCMTool subclass.
        """
        return self.get('name', name)

    def get_by_class_name(self, class_name):
        """Return the SCMTool with the given class name.

        Args:
            class_name (str):
                The class name of the SCMTool to fetch.

        Returns:
            reviewboard.scmtools.core.SCMTool:
            The SCMTool subclass.

        Raises:
            djblets.registries.errors.ItemLookupError:
                When a lookup is attempted with an unsupported attribute, or
                the item cannot be found, this exception is raised.
        """
        return self.get('class_name', class_name)
