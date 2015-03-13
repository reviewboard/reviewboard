from __future__ import unicode_literals

from django.contrib.auth.models import User
from haystack import indexes


class UserIndex(indexes.SearchIndex, indexes.Indexable):
    """A Haystack search index for users."""

    # By Haystack convention, the full-text template is automatically
    # referenced at
    # reviewboard/templates/search/indexes/accounts/user_text.txt
    text = indexes.CharField(document=True, use_template=True)

    username = indexes.CharField(model_attr='username')
    email = indexes.CharField(model_attr='email')
    full_name = indexes.CharField(model_attr='get_full_name')
    url = indexes.CharField(model_attr='get_absolute_url')
    show_profile = indexes.BooleanField(model_attr='is_profile_visible')
    groups = indexes.MultiValueField(indexed=False)

    def get_model(self):
        """Return the Django model for this index."""
        return User

    def index_queryset(self, using=None):
        """Query the list of users for the index.

        All active users will be returned.
        """
        return self.get_model().objects.filter(is_active=True)

    def prepare_groups(self, user):
        """Prepare a user's list of groups for the index.

        Only publicly-accessible groups will be stored in the index.
        """
        return [
            group.name
            for group in user.review_groups.filter(invite_only=False)
        ]
