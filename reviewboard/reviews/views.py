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

from reviewboard.accounts.decorators import check_login_required
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.diffutils import get_file_chunks_in_range
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import view_diff, view_diff_fragment, \
                                         exception_traceback_string
from reviewboard.reviews.datagrids import DashboardDataGrid, \
                                          GroupDataGrid, \
                                          ReviewRequestDataGrid, \
                                          SubmitterDataGrid, \
                                          WatchedGroupDataGrid
from reviewboard.reviews.errors import OwnershipError
from reviewboard.reviews.forms import NewReviewRequestForm, \
                                      UploadDiffForm, \
                                      UploadScreenshotForm
from reviewboard.reviews.models import Comment, ReviewRequest, \
                                       ReviewRequestDraft, Review, Group, \
                                       Screenshot, ScreenshotComment
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.errors import SCMError
from reviewboard.site.models import LocalSite


#####
##### Helper functions
#####


def _render_permission_denied(
    request,
    template_name='reviews/review_request_permission_denied.html'):
    """Renders a Permission Denied error for this review request."""

    response = render_to_response(template_name, RequestContext(request))
    response.status_code = 403
    return response


def _find_review_request(request, review_request_id, local_site_name):
    """
    Find a review request based on an ID and optional LocalSite name.

    If a local site is passed in on the URL, we want to look up the review
    request using the local_id instead of the pk. This allows each LocalSite
    configured to have its own review request ID namespace starting from 1.

    Returns either (None, response) or (ReviewRequest, None).
    """
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        review_request = get_object_or_404(ReviewRequest,
                                           local_site=local_site,
                                           local_id=review_request_id)
    else:
        review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if review_request.is_accessible_by(request.user):
        return review_request, None
    else:
        return None, _render_permission_denied(request)


def _make_review_request_context(review_request, extra_context):
    """Returns a dictionary for template contexts used for review requests.

    The dictionary will contain the common data that is used for all
    review request-related pages (the review request detail page, the diff
    viewer, and the screenshot pages).

    For convenience, extra data can be passed to this dictionary.
    """
    if review_request.repository:
        upload_diff_form = UploadDiffForm(review_request)
        scmtool = review_request.repository.get_scmtool()
    else:
        upload_diff_form = None
        scmtool = None

    return dict({
        'review_request': review_request,
        'upload_diff_form': upload_diff_form,
        'upload_screenshot_form': UploadScreenshotForm(),
        'scmtool': scmtool,
    }, **extra_context)


def _query_for_diff(review_request, user, revision, query_extra=None):
    """
    Queries for a diff based on several parameters.

    If the draft does not exist, this throws an Http404 exception.
    """
    # Normalize the revision, since it might come in as a string.
    if revision:
        revision = int(revision)

    # This will try to grab the diff associated with a draft if the review
    # request has an associated draft and is either the revision being
    # requested or no revision is being requested.
    draft = review_request.get_draft(user)
    if draft and draft.diffset and \
       (revision is None or draft.diffset.revision == revision):
        return draft.diffset

    query = Q(history=review_request.diffset_history)

    # Grab a revision if requested.
    if revision is not None:
        query = query & Q(revision=revision)

    # Anything else the caller wants.
    if query_extra:
        query = query & query_extra

    try:
        results = DiffSet.objects.filter(query).latest()
        return results
    except DiffSet.DoesNotExist:
        raise Http404


def build_diff_comment_fragments(
    comments, context,
    comment_template_name='reviews/diff_comment_fragment.html',
    error_template_name='diffviewer/diff_fragment_error.html'):

    comment_entries = []
    had_error = False
    siteconfig = SiteConfiguration.objects.get_current()

    for comment in comments:
        try:
            content = render_to_string(comment_template_name, {
                'comment': comment,
                'chunks': list(get_file_chunks_in_range(context,
                                                        comment.filediff,
                                                        comment.interfilediff,
                                                        comment.first_line,
                                                        comment.num_lines)),
                'domain': Site.objects.get_current().domain,
                'domain_method': siteconfig.get("site_domain_method"),
            })
        except Exception, e:
            content = exception_traceback_string(None, e,
                                                 error_template_name, {
                'comment': comment,
                'file': {
                    'depot_filename': comment.filediff.source_file,
                    'index': None,
                    'filediff': comment.filediff,
                },
                'domain': Site.objects.get_current().domain,
                'domain_method': siteconfig.get("site_domain_method"),
            })

            # It's bad that we failed, and we'll return a 500, but we'll
            # still return content for anything we have. This will prevent any
            # caching.
            had_error = True

        comment_entries.append({
            'comment': comment,
            'html': content,
        })

    return had_error, comment_entries


