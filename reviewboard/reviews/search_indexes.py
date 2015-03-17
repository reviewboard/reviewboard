from __future__ import unicode_literals

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

    def get_model(self):
        """Returns the Django model for this index."""
        return ReviewRequest

    def get_updated_field(self):
        return 'last_updated'

    def index_queryset(self, using=None):
        """Index only public pending and submitted review requests."""
        queryset = self.get_model().objects.public(
            status=None,
            extra_query=Q(status='P') | Q(status='S'),
            show_all_local_sites=True)
        queryset = queryset.select_related('submitter', 'diffset_history')
        queryset = queryset.prefetch_related(
            'diffset_history__diffsets__files')

        return queryset

    def prepare_file(self, obj):
        return set([
            (filediff.source_file, filediff.dest_file)
            for diffset in obj.diffset_history.diffsets.all()
            for filediff in diffset.files.all()
        ])

    def prepare_user_display_name(self, obj):
        return user_displayname(obj.submitter)
