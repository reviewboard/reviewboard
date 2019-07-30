from __future__ import unicode_literals

from django.contrib.auth.models import User
from haystack import indexes

from reviewboard.search.fields import BooleanField
from reviewboard.search.indexes import BaseSearchIndex


class UserIndex(BaseSearchIndex, indexes.Indexable):
    """A Haystack search index for users."""

    model = User
    local_site_attr = 'local_site'

    username = indexes.CharField(model_attr='username')
    email = indexes.CharField()
    full_name = indexes.CharField()
    url = indexes.CharField(model_attr='get_absolute_url')
    groups = indexes.CharField(indexed=False)
    is_profile_private = BooleanField()

    def get_updated_field(self):
        """Return the field indicating when the user was last updated.

        Users don't really have a field for this exactly, but Review Board
        does update the ``last_login`` field when users access the site,
        rather than just when they explicitly log in, so we can tie updates
        to that.

        What this basically means is that we will re-index any active accounts
        (which might have information changed), but if information is changed
        with an older account, it won't be noticed without performing a full
        re-index.

        Returns:
            unicode:
            ``last_login``.
        """
        return 'last_login'

    def index_queryset(self, using=None):
        """Query the list of users for the index.

        All active users will be returned.
        """
        return (
            self.get_model().objects
            .filter(is_active=True)
            .select_related('profile')
            .prefetch_related('review_groups', 'local_site')
        )

    def prepare_groups(self, user):
        """Prepare a user's list of groups for the index.

        Only publicly-accessible groups will be stored in the index.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            unicode:
            The names of publicly-accessible groups.
        """
        return ','.join(
            review_group.name
            for review_group in user.review_groups.all()
            if not review_group.invite_only
        )

    def prepare_email(self, user):
        """Prepare the email field for a user.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            unicode:
            The e-mail address.
        """
        profile = user.get_profile(cached_only=True)

        if profile is None or profile.is_private:
            return ''
        else:
            return user.email

    def prepare_full_name(self, user):
        """Prepare the full_name field for a user.

        This field is not included in the index when their profile is set to
        private.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            unicode:
            The full name of the user or an empty string if their profile is
            private.
        """
        profile = user.get_profile(cached_only=True)

        if profile is None or profile.is_private:
            return ''
        else:
            return user.get_full_name()

    def prepare_is_profile_private(self, user):
        """Prepare the is_profile_private field for a user.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            bool:
            Whther or not the profile is private.
        """
        profile = user.get_profile(cached_only=True)
        return profile is None or profile.is_private