fields_changed_name_map = {
    'summary': 'Summary',
    'description': 'Description',
    'testing_done': 'Testing Done',
    'bugs_closed': 'Bugs Closed',
    'branch': 'Branch',
    'target_groups': 'Reviewers (Groups)',
    'target_people': 'Reviewers (People)',
    'screenshots': 'Screenshots',
    'screenshot_captions': 'Screenshot Captions',
    'diff': 'Diff',
}


#####
##### View functions
#####

@login_required
def new_review_request(request,
                       local_site_name=None,
                       template_name='reviews/new_review_request.html'):
    """
    Displays a New Review Request form and handles the creation of a
    review request based on either an existing changeset or the provided
    information.
    """
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)

        if (request.user.is_anonymous() or
            not local_site.users.filter(pk=request.user.pk).exists()):
            return _render_permission_denied(requset)
    else:
        local_site = None

    if request.method == 'POST':
        form = NewReviewRequestForm(request.user, local_site,
                                    request.POST, request.FILES)

        if form.is_valid():
            try:
                review_request = form.create(
                    user=request.user,
                    diff_file=request.FILES.get('diff_path'),
                    parent_diff_file=request.FILES.get('parent_diff_path'),
                    local_site=local_site)
                return HttpResponseRedirect(review_request.get_absolute_url())
            except (OwnershipError, SCMError, ValueError):
                pass
    else:
        form = NewReviewRequestForm(request.user, local_site)

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'fields': simplejson.dumps(form.field_mapping),
    }))


@check_login_required
def review_detail(request,
                  review_request_id,
                  local_site_name=None,
                  template_name="reviews/review_detail.html"):
    """
    Main view for review requests. This covers the review request information
    and all the reviews on it.
    """
    # If there's a local_site passed in the URL, we want to look up the review
    # request based on the local_id instead of the pk. This allows each
    # local_site configured to have its own review request ID namespace
    # starting from 1.
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    reviews = review_request.get_public_reviews()
    review = review_request.get_pending_review(request.user)
    review_timestamp = 0
    last_visited = 0
    starred = False

    if request.user.is_authenticated():
        # If the review request is public and pending review and if the user
        # is logged in, mark that they've visited this review request.
        if review_request.public and review_request.status == "P":
            visited, visited_is_new = ReviewRequestVisit.objects.get_or_create(
                user=request.user, review_request=review_request)
            last_visited = visited.timestamp
            visited.timestamp = datetime.now()
            visited.save()

        starred = review_request in \
                  request.user.get_profile().starred_review_requests.all()

        # Unlike review above, this covers replies as well.
        try:
            last_draft_review = Review.objects.filter(
                review_request=review_request,
                user=request.user,
                public=False).latest()
            review_timestamp = last_draft_review.timestamp
        except Review.DoesNotExist:
            pass


    draft = review_request.get_draft(request.user)

    # Find out if we can bail early. Generate an ETag for this.
    last_activity_time, updated_object = review_request.get_last_activity()

    if draft:
        draft_timestamp = draft.last_updated
    else:
        draft_timestamp = ""

    etag = "%s:%s:%s:%s:%s:%s" % (request.user, last_activity_time,
                                  draft_timestamp, review_timestamp,
                                  int(starred),
                                  settings.AJAX_SERIAL)

    if etag_if_none_match(request, etag):
        return HttpResponseNotModified()

    changedescs = review_request.changedescs.filter(public=True)

    try:
        latest_changedesc = changedescs.latest('timestamp')
        latest_timestamp = latest_changedesc.timestamp
    except ChangeDescription.DoesNotExist:
        latest_timestamp = None

    entries = []

    for temp_review in reviews:
        temp_review.ordered_comments = \
            temp_review.comments.order_by('filediff', 'first_line')

        state = ''

        # Mark as collapsed if the review is older than the latest change
        if latest_timestamp and temp_review.timestamp < latest_timestamp:
            state = 'collapsed'

        try:
            latest_reply = temp_review.public_replies().latest('timestamp').timestamp
        except Review.DoesNotExist:
            latest_reply = None

        # Mark as expanded if there is a reply newer than last_visited
        if latest_reply and last_visited and last_visited < latest_reply:
          state = ''

        entries.append({
            'review': temp_review,
            'timestamp': temp_review.timestamp,
            'class': state,
        })

    for changedesc in changedescs:
        fields_changed = []

        for name, info in changedesc.fields_changed.items():
            multiline = False

            if 'added' in info or 'removed' in info:
                change_type = 'add_remove'

                # We don't hard-code URLs in the bug info, since the
                # tracker may move, but we can do it here.
                if (name == "bugs_closed" and
                    review_request.repository.bug_tracker):
                    bug_url = review_request.repository.bug_tracker
                    for field in info:
                        for i, buginfo in enumerate(info[field]):
                            try:
                                full_bug_url = bug_url % buginfo[0]
                                info[field][i] = (buginfo[0], full_bug_url)
                            except TypeError:
                                logging.warning("Invalid bugtracker url format")

            elif 'old' in info or 'new' in info:
                change_type = 'changed'
                multiline = (name == "description" or name == "testing_done")

                # Branch text is allowed to have entities, so mark it safe.
                if name == "branch":
                    if 'old' in info:
                        info['old'][0] = mark_safe(info['old'][0])

                    if 'new' in info:
                        info['new'][0] = mark_safe(info['new'][0])
            elif name == "screenshot_captions":
                change_type = 'screenshot_captions'
            else:
                # No clue what this is. Bail.
                continue

            fields_changed.append({
                'title': fields_changed_name_map.get(name, name),
                'multiline': multiline,
                'info': info,
                'type': change_type,
            })

        # Expand the latest review change
        state = ''

        # Mark as collapsed if the change is older than a newer change
        if latest_timestamp and changedesc.timestamp < latest_timestamp:
            state = 'collapsed'

        entries.append({
            'changeinfo': fields_changed,
            'changedesc': changedesc,
            'timestamp': changedesc.timestamp,
            'class': state,
        })

    entries.sort(key=lambda item: item['timestamp'])

    response = render_to_response(
        template_name,
        RequestContext(request, _make_review_request_context(review_request, {
            'draft': draft,
            'review_request_details': draft or review_request,
            'entries': entries,
            'last_activity_time': last_activity_time,
            'review': review,
            'request': request,
            'PRE_CREATION': PRE_CREATION,
        })))
    set_etag(response, etag)

    return response


