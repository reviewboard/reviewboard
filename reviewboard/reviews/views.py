from __future__ import unicode_literals

import logging
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
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
from django.utils.html import escape, format_html_join
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.dates import get_latest_timestamp
from djblets.util.decorators import augment_method_from
from djblets.util.http import (encode_etag, set_last_modified,
                               set_etag, etag_if_none_match)
from djblets.views.generic.base import PrePostDispatchViewMixin
from djblets.views.generic.etag import ETagViewMixin

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)
from reviewboard.accounts.mixins import CheckLoginRequiredViewMixin
from reviewboard.accounts.models import ReviewRequestVisit, Profile
from reviewboard.attachments.models import (FileAttachment,
                                            get_latest_file_attachments)
from reviewboard.diffviewer.diffutils import (convert_to_unicode,
                                              get_file_chunks_in_range,
                                              get_last_header_before_line,
                                              get_last_line_number_in_diff,
                                              get_original_file,
                                              get_patched_file)
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import (DiffFragmentView,
                                          DiffViewerView,
                                          DownloadPatchErrorBundleView,
                                          exception_traceback_string)
from reviewboard.hostingsvcs.bugtracker import BugTracker
from reviewboard.notifications.email.decorators import preview_email
from reviewboard.notifications.email.message import (
    prepare_reply_published_mail,
    prepare_review_published_mail,
    prepare_review_request_mail)
from reviewboard.notifications.email.views import BasePreviewEmailView
from reviewboard.reviews.ui.screenshot import LegacyScreenshotReviewUI
from reviewboard.reviews.context import (comment_counts,
                                         diffsets_with_comments,
                                         has_comments_in_diffsets_excluding,
                                         interdiffs_with_comments,
                                         make_review_request_context)
from reviewboard.reviews.detail import (ChangeEntry,
                                        InitialStatusUpdatesEntry,
                                        ReviewEntry,
                                        ReviewRequestPageData)
from reviewboard.reviews.features import status_updates_feature
from reviewboard.reviews.markdown_utils import is_rich_text_default_for_user
from reviewboard.reviews.models import (Comment,
                                        Review,
                                        ReviewRequest,
                                        Screenshot)
from reviewboard.reviews.ui.base import FileAttachmentReviewUI
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository
from reviewboard.site.decorators import check_local_site_access
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


