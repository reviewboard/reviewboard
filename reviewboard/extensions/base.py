"""Base support for writing custom extensions."""

from __future__ import unicode_literals

from djblets.extensions.extension import (Extension as DjbletsExtension,
                                          JSExtension as DjbletsJSExtension)
from djblets.extensions.manager import (ExtensionManager as
                                        DjbletsExtensionManager)


class Extension(DjbletsExtension):
    """Base class for custom extensions.

    See :ref:`writing-extensions` for information on how to make use of this
    class to write your own extensions, and the Djblets
    :py:class:`~djblets.extensions.extension.Extension` documentation for
    a full class reference.
    """
    pass


class JSExtension(DjbletsJSExtension):
    """Base class for JavaScript-side extensions.

    See :ref:`writing-extensions` for information on how to make use of this
    class to write your own JavaScript-side extensions, and the Djblets
    :py:class:`~djblets.extensions.extension.JSExtension` documentation for
    a full class reference.
    """
    pass


class ExtensionManager(DjbletsExtensionManager):
    """The extension manager used by Review Board.

    See the Djblets :py:class:`~djblets.extensions.manager.ExtensionManager`
    documentation for a full class reference.
    """
    pass


_extension_manager = None


def get_extension_manager():
    """Return the extension manager used by Review Board.

    The same instance will be returned every time.

    Returns:
        ExtensionManager:
        The extension manager used by Review Board.
    """
    global _extension_manager

    if not _extension_manager:
        _extension_manager = ExtensionManager('reviewboard.extensions')

    return _extension_manager