@login_required
@cache_control(no_cache=True, no_store=True, max_age=0, must_revalidate=True)
def review_draft_inline_form(request,
                             review_request_id,
                             template_name,
                             local_site_name=None):
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    review = review_request.get_pending_review(request.user)

    # This may be a brand new review. If so, we don't have a review object.
    if review:
        review.ordered_comments = \
            review.comments.order_by('filediff', 'first_line')

    return render_to_response(template_name, RequestContext(request, {
        'review_request': review_request,
        'review': review,
        'PRE_CREATION': PRE_CREATION,
    }))


@check_login_required
def all_review_requests(request,
                        local_site_name=None,
                        template_name='reviews/datagrid.html'):
    """
    Displays a list of all review requests.
    """
    local_site = get_object_or_none(LocalSite, name=local_site_name)
    if local_site_name and not local_site:
        raise Http404
    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.public(request.user,
                                     status=None,
                                     local_site=local_site,
                                     with_counts=True),
        _("All review requests"),
        local_site=local_site)
    return datagrid.render_to_response(template_name)


@check_login_required
def submitter_list(request,
                   local_site_name=None,
                   template_name='reviews/datagrid.html'):
    """
    Displays a list of all users.
    """
    grid = SubmitterDataGrid(
        request, local_site=get_object_or_none(LocalSite, name=local_site_name))
    return grid.render_to_response(template_name)


@check_login_required
def group_list(request,
               local_site_name=None,
               template_name='reviews/datagrid.html'):
    """
    Displays a list of all review groups.
    """
    grid = GroupDataGrid(
        request, local_site=get_object_or_none(LocalSite, name=local_site_name))
    return grid.render_to_response(template_name)


@login_required
def dashboard(request,
              template_name='reviews/dashboard.html',
              local_site_name=None):
    """
    The dashboard view, showing review requests organized by a variety of
    lists, depending on the 'view' parameter.

    Valid 'view' parameters are:

        * 'outgoing'
        * 'to-me'
        * 'to-group'
        * 'starred'
        * 'watched-groups'
        * 'incoming'
        * 'mine'
    """
    view = request.GET.get('view', None)

    local_site = get_object_or_none(LocalSite, name=local_site_name)

    if view == "watched-groups":
        # This is special. We want to return a list of groups, not
        # review requests.
        grid = WatchedGroupDataGrid(request, local_site=local_site)
    else:
        grid = DashboardDataGrid(request, local_site=local_site)

    return grid.render_to_response(template_name)