class ReviewRequestViewMixin(CheckLoginRequiredViewMixin,
                             CheckLocalSiteAccessViewMixin,
                             PrePostDispatchViewMixin):
    """Common functionality for all review request-related pages.

    This performs checks to ensure that the user has access to the page,
    returning an error page if not. It also provides common functionality
    for fetching a review request for the given page, returning suitable
    context for the template, and generating an image used to represent
    the site when posting to social media sites.
    """

    permission_denied_template_name = \
        'reviews/review_request_permission_denied.html'

    def pre_dispatch(self, request, review_request_id, *args, **kwargs):
        """Look up objects and permissions before dispatching the request.

        This will first look up the review request, returning an error page
        if it's not accessible. It will then store the review request before
        calling the handler for the HTTP request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            review_request_id (int):
                The ID of the review request being accessed.

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (dict):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client, if there's
            a Permission Denied.
        """
        self.review_request = self.get_review_request(
            review_request_id=review_request_id,
            local_site=self.local_site)

        if not self.review_request.is_accessible_by(request.user):
            return self.render_permission_denied(request)

        return None

    def render_permission_denied(self, request):
        """Render a Permission Denied page.

        This will be shown to the user if they're not able to view the
        review request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        response = render_to_response(self.permission_denied_template_name,
                                      RequestContext(request))
        response.status_code = 403

        return response

    def get_review_request(self, review_request_id, local_site=None):
        """Return the review request for the given display ID.

        Args:
            review_request_id (int):
                The review request's display ID.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site the review request is on.

        Returns:
            reviewboard.reviews.models.review_request.ReviewRequest:
            The review request for the given display ID and Local Site.

        Raises:
            django.http.Http404:
                The review request could not be found.
        """
        q = ReviewRequest.objects.all()

        if local_site:
            q = q.filter(local_site=local_site,
                         local_id=review_request_id)
        else:
            q = q.filter(pk=review_request_id)

        q = q.select_related('submitter', 'repository')

        return get_object_or_404(q)

    def get_diff(self, revision=None, draft=None):
        """Return a diff on the review request matching the given criteria.

        If a draft is provided, and ``revision`` is either ``None`` or matches
        the revision on the draft's DiffSet, that DiffSet will be returned.

        Args:
            revision (int, optional):
                The revision of the diff to retrieve. If not provided, the
                latest DiffSet will be returned.

            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The draft of the review request.

        Returns:
            reviewboard.diffviewer.models.DiffSet:
            The resulting DiffSet.

        Raises:
            django.http.Http404:
                The diff does not exist.
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

        query = Q(history=self.review_request.diffset_history_id)

        # Grab a revision if requested.
        if revision is not None:
            query = query & Q(revision=revision)

        try:
            return DiffSet.objects.filter(query).latest()
        except DiffSet.DoesNotExist:
            raise Http404

    def get_social_page_image_url(self, file_attachments):
        """Return the URL to an image used for social media sharing.

        This will look for the first attachment in a list of attachments that
        can be used to represent the review request on social media sites and
        chat services. If a suitable attachment is found, its URL will be
        returned.

        Args:
            file_attachments (list of reviewboard.attachments.models.
                              FileAttachment):
                A list of file attachments used on a review request.

        Returns:
            unicode:
            The URL to the first image file attachment, if found, or ``None``
            if no suitable attachments were found.
        """
        for file_attachment in file_attachments:
            if file_attachment.mimetype.startswith('image/'):
                return file_attachment.get_absolute_url()

        return None

    def get_context_data(self, **kwargs):
        """Return context data for the template.

        This ensures the context is wrapped in a
        :py:class:`django.template.RequestContext`, which is needed when
        constructing parts of the context for these pages.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            django.template.RequestContext:
            The resulting context data for the template.
        """
        return RequestContext(
            self.request,
            super(ReviewRequestViewMixin, self).get_context_data(**kwargs))


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
                'requires_basedir': not scmtool.diffs_use_absolute_paths,
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


