from __future__ import unicode_literals

import logging
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.http import (Http404,
                         HttpResponse,
                         HttpResponseNotFound,
                         HttpResponseNotModified,
                         HttpResponseRedirect)
from django.shortcuts import (get_object_or_404, get_list_or_404,
                              render_to_response)
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six, timezone
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.dates import get_latest_timestamp
from djblets.util.decorators import augment_method_from
from djblets.util.http import (encode_etag, set_last_modified,
                               set_etag, etag_if_none_match)

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)
from reviewboard.accounts.models import ReviewRequestVisit, Profile
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.diffutils import (convert_to_unicode,
                                              get_file_chunks_in_range,
                                              get_last_header_before_line,
                                              get_last_line_number_in_diff,
                                              get_original_file,
                                              get_patched_file)
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import (DiffFragmentView, DiffViewerView,
                                          exception_traceback_string)
from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.reviews.ui.screenshot import LegacyScreenshotReviewUI
from reviewboard.reviews.context import (comment_counts,
                                         diffsets_with_comments,
                                         has_comments_in_diffsets_excluding,
                                         interdiffs_with_comments,
                                         make_review_request_context)
from reviewboard.reviews.fields import get_review_request_fieldsets
from reviewboard.reviews.markdown_utils import is_rich_text_default_for_user
from reviewboard.reviews.models import (BaseComment, Comment,
                                        FileAttachmentComment,
                                        ReviewRequest, Review,
                                        Screenshot, ScreenshotComment)
from reviewboard.reviews.ui.base import FileAttachmentReviewUI
from reviewboard.scmtools.models import Repository
from reviewboard.site.decorators import check_local_site_access
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.encoder import status_to_string


#
# Helper functions
#


def _render_permission_denied(
    request,
    template_name='reviews/review_request_permission_denied.html'):
    """Renders a Permission Denied error for this review request."""

    response = render_to_response(template_name, RequestContext(request))
    response.status_code = 403
    return response


def _find_review_request_object(review_request_id, local_site):
    """Finds a review request given an ID and an optional LocalSite name.

    If a local site is passed in on the URL, we want to look up the review
    request using the local_id instead of the pk. This allows each LocalSite
    configured to have its own review request ID namespace starting from 1.
    """
    q = ReviewRequest.objects.all()

    if local_site:
        q = q.filter(local_site=local_site,
                     local_id=review_request_id)
    else:
        q = q.filter(pk=review_request_id)

    try:
        q = q.select_related('submitter', 'repository')
        return q.get()
    except ReviewRequest.DoesNotExist:
        raise Http404


