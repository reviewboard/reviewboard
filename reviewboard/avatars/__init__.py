"""Base support for Review Board avatars."""

from __future__ import unicode_literals

from djblets.registries.importer import lazy_import_registry


#: The avatar services registry.
avatar_services = lazy_import_registry('reviewboard.avatars.registry',
                                       'AvatarServiceRegistry')
