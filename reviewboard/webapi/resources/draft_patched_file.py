from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_patched_file import \
    BasePatchedFileResource


class DraftPatchedFileResource(BasePatchedFileResource):
    """Provides the patched file corresponding to a draft file diff."""
    name = 'draft_patched_file'

    def get_filediff(self, request, *args, **kwargs):
        """Returns the FileDiff, or an error, for the given parameters."""
        draft_resource = resources.review_request_draft

        try:
            draft = draft_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not draft_resource.has_access_permissions(request, draft):
            return self._no_access_error(request.user)

        try:
            return resources.draft_filediff.get_object(request, *args,
                                                       **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST


draft_patched_file_resource = DraftPatchedFileResource()
