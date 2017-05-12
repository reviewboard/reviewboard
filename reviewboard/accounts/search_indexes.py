from __future__ import unicode_literals

from django.contrib.auth.models import User
from haystack import indexes

from reviewboard.search.indexes import BaseSearchIndex


class UserIndex(BaseSearchIndex, indexes.Indexable):
    """A Haystack search index for users."""

    model = User
    local_site_attr = 'local_site'

    username = indexes.CharField(model_attr='username')
    email = indexes.CharField(model_attr='email')
    full_name = indexes.CharField(model_attr='get_full_name')
    url = indexes.CharField(model_attr='get_absolute_url')
    show_profile = indexes.BooleanField(model_attr='is_profile_visible')
    groups = indexes.CharField(indexed=False)

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
        """
        return ','.join(
            review_group.name
            for review_group in user.review_groups.all()
            if not review_group.invite_only
        )