@check_login_required
def group(request,
          name,
          template_name='reviews/datagrid.html',
          local_site_name=None):
    """
    A list of review requests belonging to a particular group.
    """
    # Make sure the group exists
    local_site = get_object_or_none(LocalSite, name=local_site_name)
    group = get_object_or_404(Group, name=name, local_site=local_site)

    if not group.is_accessible_by(request.user):
        return _render_permission_denied(
            request, 'reviews/group_permission_denied.html')

    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.to_group(name, local_site, status=None,
                                       with_counts=True),
        _("Review requests for %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
def group_members(request,
                  name,
                  template_name='reviews/datagrid.html',
                  local_site_name=None):
    """
    A list of users registered for a particular group.
    """
    # Make sure the group exists
    group = get_object_or_404(Group,
                              name=name,
                              local_site__name=local_site_name)

    if not group.is_accessible_by(request.user):
        return _render_permission_denied(
            request, 'reviews/group_permission_denied.html')

    datagrid = SubmitterDataGrid(request,
                                 group.users.filter(is_active=True),
                                 _("Members of group %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
def submitter(request,
              username,
              template_name='reviews/datagrid.html',
              local_site_name=None):
    """
    A list of review requests owned by a particular user.
    """
    local_site = get_object_or_none(LocalSite, name=local_site_name)
    if local_site_name and not local_site:
        raise Http404

    # Make sure the user exists
    if local_site:
        if not local_site.users.filter(username=username).exists():
            raise Http404
    else:
        get_object_or_404(User, username=username)

    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.from_user(username, status=None,
                                        with_counts=True,
                                        local_site=local_site),
        _("%s's review requests") % username,
        local_site=local_site)

    return datagrid.render_to_response(template_name)


@check_login_required
def diff(request,
         review_request_id,
         revision=None,
         interdiff_revision=None,
         local_site_name=None,
         template_name='diffviewer/view_diff.html'):
    """
    A wrapper around diffviewer.views.view_diff that handles querying for
    diffs owned by a review request,taking into account interdiffs and
    providing the user's current review of the diff if it exists.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    diffset = _query_for_diff(review_request, request.user, revision)

    interdiffset = None
    review = None
    draft = None

    if interdiff_revision and interdiff_revision != revision:
        # An interdiff revision was specified. Try to find a matching
        # diffset.
        interdiffset = _query_for_diff(review_request, request.user,
                                       interdiff_revision)

    # Try to find an existing pending review of this diff from the
    # current user.
    review = review_request.get_pending_review(request.user)
    draft = review_request.get_draft(request.user)

    has_draft_diff = draft and draft.diffset
    is_draft_diff = has_draft_diff and draft.diffset == diffset
    is_draft_interdiff = has_draft_diff and interdiffset and \
                         draft.diffset == interdiffset

    num_diffs = review_request.diffset_history.diffsets.count()
    if draft and draft.diffset:
        num_diffs += 1

    last_activity_time, updated_object = review_request.get_last_activity()

    return view_diff(
         request, diffset, interdiffset, template_name=template_name,
         extra_context=_make_review_request_context(review_request, {
            'review': review,
            'review_request_details': draft or review_request,
            'draft': draft,
            'is_draft_diff': is_draft_diff,
            'is_draft_interdiff': is_draft_interdiff,
            'num_diffs': num_diffs,
            'last_activity_time': last_activity_time,
            'specific_diff_requested': revision is not None or
                                       interdiff_revision is not None,
            'base_url': review_request.get_absolute_url(),
        }))


@check_login_required
def raw_diff(request,
             review_request_id,
             revision=None,
             local_site_name=None):
    """
    Displays a raw diff of all the filediffs in a diffset for the
    given review request.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    diffset = _query_for_diff(review_request, request.user, revision)

    tool = review_request.repository.get_scmtool()
    data = tool.get_parser('').raw_diff(diffset)

    resp = HttpResponse(data, mimetype='text/x-patch')

    if diffset.name == 'diff':
        filename = "bug%s.patch" % review_request.bugs_closed.replace(',', '_')
    else:
        filename = diffset.name

    resp['Content-Disposition'] = 'inline; filename=%s' % filename
    set_last_modified(resp, diffset.timestamp)

    return resp


@check_login_required
def comment_diff_fragments(
    request,
    review_request_id,
    comment_ids,
    template_name='reviews/load_diff_comment_fragments.js',
    comment_template_name='reviews/diff_comment_fragment.html',
    error_template_name='diffviewer/diff_fragment_error.html',
    local_site_name=None):
    """
    Returns the fragment representing the parts of a diff referenced by the
    specified list of comment IDs. This is used to allow batch lazy-loading
    of these diff fragments based on filediffs, since they may not be cached
    and take time to generate.
    """
    # While we don't actually need the review request, we still want to do this
    # lookup in order to get the permissions checking.
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    comments = get_list_or_404(Comment, pk__in=comment_ids.split(","))
    latest_timestamp = get_latest_timestamp([comment.timestamp
                                             for comment in comments])

    if get_modified_since(request, latest_timestamp):
        return HttpResponseNotModified()

    context = RequestContext(request, {
        'comment_entries': [],
        'container_prefix': request.GET.get('container_prefix'),
        'queue_name': request.GET.get('queue'),
    })

    had_error, context['comment_entries'] = \
        build_diff_comment_fragments(comments,
                                     context,
                                     comment_template_name,
                                     error_template_name)

    page_content = render_to_string(template_name, context)

    if had_error:
        return HttpResponseServerError(page_content)

    response = HttpResponse(page_content)
    set_last_modified(response, comment.timestamp)
    response['Expires'] = http_date(time.time() + 60 * 60 * 24 * 365) # 1 year
    return response


@check_login_required
def diff_fragment(request,
                  review_request_id,
                  revision,
                  filediff_id,
                  interdiff_revision=None,
                  chunkindex=None,
                  template_name='diffviewer/diff_file_fragment.html',
                  local_site_name=None):
    """
    Wrapper around diffviewer.views.view_diff_fragment that takes a review
    request.

    Displays just a fragment of a diff or interdiff owned by the given
    review request. The fragment is identified by the chunk index in the
    diff.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    review_request.get_draft(request.user)

    if interdiff_revision is not None:
        interdiffset = _query_for_diff(review_request, request.user,
                                       interdiff_revision)
        interdiffset_id = interdiffset.id
    else:
        interdiffset_id = None

    diffset = _query_for_diff(review_request, request.user, revision)

    return view_diff_fragment(request, diffset.id, filediff_id,
                              review_request.get_absolute_url(),
                              interdiffset_id, chunkindex, template_name)


@check_login_required
def preview_review_request_email(
    request,
    review_request_id,
    format,
    text_template_name='notifications/review_request_email.txt',
    html_template_name='notifications/review_request_email.html',
    local_site_name=None):
    """
    Previews the e-mail message that would be sent for an initial
    review request or an update.

    This is mainly used for debugging.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    siteconfig = SiteConfiguration.objects.get_current()

    if format == 'text':
        template_name = text_template_name
        mimetype = 'text/plain'
    elif format == 'html':
        template_name = html_template_name
        mimetype = 'text/html'
    else:
        raise Http404

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'user': request.user,
            'domain': Site.objects.get_current().domain,
            'domain_method': siteconfig.get("site_domain_method"),
        }),
    ), mimetype=mimetype)


