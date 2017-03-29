from __future__ import unicode_literals

from djblets.avatars.registry import (
    AvatarServiceRegistry as DjbletsAvatarServiceRegistry)
from djblets.avatars.services import (GravatarService,
                                      URLAvatarService)
from djblets.registries.mixins import ExceptionFreeGetterMixin
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.avatars.services import FileUploadService
from reviewboard.avatars.settings import UserProfileAvatarSettingsManager


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

    #: The default avatar service classes.
    default_avatar_service_classes = [
        GravatarService,
        FileUploadService,
        URLAvatarService,
    ]

    settings_manager_class = UserProfileAvatarSettingsManager

    @property
    def avatars_enabled(self):
        """Whether or not avatars are enabled.

        Returns:
            bool: Whether or not avatars are enabled.
        """
        self.populate()

        siteconfig = SiteConfiguration.objects.get_current()
        return siteconfig.get(self.AVATARS_ENABLED_KEY)

    @avatars_enabled.setter
    def avatars_enabled(self, value):
        """Set whether or not avatars are enabled.

        Args:
            value (bool):
                Whether or not avatars are to be enabled.
        """
        self.populate()

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set(self.AVATARS_ENABLED_KEY, value)
        siteconfig.save()

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
                siteconfig.set(
                    self.ENABLED_SERVICES_KEY, [
                        service.avatar_service_id
                        for service in self.default_avatar_service_classes
                    ]
                )
                siteconfig.set(self.DEFAULT_SERVICE_KEY,
                               GravatarService.avatar_service_id)

            siteconfig.save()

        super(AvatarServiceRegistry, self).populate()
