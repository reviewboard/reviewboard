from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from djblets.util.templatetags.djblets_utils import user_displayname
from haystack import indexes

from reviewboard.reviews.models import ReviewRequest
from reviewboard.search.indexes import BaseSearchIndex


class ReviewRequestIndex(BaseSearchIndex, indexes.Indexable):
    """A Haystack search index for Review Requests."""
    model = ReviewRequest
    local_site_attr = 'local_site_id'

    # We shouldn't use 'id' as a field name because it's by default reserved
    # for Haystack. Hiding it will cause duplicates when updating the index.
    review_request_id = indexes.IntegerField(model_attr='display_id')
    summary = indexes.CharField(model_attr='summary')
    description = indexes.CharField(model_attr='description')
    testing_done = indexes.CharField(model_attr='testing_done')
    bug = indexes.CharField(model_attr='bugs_closed')
    username = indexes.CharField(model_attr='submitter__username')
    user_display_name = indexes.CharField()
    author = indexes.CharField(model_attr='submitter__get_full_name')
    last_updated = indexes.DateTimeField(model_attr='last_updated')
    url = indexes.CharField(model_attr='get_absolute_url')
    file = indexes.CharField()

    # These fields all contain information needed to perform queries about
    # whether a review request is accessible by a given user.
    private = indexes.BooleanField()
    private_repository_id = indexes.IntegerField()
    private_target_groups = indexes.MultiValueField()
    target_users = indexes.MultiValueField()

    def get_model(self):
        """Returns the Django model for this index."""
        return ReviewRequest

    def get_updated_field(self):
        return 'last_updated'

    def index_queryset(self, using=None):
        """Index only public pending and submitted review requests."""
        return (
            self.get_model().objects
            .public(status=None,
                    extra_query=Q(status='P') | Q(status='S'),
                    show_all_local_sites=True,
                    filter_private=False)
            .select_related('diffset_history',
                            'local_site',
                            'repository',
                            'submitter')
            .prefetch_related('diffset_history__diffsets__files',
                              'target_groups',
                              'target_people')
        )

    def prepare_file(self, obj):
        return set([
            (filediff.source_file, filediff.dest_file)
            for diffset in obj.diffset_history.diffsets.all()
            for filediff in diffset.files.all()
        ])

    def prepare_private(self, review_request):
        """Prepare the private flag for the index.

        This will be set to true if the review request isn't generally
        accessible to users.
        """
        return not review_request.is_accessible_by(AnonymousUser(),
                                                   silent=True)

    def prepare_private_repository_id(self, review_request):
        """Prepare the private repository ID, if any, for the index.

        If there's no repository, or it's public, 0 will be returned instead.
        """
        if review_request.repository and not review_request.repository.public:
            return review_request.repository_id
        else:
            return 0

    def prepare_private_target_groups(self, review_request):
        """Prepare the list of invite-only target groups for the index.

        If there aren't any invite-only groups associated, ``[0]`` will be
        returned. This allows queries to be performed that check that none
        of the groups are private, since we can't query against empty lists.
        """
        return [
            group.pk
            for group in review_request.target_groups.all()
            if group.invite_only
        ] or [0]

    def prepare_target_users(self, review_request):
        """Prepare the list of target users for the index.

        If there aren't any target users, ``[0]`` will be returned. This
        allows queries to be performed that check that there aren't any
        users in the list, since we can't query against empty lists.
        """
        return [
            user.pk
            for user in review_request.target_people.all()
        ] or [0]

    def prepare_user_display_name(self, obj):
        return user_displayname(obj.submitter)
