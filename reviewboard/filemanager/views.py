import logging
import time
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, \
                        HttpResponseNotModified, HttpResponseServerError, \
                        HttpResponseForbidden
from django.shortcuts import get_object_or_404, get_list_or_404, \
                             render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.generic.list_detail import object_list

from djblets.auth.util import login_required
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.dates import get_latest_timestamp
from djblets.util.http import set_last_modified, get_modified_since, \
                              set_etag, etag_if_none_match
from djblets.util.misc import get_object_or_none

from reviewboard.accounts.decorators import check_login_required, \
                                            valid_prefs_required
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.diffutils import get_file_chunks_in_range
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import view_diff, view_diff_fragment, \
                                         exception_traceback_string
from reviewboard.filemanager.models import UploadedFile
from reviewboard.reviews.errors import OwnershipError
from reviewboard.filemanager.forms import CommentFileForm
from reviewboard.reviews.views import find_review_request
from reviewboard.reviews.models import Comment, ReviewRequest, \
                                       ReviewRequestDraft, Review, Group, \
                                       UploadedFileComment
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import SCMError
from reviewboard.site.models import LocalSite

@login_required
def delete_file(request,
                      review_request_id,
                      file_id,
                      local_site_name=None):
    """
    Deletes a file from a review request and redirects back to the
    review request page.
    """
    review_request, response = \
        find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    s = UploadedFile.objects.get(id=file_id)

    draft = ReviewRequestDraft.create(review_request)
    draft.files.remove(s)
    draft.inactive_files.add(s)
    draft.save()

    return HttpResponseRedirect(review_request.get_absolute_url())


