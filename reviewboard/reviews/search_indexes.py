from django.db.models import Q
from haystack import indexes

from reviewboard.reviews.models import ReviewRequest


class ReviewRequestIndex(indexes.SearchIndex, indexes.Indexable):
    """A Haystack search index for Review Requests."""
    # By Haystack convention, the full-text template is automatically
    # referenced at
    # reviewboard/templates/search/indexes/reviews/reviewrequest_text.txt
    text = indexes.CharField(document=True, use_template=True)

    # We shouldn't use 'id' as a field name because it's by default reserved
    # for Haystack. Hiding it will cause duplicates when updating the index.
    review_request_id = indexes.IntegerField(model_attr='id')
    summary = indexes.CharField(model_attr='summary')
    description = indexes.CharField(model_attr='description')
    testing_done = indexes.CharField(model_attr='testing_done')
    bug = indexes.CharField(model_attr='bugs_closed')
    username = indexes.CharField(model_attr='submitter__username')
    author = indexes.CharField(model_attr='submitter__get_full_name')
    file = indexes.CharField(model_attr='get_all_diff_filenames')

    def get_model(self):
        """Returns the Django model for this index."""
        return ReviewRequest

    def index_queryset(self, using=None):
        """Index only public pending and submitted review requests."""
        return self.get_model().objects.public(
            status=None,
            extra_query=Q(status='P') | Q(status='S'))
