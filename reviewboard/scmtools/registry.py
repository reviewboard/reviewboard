"""Registry for SCMTools.

Version Added:
    5.0
"""

import logging
from importlib import import_module

from django.conf import settings
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
        self.conflicting_tools = []

    def populate(self):
        """Ensure the registry is populated.

        Calling this method when the registry is populated will have no effect.
        """
        if self.populated:
            return

        super(SCMToolRegistry, self).populate()

        if not self._initial_populate_done:
            self._initial_populate_done = True

            # Avoid populating the Tool entries by default when running unit
            # tests, so we can continue to have tests opt into new entries.
            # This avoids side effects and extra unnecessary test time.
            if not settings.RUNNING_TEST:
                self.populate_db()

    def populate_db(self):
        """Populate the database with missing Tool entries.

        For backwards-compatibility, this will ensure that there's a matching
        :py:class:`~reviewboard.scmtools.models.Tool` in the database for
        every registered SCMTool.

        This will be called automatically when the registry is first set up,
        and in response to any failed database queries for tools.

        It should not be called outside of Review Board.
        """
        # If there are any tools present that don't exist in the Tool
        # table, create those now. This obsoletes the old registerscmtools
        # management command.
        tools = list(Tool.objects.all())
        new_tools = []
        registered_by_class = {}
        registered_by_name = {}

        for tool in tools:
            registered_by_name[tool.name] = tool
            registered_by_class[tool.class_name] = tool

        conflicting_tools = []

        # If the user has a modified setup, they may have pointed a tool
        # to a different class path. We want to catch this and warn.
        for scmtool_cls in self:
            tool_by_name = registered_by_name.get(scmtool_cls.name)
            tool_by_class = registered_by_class.get(scmtool_cls.class_name)

            if tool_by_name is None and tool_by_class is None:
                # This is a brand-new Tool. Schedule it for population in the
                # database.
                new_tools.append(Tool(name=scmtool_cls.name,
                                      class_name=scmtool_cls.class_name))
            elif (tool_by_class is not None and
                  tool_by_class.name != scmtool_cls.name):
                # This tool matches another by class name, but isn't the same
                # tool.
                conflicting_tools.append((scmtool_cls, tool_by_class))
            elif (tool_by_name is not None and
                  tool_by_name.class_name != scmtool_cls.class_name):
                # This tool matches another by name, but isn't the same tool.
                conflicting_tools.append((scmtool_cls, tool_by_name))
            else:
                # This is already in the database, so skip it.
                pass

        self.conflicting_tools = sorted(
            conflicting_tools,
            key=lambda pair: pair[0].name)

        if conflicting_tools:
            for scmtool_cls, conflict_tool in self.conflicting_tools:
                logger.warning(
                    'Tool ID %d (name=%r, class_name=%r) conflicts with '
                    'SCMTool %r (name=%r, class_name=%r)',
                    conflict_tool.pk,
                    conflict_tool.name,
                    conflict_tool.class_name,
                    scmtool_cls.scmtool_id,
                    scmtool_cls.name,
                    scmtool_cls.class_name)

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
                        'SCMTool %r in the scmtools_tool table could not be '
                        'loaded: %s'
                        % (tool.class_name, e))

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
        """
        return self.get('class_name', class_name)