@check_login_required
def preview_review_email(request, review_request_id, review_id, format,
                         text_template_name='notifications/review_email.txt',
                         html_template_name='notifications/review_email.html',
                         extra_context={},
                         local_site_name=None):
    """
    Previews the e-mail message that would be sent for a review of a
    review request.

    This is mainly used for debugging.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)
    siteconfig = SiteConfiguration.objects.get_current()

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    if format == 'text':
        template_name = text_template_name
        mimetype = 'text/plain'
    elif format == 'html':
        template_name = html_template_name
        mimetype = 'text/html'
    else:
        raise Http404

    context = {
        'review_request': review_request,
        'review': review,
        'user': request.user,
        'domain': Site.objects.get_current().domain,
        'domain_method': siteconfig.get("site_domain_method"),
    }
    context.update(extra_context)

    has_error, context['comment_entries'] = \
        build_diff_comment_fragments(
            review.ordered_comments, context,
            "notifications/email_diff_comment_fragment.html")

    return HttpResponse(
        render_to_string(template_name, RequestContext(request, context)),
        mimetype=mimetype)


@check_login_required
def preview_reply_email(request, review_request_id, review_id, reply_id,
                        format,
                        text_template_name='notifications/reply_email.txt',
                        html_template_name='notifications/reply_email.html',
                        local_site_name=None):
    """
    Previews the e-mail message that would be sent for a reply to a
    review of a review request.

    This is mainly used for debugging.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)
    reply = get_object_or_404(Review, pk=reply_id, base_reply_to=review)
    siteconfig = SiteConfiguration.objects.get_current()

    reply.ordered_comments = \
        reply.comments.order_by('filediff', 'first_line')

    if format == 'text':
        template_name = text_template_name
        mimetype = 'text/plain'
    elif format == 'html':
        template_name = html_template_name
        mimetype = 'text/html'
    else:
        raise Http404

    context = {
        'review_request': review_request,
        'review': review,
        'reply': reply,
        'user': request.user,
        'domain': Site.objects.get_current().domain,
        'domain_method': siteconfig.get("site_domain_method"),
    }

    has_error, context['comment_entries'] = \
        build_diff_comment_fragments(
            reply.ordered_comments, context,
            "notifications/email_diff_comment_fragment.html")

    return HttpResponse(
        render_to_string(template_name, RequestContext(request, context)),
        mimetype=mimetype)


