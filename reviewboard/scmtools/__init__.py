"""Module for interacting with different source code management tools."""

from djblets.registries.importer import lazy_import_registry

from reviewboard.signals import initializing


scmtools_registry = lazy_import_registry(
    'reviewboard.scmtools.registry',
    'SCMToolRegistry')


def _populate_registry(**kwargs):
    """Populate the SCMTools registry.

    Version Added:
        5.0

    Args:
        **kwargs (dict, unused):
            Keyword arguments sent by the signal.
    """
    # TODO: We do this here because we want the registry to be populated early
    # in case we need to create any new entries for the Tool table. We can't do
    # it in AppConfig.ready because that's not allowed to do database queries
    # (and can break things like building docs as a result). Once we get rid of
    # the Tool model, we can either move this into an AppConfig, or just let
    # the registry populate itself the first time it's accessed.
    scmtools_registry.populate()


initializing.connect(_populate_registry)
