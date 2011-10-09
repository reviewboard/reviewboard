from djblets.extensions.base import ExtensionManager


_extension_manager = None

def get_extension_manager():
    global _extension_manager

    if not _extension_manager:
        _extension_manager = ExtensionManager("reviewboard.extensions")

    return _extension_manager
