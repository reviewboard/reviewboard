from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from djblets.util.compat.six.moves.urllib.parse import quote as urllib_quote
from djblets.util.http import set_last_modified
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.diffviewer.diffutils import (get_original_file,
                                              get_patched_file)
from reviewboard.diffviewer.models import DiffSet
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.errors import FILE_RETRIEVAL_ERROR
from reviewboard.webapi.resources import resources


class PatchedFileResource(WebAPIResource):
    """Provides the patched file corresponding to a file diff."""
    name = 'patched_file'
    singleton = True
    allowed_mimetypes = [
        {'item': 'text/plain'},
    ]

    @webapi_check_login_required
    @webapi_check_local_site
    def get(self, request, diffset_id=None, *args, **kwargs):
        """Returns the patched file.

        The file is returned as :mimetype:`text/plain` and is the result
        of applying the patch to the original file.
        """
        try:
            attached_diffset = DiffSet.objects.filter(pk=diffset_id,
                                                      history__isnull=True)

            if attached_diffset.exists():
                filediff_resource = resources.filediff
            else:
                filediff_resource = resources.draft_filediff

            filediff = filediff_resource.get_object(
                request, diffset=diffset_id, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if filediff.deleted:
            return DOES_NOT_EXIST

        try:
            orig_file = get_original_file(filediff, request=request)
        except Exception as e:
            logging.error("Error retrieving original file: %s", e, exc_info=1,
                          request=request)
            return FILE_RETRIEVAL_ERROR

        try:
            patched_file = get_patched_file(orig_file, filediff,
                                            request=request)
        except Exception as e:
            logging.error("Error retrieving patched file: %s", e, exc_info=1,
                          request=request)
            return FILE_RETRIEVAL_ERROR

        resp = HttpResponse(patched_file, mimetype='text/plain')
        filename = urllib_quote(filediff.dest_file)
        resp['Content-Disposition'] = 'inline; filename=%s' % filename
        set_last_modified(resp, filediff.diffset.timestamp)

        return resp


patched_file_resource = PatchedFileResource()
