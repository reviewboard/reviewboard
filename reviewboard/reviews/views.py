from __future__ import unicode_literals

import copy
import logging
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import (HttpResponse, HttpResponseRedirect, Http404,
                         HttpResponseNotModified, HttpResponseServerError)
from django.shortcuts import (get_object_or_404, get_list_or_404,
                              render_to_response)
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six, timezone
from django.utils.decorators import method_decorator
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import ListView
from djblets.db.query import get_object_or_none
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.dates import get_latest_timestamp
from djblets.util.decorators import augment_method_from
from djblets.util.http import (set_last_modified, get_modified_since,
                               set_etag, etag_if_none_match)

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)
from reviewboard.accounts.models import ReviewRequestVisit, Profile
from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.diffutils import get_file_chunks_in_range
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import (DiffFragmentView, DiffViewerView,
                                          exception_traceback_string)
from reviewboard.extensions.hooks import (DashboardHook,
                                          ReviewRequestDetailHook,
                                          UserPageSidebarHook)
from reviewboard.reviews.ui.screenshot import LegacyScreenshotReviewUI
from reviewboard.reviews.context import (comment_counts,
                                         diffsets_with_comments,
                                         has_comments_in_diffsets_excluding,
                                         interdiffs_with_comments,
                                         make_review_request_context)
from reviewboard.reviews.datagrids import (DashboardDataGrid,
                                           GroupDataGrid,
                                           ReviewRequestDataGrid,
                                           SubmitterDataGrid,
                                           WatchedGroupDataGrid,
                                           get_sidebar_counts)
