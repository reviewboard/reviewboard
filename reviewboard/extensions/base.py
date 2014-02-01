from __future__ import unicode_literals

from djblets.extensions.extension import Extension, JSExtension
from djblets.extensions.manager import ExtensionManager


__all__ = [
    'ExtensionManager', 'Extension', 'JSExtension', 'get_extension_manager'
]


_extension_manager = None


def get_extension_manager():
    global _extension_manager

    if not _extension_manager:
        _extension_manager = ExtensionManager("reviewboard.extensions")

    return _extension_manager
