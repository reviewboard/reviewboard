from __future__ import unicode_literals

from django.db.models import Manager


class ProfileManager(Manager):
    def get_or_create(self, user, *args, **kwargs):
        if hasattr(user, '_profile'):
            return user._profile, False

        profile, is_new = \
            super(ProfileManager, self).get_or_create(user=user, *args,
                                                      **kwargs)
        user._profile = profile

        return profile, is_new