from reviewboard.reviews.models import (Comment,
                                        FileAttachmentComment,
                                        Group, ReviewRequest, Review,
                                        Screenshot, ScreenshotComment)
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.webapi.encoder import status_to_string


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
    Find a review request based on an ID, optional LocalSite name and optional
    select related query.

    If a local site is passed in on the URL, we want to look up the review
    request using the local_id instead of the pk. This allows each LocalSite
    configured to have its own review request ID namespace starting from 1.

    Returns either (None, response) or (ReviewRequest, None).
    """
    q = ReviewRequest.objects.all()

    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return None, _render_permission_denied(request)

        q = q.filter(local_site=local_site,
                     local_id=review_request_id)
    else:
        q = q.filter(pk=review_request_id)

    try:
        q = q.select_related('submitter', 'repository')
        review_request = q.get()
    except ReviewRequest.DoesNotExist:
        raise Http404

    if review_request.is_accessible_by(request.user):
        return review_request, None
    else:
        return None, _render_permission_denied(request)


def _build_id_map(objects):
    """Builds an ID map out of a list of objects.

    The resulting map makes it easy to quickly look up an object from an ID.
    """
    id_map = {}

    for obj in objects:
        id_map[obj.pk] = obj

    return id_map


def _query_for_diff(review_request, user, revision, draft):
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
    if (draft and draft.diffset_id and
        (revision is None or draft.diffset.revision == revision)):
        return draft.diffset

    query = Q(history=review_request.diffset_history_id)

    # Grab a revision if requested.
    if revision is not None:
        query = query & Q(revision=revision)

    try:
        return DiffSet.objects.filter(query).latest()
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
        except Exception as e:
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
    'summary': _('Summary'),
    'description': _('Description'),
    'testing_done': _('Testing Done'),
    'bugs_closed': _('Bugs Closed'),
    'depends_on': _('Depends On'),
    'branch': _('Branch'),
    'target_groups': _('Reviewers (Groups)'),
    'target_people': _('Reviewers (People)'),
    'screenshots': _('Screenshots'),
    'screenshot_captions': _('Screenshot Captions'),
    'files': _('Uploaded Files'),
    'file_captions': _('Uploaded File Captions'),
    'diff': _('Diff'),
}


#####
##### View functions
#####

@login_required
def new_review_request(request,
                       local_site_name=None,
                       template_name='reviews/new_review_request.html'):
    """Displays the New Review Request UI.

    This handles the creation of a review request based on either an existing
    changeset or the provided information.
    """
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None

    valid_repos = []
    repos = Repository.objects.accessible(request.user, local_site=local_site)

    for repo in repos.order_by('name'):
        try:
            scmtool = repo.get_scmtool()
            valid_repos.append({
                'id': repo.id,
                'name': repo.name,
                'scmtool_name': scmtool.name,
                'supports_post_commit': repo.supports_post_commit,
                'local_site_name': local_site_name or '',
                'files_only': False,
                'requires_change_number': scmtool.supports_pending_changesets,
                'requires_basedir': not scmtool.get_diffs_use_absolute_paths(),
            })
        except Exception as e:
            logging.error('Error loading SCMTool for repository '
                          '%s (ID %d): %s' % (repo.name, repo.id, e),
                          exc_info=1)

    valid_repos.insert(0, {
        'id': '',
        'name': _('(None - File attachments only)'),
        'scmtool_name': '',
        'supports_post_commit': False,
        'files_only': True,
        'local_site_name': local_site_name or '',
    })

    return render_to_response(template_name, RequestContext(request, {
        'repos': valid_repos,
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
    review_request, response = _find_review_request(
        request, review_request_id, local_site_name)

    if not review_request:
        return response

    # The review request detail page needs a lot of data from the database,
    # and going through standard model relations will result in far too many
    # queries. So we'll be optimizing quite a bit by prefetching and
    # re-associating data.
    #
    # We will start by getting the list of reviews. We'll filter this out into
    # some other lists, build some ID maps, and later do further processing.
    entries = []
    public_reviews = []
    body_top_replies = {}
    body_bottom_replies = {}
    replies = {}
    reply_timestamps = {}
    reviews_entry_map = {}
    reviews_id_map = {}
    review_timestamp = 0

    # Start by going through all reviews that point to this review request.
    # This includes draft reviews. We'll be separating these into a list of
    # public reviews and a mapping of replies.
    #
    # We'll also compute the latest review timestamp early, for the ETag
    # generation below.
    #
    # The second pass will come after the ETag calculation.
    all_reviews = list(review_request.reviews.select_related('user'))

    for review in all_reviews:
        review._body_top_replies = []
        review._body_bottom_replies = []

        if review.public:
            # This is a review we'll display on the page. Keep track of it
            # for later display and filtering.
            public_reviews.append(review)
            parent_id = review.base_reply_to_id

            if parent_id is not None:
                # This is a reply to a review. We'll store the reply data
                # into a map, which associates a review ID with its list of
                # replies, and also figures out the timestamps.
                #
                # Later, we'll use this to associate reviews and replies for
                # rendering.
                if parent_id not in replies:
                    replies[parent_id] = [review]
                    reply_timestamps[parent_id] = review.timestamp
                else:
                    replies[parent_id].append(review)
                    reply_timestamps[parent_id] = max(
                        reply_timestamps[parent_id],
                        review.timestamp)
        elif (request.user.is_authenticated() and
              review.user_id == request.user.pk and
              (review_timestamp == 0 or review.timestamp > review_timestamp)):
            # This is the latest draft so far from the current user, so
            # we'll use this timestamp in the ETag.
            review_timestamp = review.timestamp

        if review.public or (request.user.is_authenticated() and
                             review.user_id == request.user.pk):
            reviews_id_map[review.pk] = review

            # If this review is replying to another review's body_top or
            # body_bottom fields, store that data.
            for reply_id, reply_list in (
                (review.body_top_reply_to_id, body_top_replies),
                (review.body_bottom_reply_to_id, body_bottom_replies)):
                if reply_id is not None:
                    if reply_id not in reply_list:
                        reply_list[reply_id] = [review]
                    else:
                        reply_list[reply_id].append(review)

    pending_review = review_request.get_pending_review(request.user)
    review_ids = list(reviews_id_map.keys())
    last_visited = 0
    starred = False

    if request.user.is_authenticated():
        # If the review request is public and pending review and if the user
        # is logged in, mark that they've visited this review request.
        if review_request.public and review_request.status == "P":
            visited, visited_is_new = ReviewRequestVisit.objects.get_or_create(
                user=request.user, review_request=review_request)
            last_visited = visited.timestamp.replace(tzinfo=utc)
            visited.timestamp = timezone.now()
            visited.save()

        try:
            profile = request.user.get_profile()
            starred_review_requests = \
                profile.starred_review_requests.filter(pk=review_request.pk)
            starred = (starred_review_requests.count() > 0)
        except Profile.DoesNotExist:
            pass

    draft = review_request.get_draft(request.user)
    review_request_details = draft or review_request
    diffsets = review_request.get_diffsets()

    # Map diffset IDs to their revision ID for changedescs
    diffset_versions = {}
    for diffset in diffsets:
        diffset_versions[diffset.pk] = diffset.revision

    # Find out if we can bail early. Generate an ETag for this.
    last_activity_time, updated_object = \
        review_request.get_last_activity(diffsets, public_reviews)

    if draft:
        draft_timestamp = draft.last_updated
    else:
        draft_timestamp = ""

    blocks = list(review_request.blocks.all())

    etag = "%s:%s:%s:%s:%s:%s:%s:%s" % (
        request.user, last_activity_time, draft_timestamp,
        review_timestamp, review_request.last_review_activity_timestamp,
        ','.join([six.text_type(r.pk) for r in blocks]),
        int(starred), settings.AJAX_SERIAL
    )

    if etag_if_none_match(request, etag):
        return HttpResponseNotModified()

    # Get the list of public ChangeDescriptions.
    #
    # We want to get the latest ChangeDescription along with this. This is
    # best done here and not in a separate SQL query.
    changedescs = list(review_request.changedescs.filter(public=True))

    if changedescs:
        # We sort from newest to oldest, so the latest one is the first.
        latest_changedesc = changedescs[0]
        latest_timestamp = latest_changedesc.timestamp
    else:
        latest_changedesc = None
        latest_timestamp = None

    # Now that we have the list of public reviews and all that metadata,
    # being processing them and adding entries for display in the page.
    #
    # We do this here and not above because we don't want to build *too* much
    # before the ETag check.
    for review in public_reviews:
        if not review.is_reply():
            state = ''

            # Mark as collapsed if the review is older than the latest
            # change.
            if latest_timestamp and review.timestamp < latest_timestamp:
                state = 'collapsed'

            latest_reply = reply_timestamps.get(review.pk, None)

            # Mark as expanded if there is a reply newer than last_visited
            if latest_reply and last_visited and last_visited < latest_reply:
                state = ''

            entry = {
                'review': review,
                'comments': {
                    'diff_comments': [],
                    'screenshot_comments': [],
                    'file_attachment_comments': []
                },
                'timestamp': review.timestamp,
                'class': state,
                'collapsed': state == 'collapsed',
            }
            reviews_entry_map[review.pk] = entry
            entries.append(entry)

    # Link up all the review body replies.
    for key, reply_list in (('_body_top_replies', body_top_replies),
                            ('_body_bottom_replies', body_bottom_replies)):
        for reply_id, replies in six.iteritems(reply_list):
            setattr(reviews_id_map[reply_id], key, replies)

    # Get all the file attachments and screenshots and build a couple maps,
    # so we can easily associate those objects in comments.
    file_attachments = []

    for file_attachment in review_request_details.get_file_attachments():
        file_attachment._comments = []
        file_attachments.append(file_attachment)

    screenshots = []

    for screenshot in review_request_details.get_screenshots():
        screenshot._comments = []
        screenshots.append(screenshot)

    file_attachment_id_map = _build_id_map(file_attachments)
    screenshot_id_map = _build_id_map(screenshots)

    # There will be non-visible (generally deleted) file attachments and
    # screenshots we'll need to reference. to save on queries, we'll only
    # get these when we first encounter one not in the above maps.
    has_inactive_file_attachments = False
    has_inactive_screenshots = False

    issues = {
        'total': 0,
        'open': 0,
        'resolved': 0,
        'dropped': 0
    }

    # Get all the comments and attach them to the reviews.
    for model, key, ordering in (
        (Comment, 'diff_comments',
         ('comment__filediff', 'comment__first_line', 'comment__timestamp')),
        (ScreenshotComment, 'screenshot_comments', None),
        (FileAttachmentComment, 'file_attachment_comments', None)):
        # Due to how we initially made the schema, we have a ManyToManyField
        # inbetween comments and reviews, instead of comments having a
        # ForeignKey to the review. This makes it difficult to easily go
        # from a comment to a review ID.
        #
        # The solution to this is to not query the comment objects, but rather
        # the through table. This will let us grab the review and comment in
        # one go, using select_related.
        related_field = model.review.related.field
        comment_field_name = related_field.m2m_reverse_field_name()
        through = related_field.rel.through
        q = through.objects.filter(review__in=review_ids).select_related()

        if ordering:
            q = q.order_by(*ordering)

        objs = list(q)

        # Two passes. One to build a mapping, and one to actually process
        # comments.
        comment_map = {}

        for obj in objs:
            comment = getattr(obj, comment_field_name)
            comment_map[comment.pk] = comment
            comment._replies = []

        for obj in objs:
            comment = getattr(obj, comment_field_name)

            # Short-circuit some object fetches for the comment by setting
            # some internal state on them.
            assert obj.review_id in reviews_id_map
            parent_review = reviews_id_map[obj.review_id]
            comment._review = parent_review
            comment._review_request = review_request

            # If the comment has an associated object that we've already
            # queried, attach it to prevent a future lookup.
            if isinstance(comment, ScreenshotComment):
                if (comment.screenshot_id not in screenshot_id_map and
                    not has_inactive_screenshots):
                    inactive_screenshots = \
                        list(review_request_details.get_inactive_screenshots())

                    for screenshot in inactive_screenshots:
                        screenshot._comments = []

                    screenshot_id_map.update(
                        _build_id_map(inactive_screenshots))
                    has_inactive_screenshots = True

                if comment.screenshot_id in screenshot_id_map:
                    screenshot = screenshot_id_map[comment.screenshot_id]
                    comment.screenshot = screenshot
                    screenshot._comments.append(comment)
            elif isinstance(comment, FileAttachmentComment):
                if (comment.file_attachment_id not in file_attachment_id_map
                    and not has_inactive_file_attachments):
                    inactive_file_attachments = list(
                        review_request_details.get_inactive_file_attachments())

                    for file_attachment in inactive_file_attachments:
                        file_attachment._comments = []

                    file_attachment_id_map.update(
                        _build_id_map(inactive_file_attachments))
                    has_inactive_file_attachments = True

                if comment.file_attachment_id in file_attachment_id_map:
                    file_attachment = \
                        file_attachment_id_map[comment.file_attachment_id]
                    comment.file_attachment = file_attachment
                    file_attachment._comments.append(comment)

            if parent_review.is_reply():
                # This is a reply to a comment. Add it to the list of replies.
                assert obj.review_id not in reviews_entry_map
                assert parent_review.base_reply_to_id in reviews_entry_map

                # If there's an entry that isn't a reply, then it's
                # orphaned. Ignore it.
                if comment.is_reply():
                    replied_comment = comment_map[comment.reply_to_id]
                    replied_comment._replies.append(comment)
            elif parent_review.public:
                # This is a comment on a public review we're going to show.
                # Add it to the list.
                assert obj.review_id in reviews_entry_map
                entry = reviews_entry_map[obj.review_id]
                entry['comments'][key].append(comment)

                if comment.issue_opened:
                    status_key = \
                        comment.issue_status_to_string(comment.issue_status)
                    issues[status_key] += 1
                    issues['total'] += 1

    # Sort all the reviews and ChangeDescriptions into a single list, for
    # display.
    for changedesc in changedescs:
        fields_changed = []

        for name, info in six.iteritems(changedesc.fields_changed):
            info = copy.deepcopy(info)
            multiline = False
            diff_revision = False

            if 'added' in info or 'removed' in info:
                change_type = 'add_remove'

                # We don't hard-code URLs in the bug info, since the
                # tracker may move, but we can do it here.
                if (name == "bugs_closed" and
                    review_request.repository and
                    review_request.repository.bug_tracker):
                    bug_url = review_request.repository.bug_tracker
                    for field in info:
                        for i, buginfo in enumerate(info[field]):
                            try:
                                full_bug_url = bug_url % buginfo[0]
                                info[field][i] = (buginfo[0], full_bug_url)
                            except TypeError:
                                logging.warning("Invalid bugtracker url format")
                elif name == "diff" and "added" in info:
                    # Sets the incremental revision number for a review
                    # request change, provided it is an updated diff.
                    diff_revision = diffset_versions[info['added'][0][2]]

            elif 'old' in info or 'new' in info:
                change_type = 'changed'
                multiline = (name == "description" or name == "testing_done")

                # Branch text is allowed to have entities, so mark it safe.
                if name == "branch":
                    if 'old' in info:
                        info['old'][0] = mark_safe(info['old'][0])

                    if 'new' in info:
                        info['new'][0] = mark_safe(info['new'][0])

                # Make status human readable.
                if name == 'status':
                    if 'old' in info:
                        info['old'][0] = status_to_string(info['old'][0])

                    if 'new' in info:
                        info['new'][0] = status_to_string(info['new'][0])

            elif name == "screenshot_captions":
                change_type = 'screenshot_captions'
            elif name == "file_captions":
                change_type = 'file_captions'
            else:
                # No clue what this is. Bail.
                continue

            fields_changed.append({
                'title': fields_changed_name_map.get(name, name),
                'multiline': multiline,
                'info': info,
                'type': change_type,
                'diff_revision': diff_revision,
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
            'collapsed': state == 'collapsed',
        })

    entries.sort(key=lambda item: item['timestamp'])

    close_description = ''
    close_description_rich_text = False

    if latest_changedesc and 'status' in latest_changedesc.fields_changed:
        status = latest_changedesc.fields_changed['status']['new'][0]

        if status in (ReviewRequest.DISCARDED, ReviewRequest.SUBMITTED):
            close_description = latest_changedesc.text
            close_description_rich_text = latest_changedesc.rich_text

    context_data = make_review_request_context(request, review_request, {
        'blocks': blocks,
        'draft': draft,
        'detail_hooks': ReviewRequestDetailHook.hooks,
        'review_request_details': review_request_details,
        'entries': entries,
        'last_activity_time': last_activity_time,
        'review': pending_review,
        'request': request,
        'latest_changedesc': latest_changedesc,
        'close_description': close_description,
        'close_description_rich_text': close_description_rich_text,
        'PRE_CREATION': PRE_CREATION,
        'issues': issues,
        'has_diffs': (draft and draft.diffset) or len(diffsets) > 0,
        'file_attachments': [file_attachment
                             for file_attachment in file_attachments
                             if not file_attachment.is_from_diff],
        'all_file_attachments': file_attachments,
        'screenshots': screenshots,
    })

    response = render_to_response(template_name,
                                  RequestContext(request, context_data))
    set_etag(response, etag)

    return response


@check_login_required
def all_review_requests(request,
                        local_site_name=None,
                        template_name='reviews/datagrid.html'):
    """Displays a list of all review requests."""
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.public(user=request.user,
                                     status=None,
                                     local_site=local_site,
                                     with_counts=True),
        _("All Review Requests"),
        local_site=local_site)
    return datagrid.render_to_response(template_name)


@check_login_required
def submitter_list(request,
                   local_site_name=None,
                   template_name='reviews/datagrid.html'):
    """Displays a list of all users."""
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None
    grid = SubmitterDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)


@check_login_required
def group_list(request,
               local_site_name=None,
               template_name='reviews/datagrid.html'):
    """Displays a list of all review groups."""
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None
    grid = GroupDataGrid(request, local_site=local_site)
    return grid.render_to_response(template_name)


@login_required
@valid_prefs_required
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
    context = {}

    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None

    if view == "watched-groups":
        # This is special. We want to return a list of groups, not
        # review requests.
        grid = WatchedGroupDataGrid(request, local_site=local_site)
    else:
        grid = DashboardDataGrid(request, local_site=local_site)

    if not request.GET.get('gridonly', False):
        context = {
            'sidebar_counts': get_sidebar_counts(request.user, local_site),
            'sidebar_hooks': DashboardHook.hooks,
        }

    return grid.render_to_response(template_name, extra_context=context)


@check_login_required
def group(request,
          name,
          template_name='reviews/datagrid.html',
          local_site_name=None):
    """
    A list of review requests belonging to a particular group.
    """
    # Make sure the group exists
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None
    group = get_object_or_404(Group, name=name, local_site=local_site)

    if not group.is_accessible_by(request.user):
        return _render_permission_denied(
            request, 'reviews/group_permission_denied.html')

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.to_group(name,
                                       local_site,
                                       user=request.user,
                                       status=None,
                                       with_counts=True),
        _("Review requests for %s") % name,
        local_site=local_site)

    return datagrid.render_to_response(template_name)


@check_login_required
def group_members(request,
                  name,
                  template_name='reviews/datagrid.html',
                  local_site_name=None):
    """
    A list of users registered for a particular group.
    """
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None

    # Make sure the group exists
    group = get_object_or_404(Group,
                              name=name,
                              local_site=local_site)

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
              template_name='reviews/user_page.html',
              local_site_name=None):
    """
    A list of review requests owned by a particular user.
    """
    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)
        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)
    else:
        local_site = None

    # Make sure the user exists
    if local_site:
        try:
            user = local_site.users.get(username=username)
        except User.DoesNotExist:
            raise Http404
    else:
        user = get_object_or_404(User, username=username)

    datagrid = ReviewRequestDataGrid(
        request,
        ReviewRequest.objects.from_user(username,
                                        user=request.user,
                                        status=None,
                                        with_counts=True,
                                        local_site=local_site,
                                        filter_private=True),
        _("%s's review requests") % username,
        local_site=local_site)

    return datagrid.render_to_response(template_name, extra_context={
        'show_profile': user.is_profile_visible(request.user),
        'sidebar_hooks': UserPageSidebarHook.hooks,
        'viewing_user': user,
        'groups': user.review_groups.accessible(request.user),
    })


class ReviewsDiffViewerView(DiffViewerView):
    """Renders the diff viewer for a review request.

    This wraps the base DiffViewerView to display a diff for the given
    review request and the given diff revision or range.

    The view expects the following parameters to be provided:

        * review_request_id
          - The ID of the ReviewRequest containing the diff to render.

    The following may also be provided:

        * revision
          - The DiffSet revision to render.

        * interdiff_revision
          - The second DiffSet revision in an interdiff revision range.

        * local_site_name
          - The name of the LocalSite for the ReviewRequest must be on.

    See DiffViewerView's documentation for the accepted query parameters.
    """
    @method_decorator(check_login_required)
    @augment_method_from(DiffViewerView)
    def dispatch(self, *args, **kwargs):
        pass

    def get(self, request, review_request_id, revision=None,
            interdiff_revision=None, local_site_name=None):
        """Handles GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.
        """
        review_request, response = \
            _find_review_request(request, review_request_id, local_site_name)

        if not review_request:
            return response

        self.review_request = review_request
        self.draft = review_request.get_draft(request.user)
        self.diffset = _query_for_diff(review_request, request.user,
                                       revision, self.draft)
        self.interdiffset = None

        if interdiff_revision and interdiff_revision != revision:
            # An interdiff revision was specified. Try to find a matching
            # diffset.
            self.interdiffset = _query_for_diff(review_request, request.user,
                                                interdiff_revision, self.draft)

        return super(ReviewsDiffViewerView, self).get(
            request, self.diffset, self.interdiffset)

    def get_context_data(self, *args, **kwargs):
        """Calculates additional context data for rendering.

        This provides some additional data used for rendering the diff
        viewer. This data is more specific to the reviewing functionality,
        as opposed to the data calculated by DiffViewerView.get_context_data,
        which is more focused on the actual diff.
        """
        # Try to find an existing pending review of this diff from the
        # current user.
        pending_review = \
            self.review_request.get_pending_review(self.request.user)

        has_draft_diff = self.draft and self.draft.diffset
        is_draft_diff = has_draft_diff and self.draft.diffset == self.diffset
        is_draft_interdiff = (has_draft_diff and self.interdiffset and
                              self.draft.diffset == self.interdiffset)

        # Get the list of diffsets. We only want to calculate this once.
        diffsets = self.review_request.get_diffsets()
        num_diffs = len(diffsets)

        if num_diffs > 0:
            latest_diffset = diffsets[-1]
        else:
            latest_diffset = None

        if self.draft and self.draft.diffset:
            num_diffs += 1

        last_activity_time, updated_object = \
            self.review_request.get_last_activity(diffsets)

        file_attachments = list(self.review_request.get_file_attachments())
        screenshots = list(self.review_request.get_screenshots())

        try:
            latest_changedesc = \
                self.review_request.changedescs.filter(public=True).latest()
        except ChangeDescription.DoesNotExist:
            latest_changedesc = None

        # Compute the lists of comments based on filediffs and interfilediffs.
        # We do this using the 'through' table so that we can select_related
        # the reviews and comments.
        comments = {}
        q = Comment.review.related.field.rel.through.objects.filter(
            review__review_request=self.review_request)
        q = q.select_related()

        for obj in q:
            comment = obj.comment
            comment._review = obj.review
            key = (comment.filediff_id, comment.interfilediff_id)
            comments.setdefault(key, []).append(comment)

        close_description = ''
        close_description_rich_text = False

        if latest_changedesc and 'status' in latest_changedesc.fields_changed:
            status = latest_changedesc.fields_changed['status']['new'][0]

            if status in (ReviewRequest.DISCARDED, ReviewRequest.SUBMITTED):
                close_description = latest_changedesc.text
                close_description_rich_text = latest_changedesc.rich_text

        context = super(ReviewsDiffViewerView, self).get_context_data(
            *args, **kwargs)

        context.update({
            'close_description': close_description,
            'close_description_rich_text': close_description_rich_text,
            'diffsets': diffsets,
            'latest_diffset': latest_diffset,
            'review': pending_review,
            'review_request_details': self.draft or self.review_request,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': [file_attachment
                                 for file_attachment in file_attachments
                                 if not file_attachment.is_from_diff],
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
        })

        context.update(
            make_review_request_context(self.request, self.review_request))

        diffset_pair = context['diffset_pair']
        context['diff_context'].update({
            'num_diffs': num_diffs,
            'comments_hint': {
                'has_other_comments': has_comments_in_diffsets_excluding(
                    pending_review, diffset_pair),
                'diffsets_with_comments': [
                    {
                        'revision': diffset_info['diffset'].revision,
                        'is_current': diffset_info['is_current'],
                    }
                    for diffset_info in diffsets_with_comments(
                        pending_review, diffset_pair)
                ],
                'interdiffs_with_comments': [
                    {
                        'old_revision': pair['diffset'].revision,
                        'new_revision': pair['interdiff'].revision,
                        'is_current': pair['is_current'],
                    }
                    for pair in interdiffs_with_comments(
                        pending_review, diffset_pair)
                ],
            },
        })
        context['diff_context']['revision'].update({
            'latest_revision': (latest_diffset.revision
                                if latest_diffset else None),
            'is_draft_diff': is_draft_diff,
            'is_draft_interdiff': is_draft_interdiff,
        })

        files = []
        for f in context['files']:
            filediff = f['filediff']
            interfilediff = f['interfilediff']
            data = {
                'newfile': f['newfile'],
                'binary': f['binary'],
                'deleted': f['deleted'],
                'id': f['filediff'].pk,
                'depot_filename': f['depot_filename'],
                'dest_filename': f['dest_filename'],
                'dest_revision': f['dest_revision'],
                'revision': f['revision'],
                'filediff': {
                    'id': filediff.id,
                    'revision': filediff.diffset.revision,
                },
                'index': f['index'],
                'comment_counts': comment_counts(self.request.user, comments,
                                                 filediff, interfilediff),
            }

            if interfilediff:
                data['interfilediff'] = {
                    'id': interfilediff.id,
                    'revision': interfilediff.diffset.revision,
                }

            files.append(data)

        context['diff_context']['files'] = files

        return context


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

    draft = review_request.get_draft(request.user)
    diffset = _query_for_diff(review_request, request.user, revision, draft)

    tool = review_request.repository.get_scmtool()
    data = tool.get_parser('').raw_diff(diffset)

    resp = HttpResponse(data, mimetype='text/x-patch')

    if diffset.name == 'diff':
        filename = "rb%d.patch" % review_request.display_id
    else:
        filename = six.text_type(diffset.name).encode('ascii', 'ignore')

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
    response['Expires'] = http_date(time.time() + 60 * 60 * 24 * 365)  # 1 year
    return response


class ReviewsDiffFragmentView(DiffFragmentView):
    """Renders a fragment from a file in the diff viewer.

    Displays just a fragment of a diff or interdiff owned by the given
    review request. The fragment is identified by the chunk index in the
    diff.

    The view expects the following parameters to be provided:

        * review_request_id
          - The ID of the ReviewRequest containing the diff to render.

        * revision
          - The DiffSet revision to render.

        * filediff_id
          - The ID of the FileDiff within the DiffSet.

    The following may also be provided:

        * interdiff_revision
          - The second DiffSet revision in an interdiff revision range.

        * chunkindex
          - The index (0-based) of the chunk to render. If left out, the
            entire file will be rendered.

        * local_site_name
          - The name of the LocalSite for the ReviewRequest must be on.

    See DiffFragmentView's documentation for the accepted query parameters.
    """
    @method_decorator(check_login_required)
    @augment_method_from(DiffFragmentView)
    def dispatch(self, *args, **kwargs):
        pass

    def get(self, request, review_request_id, revision, filediff_id,
            interdiff_revision=None, chunkindex=None,
            local_site_name=None, *args, **kwargs):
        """Handles GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.
        """
        review_request, response = \
            _find_review_request(request, review_request_id, local_site_name)

        if not review_request:
            return response

        draft = review_request.get_draft(request.user)

        if interdiff_revision is not None:
            interdiffset = _query_for_diff(review_request, request.user,
                                           interdiff_revision, draft)
        else:
            interdiffset = None

        diffset = _query_for_diff(review_request, request.user, revision, draft)

        return super(ReviewsDiffFragmentView, self).get(
            request,
            diffset_or_id=diffset,
            filediff_id=filediff_id,
            interdiffset_or_id=interdiffset,
            chunkindex=chunkindex)

    def create_renderer(self, *args, **kwargs):
        """Creates the DiffRenderer for this fragment.

        This will augment the renderer for binary files by looking up
        file attachments, if review UIs are involved, disabling caching.
        """
        renderer = super(ReviewsDiffFragmentView, self).create_renderer(
            *args, **kwargs)

        if self.diff_file['binary']:
            # Determine the file attachments to display in the diff viewer,
            # if any.
            filediff = self.diff_file['filediff']
            interfilediff = self.diff_file['interfilediff']

            orig_attachment = None
            modified_attachment = None

            if self.diff_file['force_interdiff']:
                orig_attachment = self._get_diff_file_attachment(filediff)
                modified_attachment = \
                    self._get_diff_file_attachment(interfilediff)
            else:
                modified_attachment = self._get_diff_file_attachment(filediff)

                if not self.diff_file['is_new_file']:
                    orig_attachment = \
                        self._get_diff_file_attachment(filediff, False)

            diff_review_ui = None
            diff_review_ui_html = None
            orig_review_ui = None
            orig_review_ui_html = None
            modified_review_ui = None
            modified_review_ui_html = None

            if orig_attachment:
                orig_review_ui = orig_attachment.review_ui

            if modified_attachment:
                modified_review_ui = modified_attachment.review_ui

            # See if we're able to generate a diff review UI for these files.
            if (orig_review_ui and modified_review_ui and
                orig_review_ui.__class__ is modified_review_ui.__class__ and
                modified_review_ui.supports_diffing):
                # Both files are able to be diffed by this review UI.
                # We'll display a special diff review UI instead of two
                # side-by-side review UIs.
                diff_review_ui = modified_review_ui
                diff_review_ui.set_diff_against(orig_attachment)
                diff_review_ui_html = \
                    self._render_review_ui(diff_review_ui, False)
            else:
                # We won't be showing a diff of these files. Instead, just
                # grab the review UIs and render them.
                orig_review_ui_html = \
                    self._render_review_ui(orig_review_ui)
                modified_review_ui_html = \
                    self._render_review_ui(modified_review_ui)

            if (diff_review_ui_html or orig_review_ui_html or
                modified_review_ui_html):
                # Don't cache the view, because the Review UI may care about
                # state that we can't anticipate. At the least, it may have
                # comments or other data that change between renders, and we
                # don't want that to go stale.
                renderer.allow_caching = False

            renderer.extra_context.update({
                'orig_diff_file_attachment': orig_attachment,
                'modified_diff_file_attachment': modified_attachment,
                'orig_attachment_review_ui_html': orig_review_ui_html,
                'modified_attachment_review_ui_html': modified_review_ui_html,
                'diff_attachment_review_ui_html': diff_review_ui_html,
            })

        return renderer

    def _render_review_ui(self, review_ui, inline_only=True):
        """Renders the review UI for a file attachment."""
        if review_ui and (not inline_only or review_ui.allow_inline):
            return mark_safe(review_ui.render_to_string(self.request))

        return None

    def _get_diff_file_attachment(self, filediff, use_modified=True):
        """Fetch the FileAttachment associated with a FileDiff.

        This will query for the FileAttachment based on the provided filediff,
        and set the retrieved diff file attachment to a variable whose name is
        provided as an argument to this tag.

        If 'use_modified' is True, the FileAttachment returned will be from the
        modified version of the new file. Otherwise, it's the original file
        that's being modified.

        If no matching FileAttachment is found or if there is more than one
        FileAttachment associated with one FileDiff, None is returned. An error
        is logged in the latter case.
        """
        if not filediff:
            return None

        try:
            return FileAttachment.objects.get_for_filediff(filediff,
                                                           use_modified)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            # Only one FileAttachment should be associated with a FileDiff
            logging.error('More than one FileAttachments associated with '
                          'FileDiff %s',
                          filediff.pk,
                          exc_info=1)
            return None


@check_login_required
def preview_review_request_email(
    request,
    review_request_id,
    format,
    text_template_name='notifications/review_request_email.txt',
    html_template_name='notifications/review_request_email.html',
    changedesc_id=None,
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

    extra_context = {}

    if changedesc_id:
        changedesc = get_object_or_404(ChangeDescription, pk=changedesc_id)
        extra_context['change_text'] = changedesc.text
        extra_context['changes'] = changedesc.fields_changed

    siteconfig = SiteConfiguration.objects.get_current()

    if format == 'text':
        template_name = text_template_name
        mimetype = 'text/plain'
    elif format == 'html':
        template_name = html_template_name
        mimetype = 'text/html'
    else:
        raise Http404

    return HttpResponse(render_to_string(
        template_name,
        RequestContext(request, dict({
            'review_request': review_request,
            'user': request.user,
            'domain': Site.objects.get_current().domain,
            'domain_method': siteconfig.get("site_domain_method"),
        }, **extra_context)),
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
def review_file_attachment(request,
                           review_request_id,
                           file_attachment_id,
                           local_site_name=None):
    """Displays a file attachment with a review UI."""
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    file_attachment = get_object_or_404(FileAttachment, pk=file_attachment_id)
    review_ui = file_attachment.review_ui

    if review_ui:
        return review_ui.render_to_response(request)
    else:
        raise Http404


@check_login_required
def view_screenshot(request,
                    review_request_id,
                    screenshot_id,
                    local_site_name=None):
    """
    Displays a screenshot, along with any comments that were made on it.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site_name)

    if not review_request:
        return response

    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)
    review_ui = LegacyScreenshotReviewUI(review_request, screenshot)

    return review_ui.render_to_response(request)


