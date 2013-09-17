from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_login_required

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.filediff import FileDiffResource


class DraftFileDiffResource(FileDiffResource):
    """Provides information on per-file diffs that are part of a draft.

    Each of these contains a single, self-contained diff file that
    applies to exactly one file on a repository.
    """
    name = 'draft_file'
    uri_name = 'files'
    item_result_key = 'file'
    list_result_key = 'files'
    mimetype_list_resource_name = 'files'
    mimetype_item_resource_name = 'file'

    item_child_resources = [
        resources.original_file,
        resources.patched_file,
    ]

    def get_queryset(self, request, diff_revision, *args, **kwargs):
        draft = resources.review_request_draft.get_object(
            request, *args, **kwargs)

        return self.model.objects.filter(
            diffset__review_request_draft=draft,
            diffset__revision=diff_revision)

    def has_access_permissions(self, request, filediff, *args, **kwargs):
        return filediff.diffset.review_request_draft.get().is_accessible_by(
            request.user)

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(FileDiffResource)
    def get(self, *args, **kwargs):
        pass

    @webapi_check_local_site
    @webapi_login_required
    @augment_method_from(FileDiffResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of draft per-file diffs on the review request.

        Each per-file diff has information about the diff. It does not
        provide the contents of the diff. For that, access the per-file diff's
        resource directly and use the correct mimetype.
        """
        pass


draft_filediff_resource = DraftFileDiffResource()