class ReviewRequestDetailView(ReviewRequestViewMixin, ETagViewMixin,
                              TemplateView):
    """A view for the main review request page.

    This page shows information on the review request, all the reviews and
    issues that have been posted, and the status updates made on uploaded
    changes.
    """

    template_name = 'reviews/review_detail.html'

    def __init__(self, **kwargs):
        """Initialize a view for the request.

        Args:
            **kwargs (dict):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super(ReviewRequestDetailView, self).__init__(**kwargs)

        self.status_updates_enabled = None
        self.data = None
        self.visited = None
        self.last_visited = None
        self.blocks = None
        self.last_activity_time = None
        self.initial_status_entry = None

    def get_etag_data(self, request, *args, **kwargs):
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the template context.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passsed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            unicode:
            The ETag for the page.
        """
        review_request = self.review_request
        local_site = review_request.local_site

        # Determine which features are enabled.
        self.status_updates_enabled = status_updates_feature.is_enabled(
            local_site=local_site)

        # Begin building data for the contents of the page. This will include
        # the reviews, change descriptions, and other content shown on the
        # page.
        data = ReviewRequestPageData(review_request, request)
        self.data = data

        data.query_data_pre_etag()

        # Track the visit to this review request, so the dashboard can
        # reflect whether there are new updates.
        self.visited, self.last_visited = self.track_review_request_visit()

        self.blocks = review_request.get_blocks()

        # Prepare data used in both the page and the ETag.
        starred = self.is_review_request_starred()

        self.last_activity_time, updated_object = \
            review_request.get_last_activity(data.diffsets, data.reviews)
        etag_timestamp = self.last_activity_time

        if self.status_updates_enabled:
            for status_update in data.status_updates:
                if status_update.timestamp > etag_timestamp:
                    etag_timestamp = status_update.timestamp

        if data.draft:
            draft_timestamp = data.draft.last_updated
        else:
            draft_timestamp = ''

        return ':'.join(six.text_type(value) for value in (
            request.user,
            etag_timestamp,
            draft_timestamp,
            data.latest_review_timestamp,
            review_request.last_review_activity_timestamp,
            is_rich_text_default_for_user(request.user),
            [r.pk for r in self.blocks],
            starred,
            self.visited and self.visited.visibility,
            settings.AJAX_SERIAL,
        ))

    def track_review_request_visit(self):
        """Track a visit to the review request.

        If the user is authenticated, their visit to this page will be
        recorded. That information is used to provide an indicator in the
        dashboard when a review request is later updated.

        Returns:
            tuple:
            A tuple containing the following items:

            1. The resulting
               :py:class:`~reviewboard.accounts.models.ReviewRequestVisit`,
               if the user is authenticated and the visit could be returned or
               created.

            2. The timestamp when the user had last visited the site, prior to
               this visit (or 0 if they haven't).
        """
        user = self.request.user
        visited = None
        last_visited = 0

        if user.is_authenticated():
            review_request = self.review_request

            try:
                visited, visited_is_new = \
                    ReviewRequestVisit.objects.get_or_create(
                        user=user, review_request=review_request)
                last_visited = visited.timestamp.replace(tzinfo=utc)
            except ReviewRequestVisit.DoesNotExist:
                # Somehow, this visit was seen as created but then not
                # accessible. We need to log this and then continue on.
                logging.error('Unable to get or create ReviewRequestVisit '
                              'for user "%s" on review request at %s',
                              user.username,
                              review_request.get_absolute_url())
                visited = None

            # If the review request is public and pending review and if the user
            # is logged in, mark that they've visited this review request.
            if (visited and
                review_request.public and
                review_request.status == review_request.PENDING_REVIEW):
                visited.timestamp = timezone.now()
                visited.save()

        return visited, last_visited

    def is_review_request_starred(self):
        """Return whether the review request has been starred by the user.

        Returns:
            bool:
            ``True`` if the user has starred the review request.
            ``False`` if they have not.
        """
        user = self.request.user

        if user.is_authenticated():
            try:
                return (
                    user.get_profile().starred_review_requests
                    .filter(pk=self.review_request.pk)
                    .exists()
                )
            except Profile.DoesNotExist:
                pass

        return False

    def get_entries(self):
        """Return the entries to show on the page.

        Each entry represents a review, change description, or status update
        to display.

        Returns:
            list of reviewboard.reviews.detail.BaseReviewRequestPageEntry:
            The list of entries to show on the page.
        """
        # Convert some frequently-accessed state to local variables for faster
        # access.
        status_updates_enabled = self.status_updates_enabled
        review_request = self.review_request
        last_visited = self.last_visited
        request = self.request
        data = self.data

        entries = []
        reviews_entry_map = {}
        changedescs_entry_map = {}

        data.query_data_post_etag()

        # Now that we have the list of public reviews and all that metadata,
        # being processing them and adding entries for display in the page.
        for review in data.reviews:
            if (review.public and
                not review.is_reply() and
                not (status_updates_enabled and
                     hasattr(review, 'status_update'))):
                # Mark as collapsed if the review is older than the latest
                # change, assuming there's no reply newer than last_visited.
                latest_reply = \
                    data.latest_timestamps_by_review_id.get(review.pk)

                collapsed = (
                    review.timestamp < data.latest_changedesc_timestamp and
                    not (latest_reply and
                         last_visited and
                         last_visited < latest_reply))

                entry = ReviewEntry(request, review_request, review, collapsed,
                                    data)
                reviews_entry_map[review.pk] = entry
                entries.append(entry)

        # Add entries for the change descriptions.
        for changedesc in data.changedescs:
            # Mark as collapsed if the change is older than a newer change.
            collapsed = (changedesc.timestamp <
                         data.latest_changedesc_timestamp)

            entry = ChangeEntry(request, review_request, changedesc, collapsed,
                                data)
            changedescs_entry_map[changedesc.id] = entry
            entries.append(entry)

        if status_updates_enabled:
            self.initial_status_entry = InitialStatusUpdatesEntry(
                review_request, collapsed=(len(data.changedescs) > 0),
                data=data)

            for update in data.status_updates:
                if update.change_description_id is not None:
                    entry = changedescs_entry_map[update.change_description_id]
                else:
                    entry = self.initial_status_entry

                entry.add_update(update)

                if update.review_id is not None:
                    reviews_entry_map[update.review_id] = entry

        # Now that we have entries for all the reviews, go through all the
        # comments and add them to those entries.
        for comment in data.comments:
            review = comment.review_obj

            if review.is_reply():
                # This is a reply to a comment.
                base_reply_to_id = comment.review_obj.base_reply_to_id

                assert review.pk not in reviews_entry_map
                assert base_reply_to_id in reviews_entry_map

                # Make sure that any review boxes containing draft replies are
                # always expanded.
                if comment.is_reply() and not review.public:
                    reviews_entry_map[base_reply_to_id].collapsed = False
            elif review.public:
                # This is a comment on a public review.
                assert review.id in reviews_entry_map

                entry = reviews_entry_map[review.id]
                entry.add_comment(comment._type, comment)

        if status_updates_enabled:
            self.initial_status_entry.finalize()

            for entry in entries:
                entry.finalize()

        # Finally, sort all the entries (reviews and change descriptions) by
        # their timestamp.
        entries.sort(key=lambda item: item.timestamp)

        return entries

    def get_context_data(self, **kwargs):
        """Return data for the template.

        This will return information on the review request, the entries to
        show, file attachments, issues, metadata to use when sharing the
        review request on social networks, and everything else needed to
        render the page.

        Args:
            **kwargs (dict):
                Additional keyword arguments passed to the view.

        Returns:
            django.template.RequestContext:
            Context data for the template.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        review_request = self.review_request
        request = self.request
        data = self.data

        entries = self.get_entries()
        review = review_request.get_pending_review(request.user)
        close_description, close_description_rich_text = \
            review_request.get_close_description()
        file_attachments = \
            get_latest_file_attachments(data.active_file_attachments)
        social_page_image_url = self.get_social_page_image_url(
            file_attachments)

        context = \
            super(ReviewRequestDetailView, self).get_context_data(**kwargs)
        context.update(make_review_request_context(request, review_request))
        context.update({
            'blocks': self.blocks,
            'draft': data.draft,
            'review_request_details': data.review_request_details,
            'review_request_visit': self.visited,
            'send_email': siteconfig.get('mail_send_review_mail'),
            'initial_status_entry': self.initial_status_entry,
            'entries': entries,
            'last_activity_time': self.last_activity_time,
            'review': review,
            'request': request,
            'close_description': close_description,
            'close_description_rich_text': close_description_rich_text,
            'issue_counts': data.issue_counts,
            'issues': data.issues,
            'file_attachments': file_attachments,
            'all_file_attachments': data.all_file_attachments,
            'screenshots': data.active_screenshots,
            'social_page_image_url': social_page_image_url,
            'social_page_title': (
                'Review Request #%s: %s'
                % (review_request.display_id, review_request.summary)
            ),
        })

        return context


class ReviewsDiffViewerView(ReviewRequestViewMixin, DiffViewerView):
    """Renders the diff viewer for a review request.

    This wraps the base
    :py:class:`~reviewboard.diffviewer.views.DiffViewerView` to display a diff
    for the given review request and the given diff revision or range.

    The view expects the following parameters to be provided:

    ``review_request_id``:
        The ID of the ReviewRequest containing the diff to render.

    The following may also be provided:

    ``revision``:
        The DiffSet revision to render.

    ``interdiff_revision``:
        The second DiffSet revision in an interdiff revision range.

    ``local_site``:
        The LocalSite the ReviewRequest must be on, if any.

    See :py:class:`~reviewboard.diffviewer.views.DiffViewerView`'s
    documentation for the accepted query parameters.
    """

    def __init__(self, **kwargs):
        """Initialize a view for the request.

        Args:
            **kwargs (dict):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super(ReviewsDiffViewerView, self).__init__(**kwargs)

        self.draft = None
        self.diffset = None
        self.interdiffset = None

    def get(self, request, revision=None, interdiff_revision=None, *args,
            **kwargs):
        """Handle HTTP GET requests for this view.

        This will look up the review request and DiffSets, given the
        provided information, and pass them to the parent class for rendering.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int, optional):
                The revision of the diff to view. This defaults to the latest
                diff.

            interdiff_revision (int, optional):
                The revision to use for an interdiff, if viewing an interdiff.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request

        self.draft = review_request.get_draft(request.user)
        self.diffset = self.get_diff(revision, self.draft)

        if interdiff_revision and interdiff_revision != revision:
            # An interdiff revision was specified. Try to find a matching
            # diffset.
            self.interdiffset = self.get_diff(interdiff_revision, self.draft)

        return super(ReviewsDiffViewerView, self).get(
            request=request,
            diffset=self.diffset,
            interdiffset=self.interdiffset,
            *args,
            **kwargs)

    def get_context_data(self, **kwargs):
        """Return additional context data for the template.

        This provides some additional data used for rendering the diff
        viewer. This data is more specific to the reviewing functionality,
        as opposed to the data calculated by
        :py:meth:`DiffViewerView.get_context_data
        <reviewboard.diffviewer.views.DiffViewerView.get_context_data>`
        which is more focused on the actual diff.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.template.RequestContext:
            Context data used to render the template.
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

        review_request_details = self.draft or self.review_request

        file_attachments = list(review_request_details.get_file_attachments())
        screenshots = list(review_request_details.get_screenshots())

        latest_file_attachments = get_latest_file_attachments(file_attachments)
        social_page_image_url = self.get_social_page_image_url(
            latest_file_attachments)

        # Compute the lists of comments based on filediffs and interfilediffs.
        # We do this using the 'through' table so that we can select_related
        # the reviews and comments.
        comments = {}
        q = Comment.review.related.field.rel.through.objects.filter(
            review__review_request=self.review_request)
        q = q.select_related()

        for obj in q:
            comment = obj.comment
            comment.review_obj = obj.review
            key = (comment.filediff_id, comment.interfilediff_id)
            comments.setdefault(key, []).append(comment)

        close_description, close_description_rich_text = \
            self.review_request.get_close_description()

        siteconfig = SiteConfiguration.objects.get_current()

        context = super(ReviewsDiffViewerView, self).get_context_data(**kwargs)
        context.update({
            'close_description': close_description,
            'close_description_rich_text': close_description_rich_text,
            'diffsets': diffsets,
            'latest_diffset': latest_diffset,
            'review': pending_review,
            'review_request_details': review_request_details,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
            'send_email': siteconfig.get('mail_send_review_mail'),
            'social_page_image_url': social_page_image_url,
            'social_page_title': (
                'Diff for Review Request #%s: %s'
                % (self.review_request.display_id,
                   review_request_details.summary)
            ),
        })
        context.update(make_review_request_context(self.request,
                                                   self.review_request,
                                                   is_diff_view=True))

        diffset_pair = context['diffset_pair']
        diff_context = context['diff_context']

        diff_context.update({
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
        diff_context['revision'].update({
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
                'id': filediff.pk,
                'depot_filename': f['depot_filename'],
                'dest_filename': f['dest_filename'],
                'dest_revision': f['dest_revision'],
                'revision': f['revision'],
                'filediff': {
                    'id': filediff.pk,
                    'revision': filediff.diffset.revision,
                },
                'index': f['index'],
                'comment_counts': comment_counts(self.request.user, comments,
                                                 filediff, interfilediff),
            }

            if interfilediff:
                data['interfilediff'] = {
                    'id': interfilediff.pk,
                    'revision': interfilediff.diffset.revision,
                }

            if f['force_interdiff']:
                data['force_interdiff'] = True
                data['interdiff_revision'] = f['force_interdiff_revision']

            files.append(data)

        diff_context['files'] = files

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
    review_request, response = \
        _find_review_request(request, review_request_id, local_site)

    if not review_request:
        return response

    q = (Q(pk__in=comment_ids.split(',')) &
         Q(review__review_request=review_request))

    if request.user.is_authenticated():
        q &= (Q(review__public=True) | Q(review__user=request.user))
    else:
        q &= Q(review__public=True)

    comments = get_list_or_404(Comment, q)

    latest_timestamp = get_latest_timestamp(comment.timestamp
                                            for comment in comments)

    etag = encode_etag(
        '%s:%s:%s'
        % (comment_ids, latest_timestamp, settings.TEMPLATE_SERIAL))

    if etag_if_none_match(request, etag):
        response = HttpResponseNotModified()
    else:
        lines_of_context = request.GET.get('lines_of_context', '0,0')
        container_prefix = request.GET.get('container_prefix')

        try:
            lines_of_context = [int(i) for i in lines_of_context.split(',')]

            # Ensure that we have 2 values for lines_of_context. If only one is
            # given, assume it is both the before and after context. If more
            # than two are given, only consider the first two. If somehow we
            # get no lines of context value, we will default to [0, 0].

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
                show_controls=(container_prefix and
                               'draft' not in container_prefix)))

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

        * chunk_index
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


class ReviewsDownloadPatchErrorBundleView(DownloadPatchErrorBundleView,
                                          ReviewsDiffFragmentView):
    """A view to download the patch error bundle.

    This view allows users to download a bundle containing data to help debug
    issues when a patch fails to apply. The bundle will contain the diff, the
    original file (as returned by the SCMTool), and the rejects file, if
    applicable.
    """


class PreviewReviewRequestEmailView(ReviewRequestViewMixin,
                                    BasePreviewEmailView):
    """Display a preview of an e-mail for a review request.

    This can be used to see what an HTML or plain text e-mail will look like
    for a newly-posted review request or an update to a review request.
    """

    build_email = staticmethod(prepare_review_request_mail)

    def get_email_data(self, request, changedesc_id=None, *args, **kwargs):
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            changedesc_id (int, optional):
                The ID of a change description used when previewing a
                Review Request Updated e-mail.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        close_type = None

        if changedesc_id:
            changedesc = get_object_or_404(self.review_request.changedescs,
                                           pk=changedesc_id)
            user = changedesc.get_user(self.review_request)

            if 'status' in changedesc.fields_changed:
                close_type = changedesc.fields_changed['status']['new'][0]
        else:
            changedesc = None
            user = self.review_request.submitter

        return {
            'user': user,
            'review_request': self.review_request,
            'changedesc': changedesc,
            'close_type': close_type,
        }


class PreviewReviewEmailView(ReviewRequestViewMixin, BasePreviewEmailView):
    """Display a preview of an e-mail for a review.

    This can be used to see what an HTML or plain text e-mail will look like
    for a review.
    """

    build_email = staticmethod(prepare_review_published_mail)

    def get_email_data(self, request, review_id, *args, **kwargs):
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            review_id (int):
                The ID of the review to preview.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        review = get_object_or_404(Review,
                                   pk=review_id,
                                   review_request=self.review_request)

        return {
            'user': review.user,
            'review': review,
            'review_request': self.review_request,
            'to_submitter_only': False,
            'request': request,
        }


class PreviewReplyEmailView(ReviewRequestViewMixin, BasePreviewEmailView):
    """Display a preview of an e-mail for a reply to a review.

    This can be used to see what an HTML or plain text e-mail will look like
    for a reply to a review.
    """

    build_email = staticmethod(prepare_reply_published_mail)

    def get_email_data(self, request, review_id, reply_id, *args, **kwargs):
        """Return data used for the e-mail builder.

        The data returned will be passed to :py:attr:`build_email` to handle
        rendering the e-mail.

        This can also return a :py:class:`~django.http.HttpResponse`, which
        is useful for returning errors.

        Args:
            request (django.http.HttpResponse):
                The HTTP response from the client.

            review_id (int):
                The ID of the review the reply is for.

            reply_id (int):
                The ID of the reply to preview.

            *args (tuple):
                Additional positional arguments passed to the handler.

            **kwargs (dict):
                Additional keyword arguments passed to the handler.

        Returns:
            object:
            The dictionary data to pass as keyword arguments to
            :py:attr:`build_email`, or an instance of
            :py:class:`~django.http.HttpResponse` to immediately return to
            the client.
        """
        review = get_object_or_404(Review,
                                   pk=review_id,
                                   review_request=self.review_request)
        reply = get_object_or_404(Review, pk=reply_id, base_reply_to=review)

        return {
            'user': reply.user,
            'reply': reply,
            'review': review,
            'review_request': self.review_request,
        }


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


@check_login_required
@check_local_site_access
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


class ReviewRequestInfoboxView(ReviewRequestViewMixin, TemplateView):
    """Display a review request info popup.

    This produces the information needed to be displayed in a summarized
    information box upon hovering over a link to a review request.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """

    template_name = 'reviews/review_request_infobox.html'

    MAX_REVIEWS = 3

    def get_context_data(self, **kwargs):
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the infobox, or an error if the
            infobox could not be provided.
        """
        review_request = self.review_request
        submitter = review_request.submitter

        # Below code is heavily referenced from columns.py. We may want to
        # consider whether it's worth consolidating logic, or if we may want
        # to keep these separate.
        labels = []

        if (self.request.user.is_authenticated() and
            submitter == self.request.user and
            not review_request.public and
            review_request.status == ReviewRequest.PENDING_REVIEW):
            labels.append(('label-draft', _('Draft')))

        if review_request.status == ReviewRequest.SUBMITTED:
            labels.append(('label-submitted', _('Submitted')))
        elif review_request.status == ReviewRequest.DISCARDED:
            labels.append(('label-discarded', _('Discarded')))

        display_data = format_html_join('', '<label class="{0}">{1}</label>',
                                        labels)

        issue_total_count = (review_request.issue_open_count +
                             review_request.issue_resolved_count +
                             review_request.issue_dropped_count)

        # Fetch recent reviews to show in the infobox.
        latest_reviews = list(
            review_request.reviews
            .filter(public=True, base_reply_to__isnull=True)
            .order_by('-timestamp')[:self.MAX_REVIEWS]
        )

        return {
            'review_request': review_request,
            'review_request_id': review_request.display_id,
            'review_request_labels': display_data,
            'review_request_issue_total_count': issue_total_count,
            'review_request_latest_reviews': latest_reviews,
            'show_profile': submitter.is_profile_visible(self.request.user),
            'submitter': submitter,
        }


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

    try:
        data = get_original_file(filediff, request, encoding_list)
    except FileNotFoundError:
        logging.exception(
            'Could not retrieve file "%s" (revision %s) for filediff ID %s',
            filediff.dest_detail, revision, filediff_id)
        raise Http404

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