class ReviewsSearchView(ListView):
    template_name = 'reviews/search.html'

    def get_context_data(self, **kwargs):
        query = self.request.GET.get('q', '')
        context_data = super(ReviewsSearchView, self).get_context_data(**kwargs)
        context_data.update({
            'query': query,
            'extra_query': 'q=%s' % query,
        })

        return context_data

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        siteconfig = SiteConfiguration.objects.get_current()

        if not siteconfig.get("search_enable"):
            # FIXME: show something useful
            raise Http404

        if not query:
            # FIXME: I'm not super thrilled with this
            return HttpResponseRedirect(reverse("root"))

        if query.isdigit():
            query_review_request = get_object_or_none(ReviewRequest, pk=query)
            if query_review_request:
                return HttpResponseRedirect(
                    query_review_request.get_absolute_url())

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
        except lucene.JavaError as e:
            # FIXME: show a useful error
            raise e

        if lucene_is_2x:
            parser = lucene.QueryParser('text', lucene.StandardAnalyzer())
            result_ids = [int(lucene.Hit.cast_(hit).getDocument().get('id'))
                          for hit in searcher.search(parser.parse(query))]
        elif lucene_is_3x:
            parser = lucene.QueryParser(
                lucene.Version.LUCENE_CURRENT, 'text',
                lucene.StandardAnalyzer(lucene.Version.LUCENE_CURRENT))

            result_ids = [
                searcher.doc(hit.doc).get('id')
                for hit in searcher.search(parser.parse(query), 100).scoreDocs
            ]

        searcher.close()

        return ReviewRequest.objects.filter(
            id__in=result_ids,
            local_site__name=self.kwargs['local_site_name'])


@check_login_required
def user_infobox(request, username,
                 template_name='accounts/user_infobox.html',
                 local_site_name=None):
    """Displays a user info popup.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """
    user = get_object_or_404(User, username=username)

    if local_site_name:
        local_site = get_object_or_404(LocalSite, name=local_site_name)

        if not local_site.is_accessible_by(request.user):
            return _render_permission_denied(request)

    show_profile = user.is_profile_visible(request.user)

    etag = ':'.join([user.first_name,
                     user.last_name,
                     user.email,
                     six.text_type(user.last_login),
                     six.text_type(settings.AJAX_SERIAL),
                     six.text_type(show_profile)])
    etag = etag.encode('ascii', 'replace')

    if etag_if_none_match(request, etag):
        return HttpResponseNotModified()

    response = render_to_response(template_name, RequestContext(request, {
        'show_profile': show_profile,
        'requested_user': user,
    }))
    set_etag(response, etag)

    return response
