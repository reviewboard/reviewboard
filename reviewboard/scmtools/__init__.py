"""Module for interacting with different source code management tools."""

from djblets.registries.importer import lazy_import_registry


scmtools_registry = lazy_import_registry(
    'reviewboard.scmtools.registry',
    'SCMToolRegistry')