def _find_review_request(request, review_request_id, local_site):
    """Finds a review request matching an ID, checking user access permissions.

    If the review request is accessible by the user, we return
    (ReviewRequest, None). Otherwise, we return (None, response).
    """
    review_request = _find_review_request_object(review_request_id, local_site)

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
    error_template_name='diffviewer/diff_fragment_error.html',
    lines_of_context=None,
    show_controls=False):

    comment_entries = []
    had_error = False
    siteconfig = SiteConfiguration.objects.get_current()

    if lines_of_context is None:
        lines_of_context = [0, 0]

    for comment in comments:
        try:
            max_line = get_last_line_number_in_diff(context, comment.filediff,
                                                    comment.interfilediff)

            first_line = max(1, comment.first_line - lines_of_context[0])
            last_line = min(comment.last_line + lines_of_context[1], max_line)
            num_lines = last_line - first_line + 1

            chunks = list(get_file_chunks_in_range(context,
                                                   comment.filediff,
                                                   comment.interfilediff,
                                                   first_line,
                                                   num_lines))

            content = render_to_string(comment_template_name, {
                'comment': comment,
                'header': get_last_header_before_line(context,
                                                      comment.filediff,
                                                      comment.interfilediff,
                                                      first_line),
                'chunks': chunks,
                'domain': Site.objects.get_current().domain,
                'domain_method': siteconfig.get('site_domain_method'),
                'lines_of_context': lines_of_context,
                'expandable_above': show_controls and first_line != 1,
                'expandable_below': show_controls and last_line != max_line,
                'collapsible': lines_of_context != [0, 0],
                'lines_above': first_line - 1,
                'lines_below': max_line - last_line,
                'first_line': first_line,
            })
        except Exception as e:
            content = exception_traceback_string(
                None, e, error_template_name, {
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
            chunks = []

        comment_entries.append({
            'comment': comment,
            'html': content,
            'chunks': chunks,
        })

    return had_error, comment_entries


#
# View functions
#

@check_login_required
@valid_prefs_required
def root(request, local_site_name=None):
    """Handles the root URL of Review Board or a Local Site.

    If the user is authenticated, this will redirect to their Dashboard.
    Otherwise, they'll be redirected to the All Review Requests page.

    Either page may then redirect for login or show a Permission Denied,
    depending on the settings.
    """
    if request.user.is_authenticated():
        url_name = 'dashboard'
    else:
        url_name = 'all-review-requests'

    return HttpResponseRedirect(
        local_site_reverse(url_name, local_site_name=local_site_name))


@login_required
@check_local_site_access
def new_review_request(request,
                       local_site=None,
                       template_name='reviews/new_review_request.html'):
    """Displays the New Review Request UI.

    This handles the creation of a review request based on either an existing
    changeset or the provided information.
    """
    valid_repos = []
    repos = Repository.objects.accessible(request.user, local_site=local_site)

    if local_site:
        local_site_name = local_site.name
    else:
        local_site_name = ''

    for repo in repos.order_by('name'):
        try:
            scmtool = repo.get_scmtool()
            valid_repos.append({
                'id': repo.id,
                'name': repo.name,
                'scmtool_name': scmtool.name,
                'supports_post_commit': repo.supports_post_commit,
                'local_site_name': local_site_name,
                'files_only': False,
                'requires_change_number': scmtool.supports_pending_changesets,
                'requires_basedir': not scmtool.get_diffs_use_absolute_paths(),
            })
        except Exception:
            logging.exception('Error loading SCMTool for repository "%s" '
                              '(ID %d)',
                              repo.name, repo.id)

    valid_repos.insert(0, {
        'id': '',
        'name': _('(None - File attachments only)'),
        'scmtool_name': '',
        'supports_post_commit': False,
        'files_only': True,
        'local_site_name': local_site_name,
    })

    return render_to_response(template_name, RequestContext(request, {
        'repos': valid_repos,
    }))


def _get_latest_file_attachments(file_attachments):
    file_attachment_histories = FileAttachmentHistory.objects.filter(
        file_attachments__in=file_attachments)
    latest = dict([
        (data['id'], data['latest_revision'])
        for data in file_attachment_histories.values('id', 'latest_revision')
    ])

    return [
        f
        for f in file_attachments
        if (not f.is_from_diff and
            f.attachment_revision == latest[f.attachment_history_id])
    ]


@check_login_required
@check_local_site_access
def review_detail(request,
                  review_request_id,
                  local_site=None,
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
        request, review_request_id, local_site)

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
    visited = None

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
        try:
            visited, visited_is_new = \
                ReviewRequestVisit.objects.get_or_create(
                    user=request.user, review_request=review_request)
            last_visited = visited.timestamp.replace(tzinfo=utc)
        except ReviewRequestVisit.DoesNotExist:
            # Somehow, this visit was seen as created but then not
            # accessible. We need to log this and then continue on.
            logging.error('Unable to get or create ReviewRequestVisit '
                          'for user "%s" on review request at %s',
                          request.user.username,
                          review_request.get_absolute_url())

        # If the review request is public and pending review and if the user
        # is logged in, mark that they've visited this review request.
        if (review_request.public and
            review_request.status == review_request.PENDING_REVIEW):
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

    # Map diffset IDs to their object.
    diffsets = review_request.get_diffsets()
    diffsets_by_id = {}

    for diffset in diffsets:
        diffsets_by_id[diffset.pk] = diffset

    # Find out if we can bail early. Generate an ETag for this.
    last_activity_time, updated_object = \
        review_request.get_last_activity(diffsets, public_reviews)

    if draft:
        draft_timestamp = draft.last_updated
    else:
        draft_timestamp = ""

    if visited:
        visibility = visited.visibility
    else:
        visibility = None

    blocks = review_request.get_blocks()

    etag = encode_etag(
       '%s:%s:%s:%s:%s:%s:%s:%s:%s:%s'
        % (request.user, last_activity_time, draft_timestamp,
           review_timestamp, review_request.last_review_activity_timestamp,
           is_rich_text_default_for_user(request.user),
           [r.pk for r in blocks],
           starred, visibility, settings.AJAX_SERIAL))

    if etag_if_none_match(request, etag):
        return HttpResponseNotModified()

    # Get the list of public ChangeDescriptions.
    #
    # We want to get the latest ChangeDescription along with this. This is
    # best done here and not in a separate SQL query.
    changedescs = list(review_request.changedescs.filter(public=True))

    if changedescs:
        # We sort from newest to oldest, so the latest one is the first.
        latest_timestamp = changedescs[0].timestamp
    else:
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
                'issue_open_count': 0,
                'has_issues': False,
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
    #
    # Note that we're fetching inactive file attachments and screenshots.
    # is because any file attachments/screenshots created after the initial
    # creation of the review request that were later removed will still need
    # to be rendered as an added file in a change box.
    file_attachments = []
    inactive_file_attachments = []
    screenshots = []
    inactive_screenshots = []

    for attachment in review_request_details.get_file_attachments():
        attachment._comments = []
        file_attachments.append(attachment)

    for attachment in review_request_details.get_inactive_file_attachments():
        attachment._comments = []
        inactive_file_attachments.append(attachment)

    for screenshot in review_request_details.get_screenshots():
        screenshot._comments = []
        screenshots.append(screenshot)

    for screenshot in review_request_details.get_inactive_screenshots():
        screenshot._comments = []
        inactive_screenshots.append(screenshot)

    file_attachment_id_map = _build_id_map(file_attachments)
    file_attachment_id_map.update(_build_id_map(inactive_file_attachments))
    screenshot_id_map = _build_id_map(screenshots)
    screenshot_id_map.update(_build_id_map(inactive_screenshots))

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
                if comment.screenshot_id in screenshot_id_map:
                    screenshot = screenshot_id_map[comment.screenshot_id]
                    comment.screenshot = screenshot
                    screenshot._comments.append(comment)
            elif isinstance(comment, FileAttachmentComment):
                if comment.file_attachment_id in file_attachment_id_map:
                    file_attachment = \
                        file_attachment_id_map[comment.file_attachment_id]
                    comment.file_attachment = file_attachment
                    file_attachment._comments.append(comment)

                diff_against_id = comment.diff_against_file_attachment_id

                if diff_against_id in file_attachment_id_map:
                    file_attachment = file_attachment_id_map[diff_against_id]
                    comment.diff_against_file_attachment = file_attachment

            uncollapse = False

            if parent_review.is_reply():
                # This is a reply to a comment. Add it to the list of replies.
                assert obj.review_id not in reviews_entry_map
                assert parent_review.base_reply_to_id in reviews_entry_map

                # If there's an entry that isn't a reply, then it's
                # orphaned. Ignore it.
                if comment.is_reply():
                    replied_comment = comment_map[comment.reply_to_id]
                    replied_comment._replies.append(comment)

                    if not parent_review.public:
                        uncollapse = True
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
                    entry['has_issues'] = True

                    if comment.issue_status == BaseComment.OPEN:
                        entry['issue_open_count'] += 1

                        if review_request.submitter == request.user:
                            uncollapse = True

            # If the box was collapsed, uncollapse it.
            if uncollapse and entry['collapsed']:
                entry['class'] = ''
                entry['collapsed'] = False

    # Sort all the reviews and ChangeDescriptions into a single list, for
    # display.
    for changedesc in changedescs:
        # Process the list of fields, in order by fieldset. These will be
        # put into groups composed of inline vs. full-width field values,
        # for render into the box.
        fields_changed_groups = []
        cur_field_changed_group = None

        fieldsets = get_review_request_fieldsets(
            include_main=True,
            include_change_entries_only=True)

        for fieldset in fieldsets:
            for field_cls in fieldset.field_classes:
                field_id = field_cls.field_id

                if field_id not in changedesc.fields_changed:
                    continue

                inline = field_cls.change_entry_renders_inline

                if (not cur_field_changed_group or
                    cur_field_changed_group['inline'] != inline):
                    # Begin a new group of fields.
                    cur_field_changed_group = {
                        'inline': inline,
                        'fields': [],
                    }
                    fields_changed_groups.append(cur_field_changed_group)

                if hasattr(field_cls, 'locals_vars'):
                    field = field_cls(review_request, request=request,
                                      locals_vars=locals())
                else:
                    field = field_cls(review_request, request=request)

                cur_field_changed_group['fields'] += \
                    field.get_change_entry_sections_html(
                        changedesc.fields_changed[field_id])

        # See if the review request has had a status change.
        status_change = changedesc.fields_changed.get('status')

        if status_change:
            assert 'new' in status_change
            new_status = status_to_string(status_change['new'][0])
        else:
            new_status = None

        # Mark as collapsed if the change is older than a newer change
        if latest_timestamp and changedesc.timestamp < latest_timestamp:
            state = 'collapsed'
            collapsed = True
        else:
            state = ''
            collapsed = False

        entries.append({
            'new_status': new_status,
            'fields_changed_groups': fields_changed_groups,
            'changedesc': changedesc,
            'timestamp': changedesc.timestamp,
            'class': state,
            'collapsed': collapsed,
        })

    entries.sort(key=lambda item: item['timestamp'])

    close_description, close_description_rich_text = \
        review_request.get_close_description()

    latest_file_attachments = _get_latest_file_attachments(file_attachments)

    siteconfig = SiteConfiguration.objects.get_current()

    context_data = make_review_request_context(request, review_request, {
        'blocks': blocks,
        'draft': draft,
        'review_request_details': review_request_details,
        'review_request_visit': visited,
        'send_email': siteconfig.get('mail_send_review_mail'),
        'entries': entries,
        'last_activity_time': last_activity_time,
        'review': pending_review,
        'request': request,
        'close_description': close_description,
        'close_description_rich_text': close_description_rich_text,
        'issues': issues,
        'has_diffs': (draft and draft.diffset_id) or len(diffsets) > 0,
        'file_attachments': latest_file_attachments,
        'all_file_attachments': file_attachments,
        'screenshots': screenshots,
    })

    response = render_to_response(template_name,
                                  RequestContext(request, context_data))
    set_etag(response, etag)

    return response


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

        * local_site
          - The LocalSite the ReviewRequest must be on, if any.

    See DiffViewerView's documentation for the accepted query parameters.
    """
    @method_decorator(check_login_required)
    @method_decorator(check_local_site_access)
    @augment_method_from(DiffViewerView)
    def dispatch(self, *args, **kwargs):
        pass

    def get(self, request, review_request_id, revision=None,
            interdiff_revision=None, local_site=None):
        """Handles GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.
        """
        review_request, response = \
            _find_review_request(request, review_request_id, local_site)

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

        latest_file_attachments = \
            _get_latest_file_attachments(file_attachments)

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

        close_description, close_description_rich_text = \
            self.review_request.get_close_description()

        context = super(ReviewsDiffViewerView, self).get_context_data(
            *args, **kwargs)

        siteconfig = SiteConfiguration.objects.get_current()

        context.update({
            'close_description': close_description,
            'close_description_rich_text': close_description_rich_text,
            'diffsets': diffsets,
            'latest_diffset': latest_diffset,
            'review': pending_review,
            'review_request_details': self.draft or self.review_request,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
            'send_email': siteconfig.get('mail_send_review_mail'),
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

            if f['force_interdiff']:
                data['force_interdiff'] = True
                data['interdiff_revision'] = f['force_interdiff_revision']

            files.append(data)

        context['diff_context']['files'] = files

        return context


@check_login_required
@check_local_site_access
def raw_diff(request, review_request_id, revision=None, local_site=None):
    """
    Displays a raw diff of all the filediffs in a diffset for the
    given review request.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    draft = review_request.get_draft(request.user)
    diffset = _query_for_diff(review_request, request.user, revision, draft)

    tool = review_request.repository.get_scmtool()
    data = tool.get_parser('').raw_diff(diffset)

    resp = HttpResponse(data, content_type='text/x-patch')

    if diffset.name == 'diff':
        filename = "rb%d.patch" % review_request.display_id
    else:
        filename = six.text_type(diffset.name).encode('ascii', 'ignore')

        # Content-Disposition headers containing commas break on Chrome 16 and
        # newer. To avoid this, replace any commas in the filename with an
        # underscore. Was bug 3704.
        filename = filename.replace(',', '_')

    resp['Content-Disposition'] = 'attachment; filename=%s' % filename
    set_last_modified(resp, diffset.timestamp)

    return resp


@check_login_required
@check_local_site_access
def comment_diff_fragments(
    request,
    review_request_id,
    comment_ids,
    template_name='reviews/load_diff_comment_fragments.js',
    comment_template_name='reviews/diff_comment_fragment.html',
    error_template_name='diffviewer/diff_fragment_error.html',
    local_site=None):
    """
    Returns the fragment representing the parts of a diff referenced by the
    specified list of comment IDs. This is used to allow batch lazy-loading
    of these diff fragments based on filediffs, since they may not be cached
    and take time to generate.
    """
    comments = get_list_or_404(Comment, pk__in=comment_ids.split(","))
    latest_timestamp = get_latest_timestamp(comment.timestamp
                                            for comment in comments)

    etag = encode_etag(
        '%s:%s:%s'
        % (comment_ids, latest_timestamp, settings.TEMPLATE_SERIAL))

    if etag_if_none_match(request, etag):
        response = HttpResponseNotModified()
    else:
        # While we don't actually need the review request, we still want to do
        # this lookup in order to get the permissions checking.
        review_request, response = \
            _find_review_request(request, review_request_id, local_site)

        if not review_request:
            return response

        lines_of_context = request.GET.get('lines_of_context', '0,0')
        container_prefix = request.GET.get('container_prefix')

        try:
            lines_of_context = [int(i) for i in lines_of_context.split(',')]

            # Ensure that we have 2 values for lines_of_context. If only one is
            # given, assume it is both the before and after context. If more than
            # two are given, only consider the first two. If somehow we get no
            # lines of context value, we will default to [0, 0].

            if len(lines_of_context) == 1:
                lines_of_context.append(lines_of_context[0])
            elif len(lines_of_context) > 2:
                lines_of_context = lines_of_context[0:2]
            elif len(lines_of_context) == 0:
                raise ValueError
        except ValueError:
            lines_of_context = [0, 0]

        context = RequestContext(request, {
            'comment_entries': [],
            'container_prefix': container_prefix,
            'queue_name': request.GET.get('queue'),
            'show_controls': request.GET.get('show_controls', False),
        })

        had_error, context['comment_entries'] = (
            build_diff_comment_fragments(
                comments,
                context,
                comment_template_name,
                error_template_name,
                lines_of_context=lines_of_context,
                show_controls='draft' not in container_prefix))

        page_content = render_to_string(template_name, context)

        response = HttpResponse(
            page_content,
            content_type='application/javascript')

        if had_error:
            return response

        set_etag(response, etag)

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

        * local_site
          - The LocalSite the ReviewRequest must be on, if any.

    See DiffFragmentView's documentation for the accepted query parameters.
    """
    @method_decorator(check_login_required)
    @method_decorator(check_local_site_access)
    @augment_method_from(DiffFragmentView)
    def dispatch(self, *args, **kwargs):
        pass

    def process_diffset_info(self, review_request_id, revision,
                             interdiff_revision=None, local_site=None,
                             *args, **kwargs):
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        If the review request cannot be accessed by the user, an HttpResponse
        will be returned instead.
        """
        self.review_request, response = \
            _find_review_request(self.request, review_request_id, local_site)

        if not self.review_request:
            return response

        user = self.request.user
        draft = self.review_request.get_draft(user)

        if interdiff_revision is not None:
            interdiffset = _query_for_diff(self.review_request, user,
                                           interdiff_revision, draft)
        else:
            interdiffset = None

        diffset = _query_for_diff(self.review_request, user, revision, draft)

        return super(ReviewsDiffFragmentView, self).process_diffset_info(
            diffset_or_id=diffset,
            interdiffset_or_id=interdiffset,
            **kwargs)

    def create_renderer(self, diff_file, *args, **kwargs):
        """Creates the DiffRenderer for this fragment.

        This will augment the renderer for binary files by looking up
        file attachments, if review UIs are involved, disabling caching.
        """
        renderer = super(ReviewsDiffFragmentView, self).create_renderer(
            diff_file=diff_file, *args, **kwargs)

        if diff_file['binary']:
            # Determine the file attachments to display in the diff viewer,
            # if any.
            filediff = diff_file['filediff']
            interfilediff = diff_file['interfilediff']

            orig_attachment = None
            modified_attachment = None

            if diff_file['force_interdiff']:
                orig_attachment = self._get_diff_file_attachment(filediff)
                modified_attachment = \
                    self._get_diff_file_attachment(interfilediff)
            else:
                modified_attachment = self._get_diff_file_attachment(filediff)

                if not diff_file['is_new_file']:
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

        renderer.extra_context.update(
            self._get_download_links(renderer, diff_file))

        return renderer

    def get_context_data(self, **kwargs):
        return {
            'review_request': self.review_request,
        }

    def _get_download_links(self, renderer, diff_file):
        if diff_file['binary']:
            orig_attachment = \
                renderer.extra_context['orig_diff_file_attachment']
            modified_attachment = \
                renderer.extra_context['modified_diff_file_attachment']

            if orig_attachment:
                download_orig_url = orig_attachment.get_absolute_url()
            else:
                download_orig_url = None

            if modified_attachment:
                download_modified_url = modified_attachment.get_absolute_url()
            else:
                download_modified_url = None
        else:
            filediff = diff_file['filediff']
            interfilediff = diff_file['interfilediff']
            diffset = filediff.diffset

            if interfilediff:
                orig_url_name = 'download-modified-file'
                modified_revision = interfilediff.diffset.revision
                modified_filediff_id = interfilediff.pk
            else:
                orig_url_name = 'download-orig-file'
                modified_revision = diffset.revision
                modified_filediff_id = filediff.pk

            download_orig_url = local_site_reverse(
                orig_url_name,
                request=self.request,
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': diffset.revision,
                    'filediff_id': filediff.pk,
                })

            download_modified_url = local_site_reverse(
                'download-modified-file',
                request=self.request,
                kwargs={
                    'review_request_id': self.review_request.display_id,
                    'revision': modified_revision,
                    'filediff_id': modified_filediff_id,
                })

        return {
            'download_orig_url': download_orig_url,
            'download_modified_url': download_modified_url,
        }

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
@check_local_site_access
def preview_review_request_email(
    request,
    review_request_id,
    format,
    text_template_name='notifications/review_request_email.txt',
    html_template_name='notifications/review_request_email.html',
    changedesc_id=None,
    local_site=None):
    """
    Previews the e-mail message that would be sent for an initial
    review request or an update.

    This is mainly used for debugging.
    """
    if not settings.DEBUG:
        raise Http404

    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    extra_context = {}

    if changedesc_id:
        changedesc = get_object_or_404(review_request.changedescs,
                                       pk=changedesc_id)
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
    ), content_type=mimetype)


