"""Base support for Review Board avatars."""

from djblets.registries.importer import lazy_import_registry


#: The avatar services registry.
avatar_services = lazy_import_registry('reviewboard.avatars.registry',
                                       'AvatarServiceRegistry')
