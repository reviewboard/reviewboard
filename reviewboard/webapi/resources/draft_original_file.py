from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_original_file import \
    BaseOriginalFileResource


class DraftOriginalFileResource(BaseOriginalFileResource):
    """Provides the unpatched file corresponding to a file diff."""
    added_in = '2.0.4'

    name = 'draft_original_file'

    def get_filediff(self, request, *args, **kwargs):
        """Returns the FileDiff, or an error, for the given parameters."""
        draft_resource = resources.review_request_draft

        try:
            draft = draft_resource.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not draft_resource.has_access_permissions(request, draft):
            return self.get_no_access_error(request)

        try:
            return resources.draft_filediff.get_object(request, *args,
                                                       **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST


draft_original_file_resource = DraftOriginalFileResource()