@check_login_required
@check_local_site_access
def preview_review_email(request, review_request_id, review_id, format,
                         text_template_name='notifications/review_email.txt',
                         html_template_name='notifications/review_email.html',
                         extra_context={},
                         local_site=None):
    """
    Previews the e-mail message that would be sent for a review of a
    review request.

    This is mainly used for debugging.
    """
    if not settings.DEBUG:
        raise Http404

    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

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
        content_type=mimetype)


@check_login_required
@check_local_site_access
def preview_reply_email(request, review_request_id, review_id, reply_id,
                        format,
                        text_template_name='notifications/reply_email.txt',
                        html_template_name='notifications/reply_email.html',
                        local_site=None):
    """
    Previews the e-mail message that would be sent for a reply to a
    review of a review request.

    This is mainly used for debugging.
    """
    if not settings.DEBUG:
        raise Http404

    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

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
        content_type=mimetype)


@check_login_required
@check_local_site_access
def review_file_attachment(request, review_request_id, file_attachment_id,
                           file_attachment_diff_id=None, local_site=None):
    """Displays a file attachment with a review UI."""
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    draft = review_request.get_draft(request.user)

    # Make sure the attachment returned is part of either the review request
    # or an accessible draft.
    review_request_q = (Q(review_request=review_request) |
                        Q(inactive_review_request=review_request))

    if draft:
        review_request_q |= Q(drafts=draft) | Q(inactive_drafts=draft)

    file_attachment = get_object_or_404(
        FileAttachment,
        Q(pk=file_attachment_id) & review_request_q)

    review_ui = file_attachment.review_ui

    if not review_ui:
        review_ui = FileAttachmentReviewUI(review_request, file_attachment)

    if file_attachment_diff_id:
        file_attachment_revision = get_object_or_404(
            FileAttachment,
            Q(pk=file_attachment_diff_id) &
            Q(attachment_history=file_attachment.attachment_history) &
            review_request_q)
        review_ui.set_diff_against(file_attachment_revision)

    try:
        is_enabled_for = review_ui.is_enabled_for(
            user=request.user,
            review_request=review_request,
            file_attachment=file_attachment)
    except Exception as e:
        logging.error('Error when calling is_enabled_for for '
                      'FileAttachmentReviewUI %r: %s',
                      review_ui, e, exc_info=1)
        is_enabled_for = False

    if review_ui and is_enabled_for:
        return review_ui.render_to_response(request)
    else:
        raise Http404


