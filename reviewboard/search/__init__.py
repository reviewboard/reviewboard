"""A module exposing the search backends registry."""

from djblets.registries.importer import lazy_import_registry


#: The search backend registry.
search_backend_registry = \
    lazy_import_registry('reviewboard.search.search_backends.registry',
                         'SearchBackendRegistry')
