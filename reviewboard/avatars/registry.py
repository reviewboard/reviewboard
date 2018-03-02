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
    track the enabled state for avatars, and provide functionality for
    migrating from older (pre-3.0 and 3.0 through 3.0.3) avatar settings
    to modern settings.
    """

    #: The key for enabling avatars.
    AVATARS_ENABLED_KEY = 'avatars_enabled'

    #: The legacy key for tracking avatar settings migrations.
    #:
    #: This was used in Review Board 3.0 through 3.0.3. This is no longer
    #: stored in settings, and is used as part of the settings migration
    #: process.
    LEGACY_AVATARS_MIGRATED_KEY = 'avatars_migrated'

    #: The legacy key for enabling Gravatars.
    #:
    #: This was used in Review Board 2.0 up until 3.0 and kept in settings
    #: through 3.0.3. This is no longer stored in settings, and is used as
    #: part of the settings migration process.
    LEGACY_INTEGRATION_GRAVATARS_KEY = 'integration_gravatars'

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
        siteconfig = SiteConfiguration.objects.get_current()
        return siteconfig.get(self.AVATARS_ENABLED_KEY)

    @avatars_enabled.setter
    def avatars_enabled(self, value):
        """Set whether or not avatars are enabled.

        This will not automatically save the avatar settings. Callers must
        call :py:meth:`save` manually.

        Args:
            value (bool):
                Whether or not avatars are to be enabled.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set(self.AVATARS_ENABLED_KEY, value)
        siteconfig.save()

    def get_siteconfig_defaults(self):
        """Return defaults for the site configuration.

        Returns:
            dict:
            The defaults to register for the site configuration.
        """
        return {
            'avatars_enabled': True,
            'avatars_enabled_services': [
                service.avatar_service_id
                for service in self.default_avatar_service_classes
            ],
            'avatars_default_service': GravatarService.avatar_service_id,
        }

    def migrate_settings(self, siteconfig):
        """Migrate the avatar settings from older databases.

        Prior to Review Board 3.0, only Gravatars were supported, and we
        tracked their enabled state in the ``integration_gravatars`` key.

        Review Board 3.0 introduced modern support for avatar backends, and
        necessitated new settings and a migration path to those settings.  It
        introduced an ``avatars_migrated`` key to determine if we've migrated
        the old avatar settings from a pre-3.0 database. This meant that
        ``avatars_migrated`` had to stick in order to flag the modern avatar
        state, and that we couldn't store the default settings in the
        siteconfig defaults. This led to a migration for every new server, and
        for every unit test.

        Starting in 3.0.4, we've gotten rid of the old ``avatars_migrated``
        key, and instead check the existence of a stored ``avatars_enabled``
        in the siteconfig settings, and stored all defaults on enabled/default
        avatars in the siteconfig defaults. This means that settings are modern
        by default, and that there's less to manage during migration.

        This function will reconcile the old database settings (pre-3.0 and 3.0
        through 3.0.4) with the modern (3.0.4+) settings, removing old settings
        in the process.

        This is meant to be called during initialization before any other
        avatar-dependent code would run.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The site configuration to migrate.

        Returns:
            bool:
            ``True`` if changes to the settings were made.
            ``False`` if no changes were made.
        """
        dirty = False

        # Check if we're upgrading from a Review Board 2.0/2.5 install with
        # Gravatar support disabled. If so, we want to reflect that.
        #
        # If this is a 3.0.x (pre-3.0.4) install, we'll have
        # AVATARS_ENABLED_KEY in siteconfig, so we won't hit this logic. If
        # it's 3.0.4+ we won't have 'integration_gravatars'.
        #
        # If it's a pre-2.0 install (pre-Gravatars), or 2.0/2.5 with Gravatars
        # enabled, we won't save anything (in order to prevent an unnecessary
        # save). Instead, we'll fall back to the siteconfig default of enabled.
        if (self.AVATARS_ENABLED_KEY not in siteconfig.settings and
            siteconfig.get(self.LEGACY_INTEGRATION_GRAVATARS_KEY) is False):
            # We're upgrading from a Review Board 2.0/2.5 database with
            # Gravatars disabled, so store that in order to override the
            # default state.
            siteconfig.set(self.AVATARS_ENABLED_KEY, False)
            dirty = True

        # Clean up any old state in the siteconfig settings that we don't
        # want anymore.
        for legacy_key in (self.LEGACY_AVATARS_MIGRATED_KEY,
                           self.LEGACY_INTEGRATION_GRAVATARS_KEY):
            try:
                del siteconfig.settings[legacy_key]
                dirty = True
            except KeyError:
                pass

        return dirty
