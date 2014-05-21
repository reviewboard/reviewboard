from __future__ import unicode_literals


def has_module(module_name, members=[]):
    """Returns whether or not a given module can be imported."""
    try:
        mod = __import__(module_name, fromlist=members)
    except ImportError:
        return False

    for member in members:
        if not hasattr(mod, member):
            return False

    return True
