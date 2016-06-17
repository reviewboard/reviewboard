from __future__ import unicode_literals

from reviewboard.avatars.registry import AvatarServiceRegistry
from reviewboard.signals import initializing


#: The avatar services registry.
avatar_services = AvatarServiceRegistry()


def _enable_avatar_form(**kwargs):
    from reviewboard.accounts.forms.pages import AvatarSettingsForm
    from reviewboard.accounts.pages import AccountPage, ProfilePage

    if avatar_services.avatars_enabled:
        AccountPage.registry.add_form_to_page(ProfilePage, AvatarSettingsForm)


initializing.connect(_enable_avatar_form)
