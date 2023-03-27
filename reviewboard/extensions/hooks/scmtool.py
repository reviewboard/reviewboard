"""A hook for registering SCMTools."""

from __future__ import annotations

from django.utils.translation import gettext as _
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.scmtools import scmtools_registry


class SCMToolHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for registering an SCMTool."""

    def initialize(self, scmtool_cls):
        """Initialize the hook.

        This will register the SCMTool.

        Args:
            scmtool_cls (type):
                The SCMTool class to register. This must be a subclass of
                :py:class:`~reviewboard.scmtools.core.SCMTool`.

        Raises:
            ValueError:
                The SCMTool's :py:attr:`~reviewboard.scmtools.core.SCMTool.
                scmtool_id` attribute was not set.
        """
        scmtool_id = scmtool_cls.scmtool_id

        if scmtool_id is None:
            raise ValueError(_('%s.scmtool_id must be set.')
                             % scmtool_cls.__name__)

        self.scmtool_id = scmtool_id
        scmtools_registry.register(scmtool_cls)

    def shutdown(self):
        """Shut down the hook.

        This will unregister the SCMTool.
        """
        scmtools_registry.unregister_by_attr('scmtool_id', self.scmtool_id)