@check_login_required
@check_local_site_access
def view_screenshot(request, review_request_id, screenshot_id,
                    local_site=None):
    """
    Displays a screenshot, along with any comments that were made on it.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    draft = review_request.get_draft(request.user)

    # Make sure the screenshot returned is part of either the review request
    # or an accessible draft.
    review_request_q = (Q(review_request=review_request) |
                        Q(inactive_review_request=review_request))

    if draft:
        review_request_q |= Q(drafts=draft) | Q(inactive_drafts=draft)

    screenshot = get_object_or_404(Screenshot,
                                   Q(pk=screenshot_id) & review_request_q)
    review_ui = LegacyScreenshotReviewUI(review_request, screenshot)

    return review_ui.render_to_response(request)


@check_login_required
@check_local_site_access
def user_infobox(request, username,
                 template_name='accounts/user_infobox.html',
                 local_site=None):
    """Displays a user info popup.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """
    user = get_object_or_404(User, username=username)
    show_profile = user.is_profile_visible(request.user)

    etag = encode_etag(':'.join([
        user.first_name,
        user.last_name,
        user.email,
        six.text_type(user.last_login),
        six.text_type(settings.TEMPLATE_SERIAL),
        six.text_type(show_profile)
    ]))

    if etag_if_none_match(request, etag):
        return HttpResponseNotModified()

    response = render_to_response(template_name, RequestContext(request, {
        'show_profile': show_profile,
        'requested_user': user,
    }))
    set_etag(response, etag)

    return response


def bug_url(request, review_request_id, bug_id, local_site=None):
    """Redirects user to bug tracker issue page."""
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    # Need to create a custom HttpResponse because a non-HTTP url scheme will
    # cause HttpResponseRedirect to fail with a "Disallowed Redirect".
    response = HttpResponse(status=302)
    response['Location'] = review_request.repository.bug_tracker % bug_id
    return response


def bug_infobox(request, review_request_id, bug_id,
                template_name='reviews/bug_infobox.html',
                local_site=None):
    """Displays a bug info popup.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    repository = review_request.repository

    bug_tracker = repository.bug_tracker_service
    if not bug_tracker:
        return HttpResponseNotFound(_('Unable to find bug tracker service'))

    if not isinstance(bug_tracker, BugTracker):
        return HttpResponseNotFound(
            _('Bug tracker %s does not support metadata') % bug_tracker.name)

    bug_info = bug_tracker.get_bug_info(repository, bug_id)
    bug_description = bug_info['description']
    bug_summary = bug_info['summary']
    bug_status = bug_info['status']

    if not bug_summary and not bug_description:
        return HttpResponseNotFound(
            _('No bug metadata found for bug %(bug_id)s on bug tracker '
              '%(bug_tracker)s') % {
                'bug_id': bug_id,
                'bug_tracker': bug_tracker.name,
            })

    # Don't do anything for single newlines, but treat two newlines as a
    # paragraph break.
    escaped_description = escape(bug_description).replace('\n\n', '<br/><br/>')

    return render_to_response(template_name, RequestContext(request, {
        'bug_id': bug_id,
        'bug_description': mark_safe(escaped_description),
        'bug_status': bug_status,
        'bug_summary': bug_summary
    }))


def _download_diff_file(modified, request, review_request_id, revision,
                        filediff_id, local_site=None):
    """Downloads an original or modified file from a diff.

    This will fetch the file from a FileDiff, optionally patching it,
    and return the result as an HttpResponse.
    """
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    draft = review_request.get_draft(request.user)
    diffset = _query_for_diff(review_request, request.user, revision, draft)
    filediff = get_object_or_404(diffset.files, pk=filediff_id)
    encoding_list = diffset.repository.get_encoding_list()
    data = get_original_file(filediff, request, encoding_list)

    if modified:
        data = get_patched_file(data, filediff, request)

    data = convert_to_unicode(data, encoding_list)[1]

    return HttpResponse(data, content_type='text/plain; charset=utf-8')


@check_login_required
@check_local_site_access
def download_orig_file(*args, **kwargs):
    """Downloads an original file from a diff."""
    return _download_diff_file(False, *args, **kwargs)


@check_login_required
@check_local_site_access
def download_modified_file(*args, **kwargs):
    """Downloads a modified file from a diff."""
    return _download_diff_file(True, *args, **kwargs)
