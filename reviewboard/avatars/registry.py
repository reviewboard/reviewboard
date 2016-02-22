from __future__ import unicode_literals

from djblets.avatars.registry import (
    AvatarServiceRegistry as DjbletsAvatarServiceRegistry)
from djblets.avatars.services.gravatar import GravatarService
from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.siteconfig.models import SiteConfiguration


class AvatarServiceRegistry(ExceptionFreeGetterMixin,
                            DjbletsAvatarServiceRegistry):
    """A registry for managing avatar services.

    This registry is a special case of Djblets'
    :py:class:`~djblets.avatars.registry.AvatarServiceRegistry` that will
    automatically migrate Review Board's settings (in the site configuration)
    from the old settings pertaining to Gravatars to the new avatar services
    preferences on first run.
    """

    #: The key for enabling avatars.
    AVATARS_ENABLED_KEY = 'avatars_enabled'

    #: The key for migrating avatars.
    AVATARS_MIGRATED_KEY = 'avatars_migrated'

    def populate(self):
        """Populate the avatar service registry.

        On first run, the site configuration will be migrated to use the new
        avatar services instead of the ``integration_gravatars`` setting.
        """
        if self.populated:
            return

        siteconfig = SiteConfiguration.objects.get_current()

        # Upon first run, migrate to the new avatar services settings.
        if not siteconfig.get(self.AVATARS_MIGRATED_KEY):
            avatars_enabled = siteconfig.get('integration_gravatars')
            siteconfig.set(self.AVATARS_MIGRATED_KEY, True)
            siteconfig.set(self.AVATARS_ENABLED_KEY, avatars_enabled)

            if avatars_enabled:
                siteconfig.set(self.ENABLED_SERVICES_KEY, [GravatarService.id])
                siteconfig.set(self.DEFAULT_SERVICE_KEY, GravatarService.id)

            siteconfig.save()

        super(AvatarServiceRegistry, self).populate()
