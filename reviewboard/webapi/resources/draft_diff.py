from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_login_required

from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.diff import DiffResource


class DraftDiffResource(DiffResource):
    """Provides information on pending draft diffs for a review request.

    This list will only ever contain a maximum of one diff in current
    versions. This is to preserve compatibility with the public
    :ref:`webapi2.0-diff-resource`.

    POSTing to this resource will create or update a review request draft
    with the provided diff. This also mirrors the public diff resource.
    """
    name = 'draft_diff'
    uri_name = 'diffs'
    model_parent_key = 'review_request_draft'
    item_result_key = 'diff'
    list_result_key = 'diffs'
    mimetype_list_resource_name = 'diffs'
    mimetype_item_resource_name = 'diff'

    item_child_resources = [
        resources.draft_filediff,
    ]

    def get_parent_object(self, diffset):
        return diffset.review_request_draft.get()

    def has_access_permissions(self, request, diffset, *args, **kwargs):
        return diffset.review_request_draft.get().is_accessible_by(
            request.user)

    def get_queryset(self, request, *args, **kwargs):
        try:
            draft = resources.review_request_draft.get_object(
                request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise self.model.DoesNotExist

        return self.model.objects.filter(review_request_draft=draft)

    @webapi_login_required
    @augment_method_from(DiffResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of draft diffs on the review request.

        Each diff has the target revision and list of per-file diffs
        associated with it.
        """
        pass


draft_diff_resource = DraftDiffResource()
