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
                siteconfig.set(self.ENABLED_SERVICES_KEY, [GravatarService.id])
                siteconfig.set(self.DEFAULT_SERVICE_KEY, GravatarService.id)

            siteconfig.save()

        super(AvatarServiceRegistry, self).populate()

    def get_or_default(self, service_id=None):
        """Return either the requested avatar service or the default.

        If the requested service is unregistered or disabled, the default
        avatar service will be returned (which may be ``None`` if there is no
        default).

        Args:
            service_id (unicode, optional):
                The unique identifier of the service that is to be retrieved.
                If this is ``None``, the default service will be used.

        Returns:
            djblets.avatars.services.base.AvatarService:
            Either the requested avatar service, if it is both registered and
            enabled, or the default avatar service. If there is no default
            avatar service, this will return ``None``.
        """
        if (service_id is not None and
            self.has_service(service_id) and
            self.is_enabled(service_id)):
            return self.get('id', service_id)

        return self.default_service
