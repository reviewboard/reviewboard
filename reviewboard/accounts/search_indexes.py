"""Search indexing for accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.db.models import Prefetch
from haystack import indexes

from reviewboard.reviews.models.group import Group
from reviewboard.search.fields import BooleanField
from reviewboard.search.indexes import BaseSearchIndex
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from reviewboard.accounts.models import User as RBUser


class UserIndex(BaseSearchIndex[User], indexes.Indexable):
    """A Haystack search index for users."""

    model = User
    local_site_attr = 'local_site'

    username = indexes.CharField(model_attr='username')
    email = indexes.CharField()
    full_name = indexes.CharField()
    url = indexes.CharField(model_attr='get_absolute_url')
    groups = indexes.CharField(indexed=False)
    is_profile_private = BooleanField()

    def get_updated_field(self) -> str:
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
            str:
            ``last_login``.
        """
        return 'last_login'

    def index_queryset(
        self,
        using: (str | None) = None,
    ) -> QuerySet[User]:
        """Return a queryset for indexing users.

        Args:
            using (str, unused):
                The name of the search index.

        Returns:
            django.db.models.QuerySet:
            The queryset to index.
        """
        queryset: QuerySet[User] = (
            self.get_model().objects
            .filter(is_active=True)
            .only(
                # User fields.
                'email',
                'first_name',
                'last_name',
                'username',

                # Profile fields.
                'profile__extra_data',
                'profile__is_private',
            )
            .select_related(
                'profile',
            )
            .prefetch_related(
                Prefetch(
                    'review_groups',
                    queryset=(
                        Group.objects
                        .only(
                            'invite_only',
                            'name',
                        )
                    ),
                ),
            )
        )

        if LocalSite.objects.has_local_sites():
            # If the server has Local Sites, prefetch them for all users.
            #
            # If a Local Site is added for the first time while indexing,
            # this will result in an N+1 query issue for every user, which
            # will be expensive. This would only ever happen once, and
            # should be an unlikely event.
            queryset = queryset.prefetch_related(
                Prefetch(
                    'local_site',
                    queryset=(
                        LocalSite.objects
                        .only(
                            'name',
                        )
                    ),
                ),
            )

        return queryset

    def prepare_groups(
        self,
        user: RBUser,
    ) -> str:
        """Prepare a user's list of groups for the index.

        Only publicly-accessible groups will be stored in the index.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            str:
            The names of publicly-accessible groups.
        """
        return ','.join(
            review_group.name
            for review_group in user.review_groups.all()
            if not review_group.invite_only
        )

    def prepare_email(
        self,
        user: RBUser,
    ) -> str:
        """Prepare the email field for a user.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            str:
            The e-mail address.
        """
        if user.has_private_profile():
            return ''
        else:
            return user.email

    def prepare_full_name(
        self,
        user: RBUser,
    ) -> str:
        """Prepare the full_name field for a user.

        This field is not included in the index when their profile is set to
        private.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            str:
            The full name of the user or an empty string if their profile is
            private.
        """
        if user.has_private_profile():
            return ''
        else:
            return user.get_full_name()

    def prepare_is_profile_private(
        self,
        user: RBUser,
    ) -> bool:
        """Prepare the is_profile_private field for a user.

        Args:
            user (django.contrib.auth.models.User):
                The user being indexed.

        Returns:
            bool:
            Whether or not the profile is private.
        """
        return user.has_private_profile()
