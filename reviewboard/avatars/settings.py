from __future__ import unicode_literals

from djblets.avatars.settings import AvatarSettingsManager


class UserProfileAvatarSettingsManager(AvatarSettingsManager):
    """A mixin that provides avatar service configuration from profiles."""

    AVATAR_SETTINGS_KEY = 'avatars'
    AVATAR_SETTINGS_SERVICE_ID_KEY = 'avatar_service_id'
    AVATAR_SETTINGS_CONFIGURATION_KEY = 'configuration'

    def __init__(self, user):
        super(UserProfileAvatarSettingsManager, self).__init__(user)

        self.profile = user.get_profile()
        self.profile.settings = self.profile.settings or {}
        self.avatar_settings = self.profile.settings.setdefault(
            self.AVATAR_SETTINGS_KEY, {})

    @property
    def avatar_service_id(self):
        """Return service ID for the user's selected avatar service.

        Returns:
            unicode:
            The avatar service ID for the user's selected avatar service, or
            ``None`` if they have not selected one.
        """
        return self.avatar_settings.get(self.AVATAR_SETTINGS_SERVICE_ID_KEY)

    @avatar_service_id.setter
    def avatar_service_id(self, avatar_service_id):
        """Set the avatar service ID for the user.

        Args:
            avatar_service_id (unicode):
                The ID of the :py:class:`avatar service
                <djblets.avatars.services.base.AvatarService>` to set.
        """
        self.avatar_settings[self.AVATAR_SETTINGS_SERVICE_ID_KEY] = \
            avatar_service_id

    @property
    def configuration(self):
        """The user's configuration for all avatar services.

        Returns:
            dict:
            The user's configuration for the avatar service.
        """
        return self.avatar_settings.setdefault(
            self.AVATAR_SETTINGS_CONFIGURATION_KEY, {})

    @configuration.setter
    def configuration(self, settings):
        """Save the user's configuration for all avatar services.

        Args:
            settings (dict):
                The configuration to save.
        """
        self.avatar_settings[self.AVATAR_SETTINGS_CONFIGURATION_KEY] = settings

    def configuration_for(self, avatar_service_id):
        """The user's configuration for the given avatar service.

        Args:
            avatar_service_id (unicode):
                The ID of the :py:class:`avatar service
                <djblets.avatars.service.base.AvatarService>` to get the
                configuration for.
        Returns:
            dict:
            The configuration dictionary for the requested avatar service. It
            will be created if it does not already exist.
        """
        return self.configuration.setdefault(avatar_service_id, {})

    def save(self):
        """Save the user's settings to their profile"""
        self.profile.save(update_fields=('settings',))