@check_login_required
def view_screenshot(request,
                    review_request_id,
                    screenshot_id,
                    template_name='reviews/screenshot_detail.html',
                    local_site_name=None):
    """
    Displays a screenshot, along with any comments that were made on it.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)
    review = review_request.get_pending_review(request.user)
    draft = review_request.get_draft(request.user)

    query = Q(history=review_request.diffset_history)

    if draft:
        query = query & Q(reviewrequestdraft=draft)

    try:
        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
    except ScreenshotComment.DoesNotExist:
        comments = []

    return render_to_response(
        template_name,
        RequestContext(request, _make_review_request_context(review_request, {
            'draft': draft,
            'review_request_details': draft or review_request,
            'review': review,
            'details': draft or review_request,
            'screenshot': screenshot,
            'request': request,
            'comments': comments,
        })))


@check_login_required
def search(request,
           template_name='reviews/search.html',
           local_site_name=None):
    """
    Searches review requests on Review Board based on a query string.
    """
    query = request.GET.get('q', '')
    siteconfig = SiteConfiguration.objects.get_current()

    if not siteconfig.get("search_enable"):
        # FIXME: show something useful
        raise Http404

    if not query:
        # FIXME: I'm not super thrilled with this
        return HttpResponseRedirect(reverse("root"))

    import lucene
    lv = [int(x) for x in lucene.VERSION.split('.')]
    lucene_is_2x = lv[0] == 2 and lv[1] < 9
    lucene_is_3x = lv[0] == 3 or (lv[0] == 2 and lv[1] == 9)

    # We may have already initialized lucene
    try:
        lucene.initVM(lucene.CLASSPATH)
    except ValueError:
        pass

    index_file = siteconfig.get("search_index_file")
    if lucene_is_2x:
        store = lucene.FSDirectory.getDirectory(index_file, False)
    elif lucene_is_3x:
        store = lucene.FSDirectory.open(lucene.File(index_file))
    else:
        assert False

    try:
        searcher = lucene.IndexSearcher(store)
    except lucene.JavaError, e:
        # FIXME: show a useful error
        raise e

    if lucene_is_2x:
        parser = lucene.QueryParser('text', lucene.StandardAnalyzer())
        result_ids = [int(lucene.Hit.cast_(hit).getDocument().get('id')) \
                      for hit in searcher.search(parser.parse(query))]
    elif lucene_is_3x:
        parser = lucene.QueryParser(lucene.Version.LUCENE_CURRENT, 'text',
            lucene.StandardAnalyzer(lucene.Version.LUCENE_CURRENT))
        result_ids = [searcher.doc(hit.doc).get('id') \
                      for hit in searcher.search(parser.parse(query), 100).scoreDocs]


    searcher.close()

    results = ReviewRequest.objects.filter(id__in=result_ids,
                                           local_site__name=local_site_name)

    return object_list(request=request,
                       queryset=results,
                       paginate_by=10,
                       template_name=template_name,
                       extra_context={'query': query,
                                      'extra_query': 'q=%s' % query,
                                     })
