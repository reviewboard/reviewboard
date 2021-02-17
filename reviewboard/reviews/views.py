from __future__ import unicode_literals

import io
import json
import logging
import re
import struct

import dateutil.parser
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.http import (Http404,
                         HttpResponse,
                         HttpResponseBadRequest,
                         HttpResponseNotFound)
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.template.defaultfilters import date
from django.utils import six, timezone
from django.utils.formats import localize
from django.utils.html import escape, format_html, strip_tags
from django.utils.safestring import mark_safe
from django.utils.timezone import is_aware, localtime, make_aware, utc
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic.base import (ContextMixin, RedirectView,
                                       TemplateView, View)
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.compat.django.template.loader import render_to_string
from djblets.util.dates import get_latest_timestamp
from djblets.util.http import set_last_modified
from djblets.views.generic.base import (CheckRequestMethodViewMixin,
                                        PrePostDispatchViewMixin)
from djblets.views.generic.etag import ETagViewMixin

from reviewboard.accounts.mixins import (CheckLoginRequiredViewMixin,
                                         LoginRequiredViewMixin,
                                         UserProfileRequiredViewMixin)
from reviewboard.accounts.models import ReviewRequestVisit, Profile
from reviewboard.admin.decorators import check_read_only
from reviewboard.admin.mixins import CheckReadOnlyViewMixin
from reviewboard.admin.read_only import is_site_read_only_for
from reviewboard.attachments.models import (FileAttachment,
                                            get_latest_file_attachments)
from reviewboard.diffviewer.diffutils import (convert_to_unicode,
                                              get_file_chunks_in_range,
                                              get_filediff_encodings,
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
from reviewboard.reviews.detail import ReviewRequestPageData, entry_registry
from reviewboard.reviews.markdown_utils import (is_rich_text_default_for_user,
                                                render_markdown)
from reviewboard.reviews.models import (Comment,
                                        Review,
                                        ReviewRequest,
                                        Screenshot)
from reviewboard.reviews.ui.base import FileAttachmentReviewUI
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__name__)


class ReviewRequestViewMixin(CheckRequestMethodViewMixin,
                             CheckLoginRequiredViewMixin,
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
        return render(request,
                      self.permission_denied_template_name,
                      status=403)

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
            reviewboard.diffviewer.models.diffset.DiffSet:
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

    def get_review_request_status_html(self, review_request_details,
                                       close_info, extra_info=[]):
        """Return HTML describing the current status of a review request.

        This will return a description of the submitted, discarded, or open
        state for the review request, for use in the rendering of the page.

        Args:
            review_request_details (reviewboard.reviews.models
                                    .base_review_request_details
                                    .BaseReviewRequestDetails):
                The review request or draft being viewed.

            close_info (dict):
                A dictionary of information on the closed state of the
                review request.

            extra_info (list of dict):
                A list of dictionaries showing additional status information.
                Each must have a ``text`` field containing a format string
                using ``{keyword}``-formatted variables, a ``timestamp`` field
                (which will be normalized to the local timestamp), and an
                optional ``extra_vars`` for the format string.

        Returns:
            unicode:
            The status text as HTML for the page.
        """
        review_request = self.review_request
        status = review_request.status
        review_request_details = review_request_details

        if status == ReviewRequest.SUBMITTED:
            timestamp = close_info['timestamp']

            if timestamp:
                text = ugettext('Created {created_time} and submitted '
                                '{timestamp}')
            else:
                text = ugettext('Created {created_time} and submitted')
        elif status == ReviewRequest.DISCARDED:
            timestamp = close_info['timestamp']

            if timestamp:
                text = ugettext('Created {created_time} and discarded '
                                '{timestamp}')
            else:
                text = ugettext('Created {created_time} and discarded')
        elif status == ReviewRequest.PENDING_REVIEW:
            text = ugettext('Created {created_time} and updated {timestamp}')
            timestamp = review_request_details.last_updated
        else:
            logger.error('Unexpected review request status %r for '
                         'review request %s',
                         status, review_request.display_id,
                         request=self.request)

            return ''

        parts = [
            {
                'text': text,
                'timestamp': timestamp,
                'extra_vars': {
                    'created_time': date(localtime(review_request.time_added)),
                },
            },
        ] + extra_info

        html_parts = []

        for part in parts:
            if part['timestamp']:
                timestamp = localtime(part['timestamp'])
                timestamp_html = format_html(
                    '<time class="timesince" datetime="{0}">{1}</time>',
                    timestamp.isoformat(),
                    localize(timestamp))
            else:
                timestamp_html = ''

            html_parts.append(format_html(
                part['text'],
                timestamp=timestamp_html,
                **part.get('extra_vars', {})))

        return mark_safe(' &mdash; '.join(html_parts))


#
# Helper functions
#

def build_diff_comment_fragments(
    comments,
    context,
    comment_template_name='reviews/diff_comment_fragment.html',
    error_template_name='diffviewer/diff_fragment_error.html',
    lines_of_context=None,
    show_controls=False,
    request=None):

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

            comment_context = {
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
            }
            comment_context.update(context)
            content = render_to_string(template_name=comment_template_name,
                                       context=comment_context,
                                       request=request)
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

class RootView(CheckLoginRequiredViewMixin,
               UserProfileRequiredViewMixin,
               CheckLocalSiteAccessViewMixin,
               RedirectView):
    """Handles the root URL of Review Board or a Local Site.

    If the user is authenticated, this will redirect to their Dashboard.
    Otherwise, they'll be redirected to the All Review Requests page.

    Either page may then redirect for login or show a Permission Denied,
    depending on the settings.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        """Return the URL to redirect to.

        Args:
            *args (tuple):
                Positional arguments passed to the view.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            unicode:
            The URL to redirect to. If the user is authenticated, this will
            return the dashboard's URL. Otherwise, it will return the
            All Review Request page's URL.
        """
        if self.request.user.is_authenticated():
            url_name = 'dashboard'
        else:
            url_name = 'all-review-requests'

        return local_site_reverse(url_name, local_site=self.local_site)


class NewReviewRequestView(LoginRequiredViewMixin,
                           CheckLocalSiteAccessViewMixin,
                           UserProfileRequiredViewMixin,
                           CheckReadOnlyViewMixin,
                           TemplateView):
    """View for the New Review Request page.

    This provides the user with a UI consisting of all their repositories,
    allowing them to manually upload a diff against the repository or,
    depending on the repository's capabilities, to browse for an existing
    commit to post.
    """

    template_name = 'reviews/new_review_request.html'

    def get_context_data(self, **kwargs):
        """Return data for the template.

        This will return information on each repository shown on the page.

        Args:
            **kwargs (dict):
                Additional keyword arguments passed to the view.

        Returns:
            dict:
            Context data for the template.
        """
        local_site = self.local_site

        if local_site:
            local_site_prefix = 's/%s/' % local_site.name
        else:
            local_site_prefix = ''

        valid_repos = [{
            'name': _('(None - File attachments only)'),
            'scmtoolName': '',
            'supportsPostCommit': False,
            'filesOnly': True,
            'localSitePrefix': local_site_prefix,
        }]

        repos = Repository.objects.accessible(self.request.user,
                                              local_site=local_site)

        for repo in repos.order_by('name'):
            try:
                valid_repos.append({
                    'id': repo.pk,
                    'name': repo.name,
                    'scmtoolName': repo.scmtool_class.name,
                    'localSitePrefix': local_site_prefix,
                    'supportsPostCommit': repo.supports_post_commit,
                    'requiresChangeNumber': repo.supports_pending_changesets,
                    'requiresBasedir': not repo.diffs_use_absolute_paths,
                    'filesOnly': False,
                })
            except Exception:
                logger.exception(
                    'Error loading information for repository "%s" (ID %d) '
                    'for the New Review Request page.',
                    repo.name, repo.pk)

        return {
            'page_model_attrs': {
                'repositories': valid_repos,
            }
        }


class ReviewRequestDetailView(ReviewRequestViewMixin,
                              UserProfileRequiredViewMixin,
                              ETagViewMixin,
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

        self.data = None
        self.visited = None
        self.blocks = None
        self.last_activity_time = None
        self.last_visited = None

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

        # Track the visit to this review request, so the dashboard can
        # reflect whether there are new updates.
        self.visited, self.last_visited = self.track_review_request_visit()

        # Begin building data for the contents of the page. This will include
        # the reviews, change descriptions, and other content shown on the
        # page.
        data = ReviewRequestPageData(review_request=review_request,
                                     request=request,
                                     last_visited=self.last_visited)
        self.data = data

        data.query_data_pre_etag()

        self.blocks = review_request.get_blocks()

        # Prepare data used in both the page and the ETag.
        starred = self.is_review_request_starred()

        self.last_activity_time = review_request.get_last_activity_info(
            data.diffsets, data.reviews)['timestamp']
        etag_timestamp = self.last_activity_time

        entry_etags = ':'.join(
            entry_cls.build_etag_data(data)
            for entry_cls in entry_registry
        )

        if data.draft:
            draft_timestamp = data.draft.last_updated
        else:
            draft_timestamp = ''

        return ':'.join(six.text_type(value) for value in (
            request.user,
            etag_timestamp,
            draft_timestamp,
            data.latest_changedesc_timestamp,
            entry_etags,
            data.latest_review_timestamp,
            review_request.last_review_activity_timestamp,
            is_rich_text_default_for_user(request.user),
            is_site_read_only_for(request.user),
            [r.pk for r in self.blocks],
            starred,
            self.visited and self.visited.visibility,
            (self.last_visited and
             self.last_visited < self.last_activity_time),
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
        last_visited = None

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
                logger.error('Unable to get or create ReviewRequestVisit '
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
                    user.get_profile(create_if_missing=False)
                    .starred_review_requests
                    .filter(pk=self.review_request.pk)
                    .exists()
                )
            except Profile.DoesNotExist:
                pass

        return False

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
            dict:
            Context data for the template.
        """
        review_request = self.review_request
        request = self.request
        data = self.data

        data.query_data_post_etag()
        entries = data.get_entries()

        review = review_request.get_pending_review(request.user)
        close_info = review_request.get_close_info()
        review_request_status_html = self.get_review_request_status_html(
            review_request_details=data.review_request_details,
            close_info=close_info)

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
            'review_request_status_html': review_request_status_html,
            'entries': entries,
            'last_activity_time': self.last_activity_time,
            'last_visited': self.last_visited,
            'review': review,
            'request': request,
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
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


class ReviewRequestUpdatesView(ReviewRequestViewMixin, ETagViewMixin,
                               ContextMixin, View):
    """Internal view for sending data for updating the review request page.

    This view serializes data representing components of the review request
    page (the issue summary table and entries) that need to periodically
    update without a full page reload. It's used internally by the page to
    request and handle updates.

    The resulting format is a custom, condensed format containing metadata
    information and HTML for each component being updated. It's designed
    to be quick to parse and reduces the amount of data to send across the
    wire (unlike a format like JSON, which would add overhead to the
    serialization/deserialization time and data size when storing HTML).

    Each entry in the payload is in the following format, with all entries
    joined together:

        <metadata length>\\n
        <metadata content>
        <html length>\\n
        <html content>

    The format is subject to change without notice, and should not be
    relied upon by third parties.
    """

    def __init__(self, **kwargs):
        """Initialize the view.

        Args:
            **kwargs (tuple):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super(ReviewRequestUpdatesView, self).__init__(**kwargs)

        self.entry_ids = {}
        self.data = None
        self.since = None

    def pre_dispatch(self, request, *args, **kwargs):
        """Look up and validate state before dispatching the request.

        This looks up information based on the request before performing any
        ETag generation or otherwise handling the HTTP request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple, unused):
                Positional arguments passsed to the view.

            **kwargs (dict, unused):
                Keyword arguments passed to the view.

        Returns:
            django.http.HttpResponse:
            The HTTP response containin the updates payload.
        """
        super(ReviewRequestUpdatesView, self).pre_dispatch(request, *args,
                                                           **kwargs)

        # Find out which entries and IDs (if any) that the caller is most
        # interested in.
        entries_str = request.GET.get('entries')

        if entries_str:
            try:
                for entry_part in entries_str.split(';'):
                    entry_type, entry_ids = entry_part.split(':')
                    self.entry_ids[entry_type] = set(entry_ids.split(','))
            except ValueError as e:
                return HttpResponseBadRequest('Invalid ?entries= value: %s'
                                              % e)

        if self.entry_ids:
            entry_classes = []

            for entry_type in six.iterkeys(self.entry_ids):
                entry_cls = entry_registry.get_entry(entry_type)

                if entry_cls:
                    entry_classes.append(entry_cls)
        else:
            entry_classes = list(entry_registry)

        if not entry_classes:
            raise Http404

        self.since = request.GET.get('since')

        self.data = ReviewRequestPageData(self.review_request, request,
                                          entry_classes=entry_classes)

    def get_etag_data(self, request, *args, **kwargs):
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the payload.

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
        data = self.data

        # Build page data only for the entry we care about.
        data.query_data_pre_etag()

        last_activity_time = review_request.get_last_activity_info(
            data.diffsets, data.reviews)['timestamp']

        entry_etags = ':'.join(
            entry_cls.build_etag_data(data)
            for entry_cls in entry_registry
        )

        return ':'.join(six.text_type(value) for value in (
            request.user,
            last_activity_time,
            data.latest_review_timestamp,
            review_request.last_review_activity_timestamp,
            entry_etags,
            is_rich_text_default_for_user(request.user),
            settings.AJAX_SERIAL,
        ))

    def get(self, request, **kwargs):
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client. This will contain the
            custom update payload content.
        """
        request = self.request
        review_request = self.review_request
        data = self.data
        since = self.since

        # Finish any querying needed by entries on this page.
        self.data.query_data_post_etag()

        # Gather all the entries into a single list.
        #
        # Note that the order in which we build the resulting list of entries
        # doesn't matter at this stage, but it does need to be consistent.
        # The current order (main, initial) is based on Python 2.7 sort order,
        # which our tests are based on. This could be changed in the future.
        all_entries = data.get_entries()
        entries = all_entries['main'] + all_entries['initial']

        if self.entry_ids:
            # If specific entry IDs have been requested, limit the results
            # to those.
            entries = (
                entry
                for entry in entries
                if (entry.entry_type_id in self.entry_ids and
                    entry.entry_id in self.entry_ids[entry.entry_type_id])
            )

        # See if the caller only wants to fetch entries updated since a given
        # timestamp.
        if since:
            since = dateutil.parser.parse(since)

            if not is_aware(since):
                since = make_aware(since, utc)

            entries = (
                entry
                for entry in entries
                if (entry.updated_timestamp is not None and
                    entry.updated_timestamp > since)
            )

        # We can now begin to serialize the payload for all the updates.
        payload = io.BytesIO()
        base_entry_context = None
        needs_issue_summary_table = False

        for entry in entries:
            metadata = {
                'type': 'entry',
                'entryType': entry.entry_type_id,
                'entryID': entry.entry_id,
                'addedTimestamp': six.text_type(entry.added_timestamp),
                'updatedTimestamp': six.text_type(entry.updated_timestamp),
                'modelData': entry.get_js_model_data(),
                'viewOptions': entry.get_js_view_data(),
            }

            if base_entry_context is None:
                # Now that we know the context is needed for entries,
                # we can construct and populate it.
                base_entry_context = (
                    super(ReviewRequestUpdatesView, self)
                    .get_context_data(**kwargs)
                )
                base_entry_context.update(
                    make_review_request_context(request, review_request))

            try:
                html = render_to_string(
                    template_name=entry.template_name,
                    context=dict({
                        'show_entry_statuses_area': (
                            entry.entry_pos == entry.ENTRY_POS_MAIN),
                        'entry': entry,
                    }, **base_entry_context),
                    request=request)
            except Exception as e:
                logger.error('Error rendering review request page entry '
                             '%r: %s',
                             entry, e, request=request)

            self._write_update(payload, metadata, html)

            if entry.needs_reviews:
                needs_issue_summary_table = True

        # If any of the entries required any information on reviews, then
        # the state of the issue summary table may have changed. We'll need
        # to send this along as well.
        if needs_issue_summary_table:
            metadata = {
                'type': 'issue-summary-table',
            }

            html = render_to_string(
                template_name='reviews/review_issue_summary_table.html',
                context={
                    'issue_counts': data.issue_counts,
                    'issues': data.issues,
                },
                request=request)

            self._write_update(payload, metadata, html)

        # The payload's complete. Close it out and send to the client.
        result = payload.getvalue()
        payload.close()

        return HttpResponse(result, content_type='text/plain; charset=utf-8')

    def _write_update(self, payload, metadata, html):
        """Write an update to the payload.

        This will format the metadata and HTML for the update and write it.

        Args:
            payload (io.BytesIO):
                The payload to write to.

            metadata (dict):
                The JSON-serializable metadata to write.

            html (unicode):
                The HTML to write.
        """
        metadata = json.dumps(metadata).encode('utf-8')
        html = html.strip().encode('utf-8')

        payload.write(struct.pack(b'<L', len(metadata)))
        payload.write(metadata)
        payload.write(struct.pack(b'<L', len(html)))
        payload.write(html)


class ReviewsDiffViewerView(ReviewRequestViewMixin,
                            UserProfileRequiredViewMixin,
                            DiffViewerView):
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

        self.draft = review_request.get_draft(review_request.submitter)

        if self.draft and not self.draft.is_accessible_by(request.user):
            self.draft = None

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
            dict:
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

        last_activity_time = self.review_request.get_last_activity_info(
            diffsets)['timestamp']

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
        q = (
            Review.comments.through.objects
            .filter(review__review_request=self.review_request)
            .select_related()
        )

        for obj in q:
            comment = obj.comment
            comment.review_obj = obj.review
            key = (comment.filediff_id, comment.interfilediff_id)
            comments.setdefault(key, []).append(comment)

        # Build the status information shown below the summary.
        close_info = self.review_request.get_close_info()

        if latest_diffset:
            status_extra_info = [{
                'text': ugettext('Latest diff uploaded {timestamp}'),
                'timestamp': latest_diffset.timestamp,
            }]
        else:
            status_extra_info = []

        review_request_status_html = self.get_review_request_status_html(
            review_request_details=review_request_details,
            close_info=close_info,
            extra_info=status_extra_info)

        # Build the final context for the page.
        context = super(ReviewsDiffViewerView, self).get_context_data(**kwargs)
        context.update({
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'diffsets': diffsets,
            'review': pending_review,
            'review_request_details': review_request_details,
            'review_request_status_html': review_request_status_html,
            'draft': self.draft,
            'last_activity_time': last_activity_time,
            'file_attachments': latest_file_attachments,
            'all_file_attachments': file_attachments,
            'screenshots': screenshots,
            'comments': comments,
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
            base_filediff = f['base_filediff']

            if base_filediff:
                base_filediff_id = base_filediff.pk
            else:
                base_filediff_id = None

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
                'base_filediff_id': base_filediff_id,
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


class DownloadRawDiffView(ReviewRequestViewMixin, View):
    """View for downloading a raw diff from a review request.

    This will generate a single raw diff file spanning all the FileDiffs
    in a diffset for the revision specified in the URL.
    """

    def get(self, request, revision=None, *args, **kwargs):
        """Handle HTTP GET requests for this view.

        This will generate the raw diff file and send it to the client.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int, optional):
                The revision of the diff to download. Defaults to the latest
                revision.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request

        draft = review_request.get_draft(request.user)
        diffset = self.get_diff(revision, draft)

        tool = review_request.repository.get_scmtool()
        data = tool.get_parser(b'').raw_diff(diffset)

        resp = HttpResponse(data, content_type='text/x-patch')

        if diffset.name == 'diff':
            filename = 'rb%d.patch' % review_request.display_id
        else:
            # Get rid of any Unicode characters that may be in the filename.
            filename = diffset.name.encode('ascii', 'ignore').decode('ascii')

            # Content-Disposition headers containing commas break on Chrome 16
            # and newer. To avoid this, replace any commas in the filename with
            # an underscore. Was bug 3704.
            filename = filename.replace(',', '_')

        resp['Content-Disposition'] = 'attachment; filename=%s' % filename
        set_last_modified(resp, diffset.timestamp)

        return resp


class CommentDiffFragmentsView(ReviewRequestViewMixin, ETagViewMixin,
                               ContextMixin, View):
    """View for rendering a section of a diff that a comment pertains to.

    This takes in one or more
    :py:class:`~reviewboard.reviews.models.diff_comment.Comment` IDs
    (comma-separated) as part of the URL and returns a payload containing
    data and HTML for each comment's diff fragment, which the client can
    parse in order to dynamically load the fragments into the page.

    The resulting format is a custom, condensed format containing the comment
    ID and HTML for each diff fragment. It's designed to be quick to parse and
    reduces the amount of data to send across the wire (unlike a format like
    JSON, which would add overhead to the serialization/deserialization time
    and data size when storing HTML, or JavaScript, which releases prior to
    3.0 used to handle injecting fragments into the DOM).

    Each entry in the payload is in the following format, with all entries
    joined together:

        <comment ID>\\n
        <html length>\\n
        <html content>

    The format is subject to change without notice, and should not be relied
    upon by third parties.

    The following URL query options are supported:

    ``allow_expansion``:
        Whether expansion controls should be shown to the user. To enable
        this, the caller must pass a value of ``1``. This is disabled by
        default.

    ``lines_of_context``:
        The number of lines of context before and after the commented region
        of the diff. This is in the form of ``pre,post``, where both are the
        numbers of lines. This defaults to ``0,0``.
    """

    comment_template_name = 'reviews/diff_comment_fragment.html'
    error_template_name = 'diffviewer/diff_fragment_error.html'

    content_type = 'application/javascript'

    EXPIRATION_SECONDS = 60 * 60 * 24 * 365  # 1 year

    def get_etag_data(self, request, comment_ids, *args, **kwargs):
        """Return an ETag for the view.

        This will look up state needed for the request and generate a
        suitable ETag. Some of the information will be stored for later
        computation of the template context.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            comment_ids (unicode):
                A list of comment IDs to render.

            *args (tuple, unused):
                Positional arguments passsed to the handler.

            **kwargs (dict, unused):
                Keyword arguments passed to the handler.

        Returns:
            unicode:
            The ETag for the page.
        """
        q = (Q(pk__in=comment_ids.split(',')) &
             Q(review__review_request=self.review_request))

        if request.user.is_authenticated():
            q &= Q(review__public=True) | Q(review__user=request.user)
        else:
            q &= Q(review__public=True)

        self.comments = get_list_or_404(Comment, q)

        latest_timestamp = get_latest_timestamp(
            comment.timestamp
            for comment in self.comments
        )

        return '%s:%s:%s' % (comment_ids, latest_timestamp,
                             settings.TEMPLATE_SERIAL)

    def get(self, request, **kwargs):
        """Handle HTTP GET requests for this view.

        This will generate a payload for the diff comments being loaded and
        pass them in a format that can be parsed by the client.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the fragments payload.
        """
        lines_of_context = request.GET.get('lines_of_context', '0,0')
        allow_expansion = (request.GET.get('allow_expansion') == '1')

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

        context = \
            super(CommentDiffFragmentsView, self).get_context_data(**kwargs)
        context.update({
            'request': request,
            'user': request.user,
        })

        payload = io.BytesIO()
        comment_entries = build_diff_comment_fragments(
            comments=self.comments,
            context=context,
            comment_template_name=self.comment_template_name,
            error_template_name=self.error_template_name,
            lines_of_context=lines_of_context,
            show_controls=allow_expansion)[1]

        for entry in comment_entries:
            html = entry['html'].strip().encode('utf-8')

            payload.write(struct.pack(b'<LL', entry['comment'].pk, len(html)))
            payload.write(html)

        result = payload.getvalue()
        payload.close()

        return HttpResponse(result, content_type='text/plain; charset=utf-8')


class ReviewsDiffFragmentView(ReviewRequestViewMixin, DiffFragmentView):
    """Renders a fragment from a file in the diff viewer.

    Displays just a fragment of a diff or interdiff owned by the given
    review request. The fragment is identified by the chunk index in the
    diff.

    ``review_request_id``:
        The ID of the ReviewRequest containing the diff to render.

    ``revision``:
        The DiffSet revision to render.

    ``filediff_id``:
        The ID of the FileDiff within the DiffSet.

    The following may also be provided:

    ``interdiff_revision``:
        The second DiffSet revision in an interdiff revision range.

    ``chunk_index``:
        The index (0-based) of the chunk to render. If left out, the
        entire file will be rendered.

    ``local_site``:
        The LocalSite the ReviewRequest must be on, if any.

    See :py:class:`~reviewboard.diffviewer.views.DiffFragmentView` for the
    accepted query parameters.
    """

    def process_diffset_info(self, revision, interdiff_revision=None,
                             **kwargs):
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        If the review request cannot be accessed by the user, an HttpResponse
        will be returned instead.

        Args:
            revision (int):
                The revision of the diff to view.

            interdiff_revision (int, optional):
                The second diff revision if viewing an interdiff.

            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            dict:
            Information on the diff for use in the template and in queries.
        """
        user = self.request.user
        draft = self.review_request.get_draft(user)

        if interdiff_revision is not None:
            interdiffset = self.get_diff(interdiff_revision, draft)
        else:
            interdiffset = None

        diffset = self.get_diff(revision, draft)

        return super(ReviewsDiffFragmentView, self).process_diffset_info(
            diffset_or_id=diffset,
            interdiffset_or_id=interdiffset,
            **kwargs)

    def create_renderer(self, diff_file, *args, **kwargs):
        """Create the DiffRenderer for this fragment.

        This will augment the renderer for binary files by looking up
        file attachments, if review UIs are involved, disabling caching.

        Args:
            diff_file (dict):
                The information on the diff file to render.

            *args (tuple):
                Additional positional arguments from the parent class.

            **kwargs (dict):
                Additional keyword arguments from the parent class.

        Returns:
            reviewboard.diffviewer.renderers.DiffRenderer:
            The resulting diff renderer.
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
            logger.error('More than one FileAttachments associated with '
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
            'to_owner_only': False,
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


class ReviewFileAttachmentView(ReviewRequestViewMixin,
                               UserProfileRequiredViewMixin,
                               View):
    """Displays a file attachment with a review UI."""

    def get(self, request, file_attachment_id, file_attachment_diff_id=None,
            *args, **kwargs):
        """Handle a HTTP GET request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            file_attachment_id (int):
                The ID of the file attachment to review.

            file_attachment_diff_id (int, optional):
                The ID of the file attachment to diff against.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the handler.
        """
        review_request = self.review_request
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
            logger.error('Error when calling is_enabled_for for '
                         'FileAttachmentReviewUI %r: %s',
                         review_ui, e, exc_info=1)
            is_enabled_for = False

        if review_ui and is_enabled_for:
            return review_ui.render_to_response(request)
        else:
            raise Http404


class ReviewScreenshotView(ReviewRequestViewMixin,
                           UserProfileRequiredViewMixin,
                           View):
    """Displays a review UI for a screenshot.

    Screenshots are a legacy feature, predating file attachments. While they
    can't be created anymore, this view does allow for reviewing screenshots
    uploaded in old versions.
    """

    def get(self, request, screenshot_id, *args, **kwargs):
        """Handle a HTTP GET request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            screenshot_id (int):
                The ID of the screenshot to review.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response from the handler.
        """
        review_request = self.review_request
        draft = review_request.get_draft(request.user)

        # Make sure the screenshot returned is part of either the review
        # request or an accessible draft.
        review_request_q = (Q(review_request=review_request) |
                            Q(inactive_review_request=review_request))

        if draft:
            review_request_q |= Q(drafts=draft) | Q(inactive_drafts=draft)

        screenshot = get_object_or_404(Screenshot,
                                       Q(pk=screenshot_id) & review_request_q)
        review_ui = LegacyScreenshotReviewUI(review_request, screenshot)

        return review_ui.render_to_response(request)


class BugURLRedirectView(ReviewRequestViewMixin, View):
    """Redirects the user to an external bug report."""

    def get(self, request, bug_id, **kwargs):
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            bug_id (unicode):
                The ID of the bug report to redirect to.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response redirecting the client.
        """
        # Need to create a custom HttpResponse because a non-HTTP url scheme
        # will cause HttpResponseRedirect to fail with a "Disallowed Redirect".
        response = HttpResponse(status=302)
        response['Location'] = \
            self.review_request.repository.bug_tracker % bug_id

        return response


class BugInfoboxView(ReviewRequestViewMixin, TemplateView):
    """Displays information on a bug, for use in bug pop-up infoboxes.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """

    template_name = 'reviews/bug_infobox.html'

    HTML_ENTITY_RE = re.compile(r'(&[a-z]+;)')
    HTML_ENTITY_MAP = {
        '&quot;': '"',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
    }

    def get(self, request, bug_id, **kwargs):
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            bug_id (unicode):
                The ID of the bug to view.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.

            If details on a bug could not be found or fetching bug information
            is not supported, this will return a a :http:`404`.
        """
        request = self.request
        review_request = self.review_request
        repository = review_request.repository

        bug_tracker = repository.bug_tracker_service

        if not bug_tracker:
            return HttpResponseNotFound(
                _('Unable to find bug tracker service'))

        if not isinstance(bug_tracker, BugTracker):
            return HttpResponseNotFound(
                _('Bug tracker %s does not support metadata')
                % bug_tracker.name)

        self.bug_id = bug_id
        self.bug_info = bug_tracker.get_bug_info(repository, bug_id)

        if (not self.bug_info.get('summary') and
            not self.bug_info.get('description')):
            return HttpResponseNotFound(
                _('No bug metadata found for bug %(bug_id)s on bug tracker '
                  '%(bug_tracker)s') % {
                    'bug_id': bug_id,
                    'bug_tracker': bug_tracker.name,
                })

        return super(BugInfoboxView, self).get(request, **kwargs)

    def get_context_data(self, **kwargs):
        """Return context data for the template.

        Args:
            **kwargs (dict):
                Keyword arguments passed to the view.

        Returns:
            dict:
            The resulting context data for the template.
        """
        description_text_format = self.bug_info.get('description_text_format',
                                                    'plain')
        description = self.normalize_text(self.bug_info['description'],
                                          description_text_format)

        bug_url = local_site_reverse(
            'bug_url',
            args=[self.review_request.display_id, self.bug_id])

        context_data = super(BugInfoboxView, self).get_context_data(**kwargs)
        context_data.update({
            'bug_id': self.bug_id,
            'bug_url': bug_url,
            'bug_description': description,
            'bug_description_rich_text': description_text_format == 'markdown',
            'bug_status': self.bug_info['status'],
            'bug_summary': self.bug_info['summary'],
        })

        return context_data

    def normalize_text(self, text, text_format):
        """Normalize the text for display.

        Based on the text format, this will sanitize and normalize the text
        so it's suitable for rendering to HTML.

        HTML text will have tags stripped away and certain common entities
        replaced.

        Markdown text will be rendered using our default Markdown parser
        rules.

        Plain text (or any unknown text format) will simply be escaped and
        wrapped, with paragraphs left intact.

        Args:
            text (unicode):
                The text to normalize for display.

            text_format (unicode):
                The text format. This should be one of ``html``, ``markdown``,
                or ``plain``.

        Returns:
            django.utils.safestring.SafeText:
            The resulting text, safe for rendering in HTML.
        """
        if text_format == 'html':
            # We want to strip the tags away, but keep certain common entities.
            text = (
                escape(self.HTML_ENTITY_RE.sub(
                    lambda m: (self.HTML_ENTITY_MAP.get(m.group(0)) or
                               m.group(0)),
                    strip_tags(text)))
                .replace('\n\n', '<br><br>'))
        elif text_format == 'markdown':
            # This might not know every bit of Markdown that's thrown at us,
            # but we'll do the best we can.
            text = render_markdown(text)
        else:
            # Should be plain text, but don't trust it.
            text = escape(text).replace('\n\n', '<br><br>')

        return mark_safe(text)


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
        draft = review_request.get_draft(self.request.user)

        # We only want to show one label. If there's a draft, then that's
        # the most important information, so we'll only show that. Otherwise,
        # we'll show the submitted/discarded state.
        label = None

        if draft:
            label = ('review-request-infobox-label-draft', _('Draft'))
        elif review_request.status == ReviewRequest.SUBMITTED:
            label = ('review-request-infobox-label-submitted', _('Submitted'))
        elif review_request.status == ReviewRequest.DISCARDED:
            label = ('review-request-infobox-label-discarded', _('Discarded'))

        if label:
            label = format_html('<label class="{0}">{1}</label>', *label)

        # Fetch information on the reviews for this review request.
        review_count = (
            review_request.reviews
            .filter(public=True, base_reply_to__isnull=True)
            .count()
        )

        # Fetch information on the draft for this review request.
        diffset = None

        if draft and draft.diffset_id:
            diffset = draft.diffset

        if not diffset and review_request.diffset_history_id:
            try:
                diffset = (
                    DiffSet.objects
                    .filter(history__pk=review_request.diffset_history_id)
                    .latest()
                )
            except DiffSet.DoesNotExist:
                pass

        if diffset:
            diff_url = '%s#index_header' % local_site_reverse(
                'view-diff-revision',
                args=[review_request.display_id, diffset.revision],
                local_site=review_request.local_site)
        else:
            diff_url = None

        return {
            'review_request': review_request,
            'review_request_label': label or '',
            'review_request_details': draft or review_request,
            'issue_total_count': (review_request.issue_open_count +
                                  review_request.issue_resolved_count +
                                  review_request.issue_dropped_count +
                                  review_request.issue_verifying_count),
            'review_count': review_count,
            'diffset': diffset,
            'diff_url': diff_url,
        }


class DownloadDiffFileView(ReviewRequestViewMixin, View):
    """Downloads an original or modified file from a diff.

    This will fetch the file from a FileDiff, optionally patching it,
    and return the result as an HttpResponse.
    """

    TYPE_ORIG = 0
    TYPE_MODIFIED = 1

    file_type = TYPE_ORIG

    def get(self, request, revision, filediff_id, *args, **kwargs):
        """Handle HTTP GET requests for this view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            revision (int):
                The revision of the diff to download the file from.

            filediff_id (int, optional):
                The ID of the FileDiff corresponding to the file to download.

            *args (tuple):
                Positional arguments passed to the handler.

            **kwargs (dict):
                Keyword arguments passed to the handler.

        Returns:
            django.http.HttpResponse:
            The HTTP response to send to the client.
        """
        review_request = self.review_request
        draft = review_request.get_draft(request.user)
        diffset = self.get_diff(revision, draft)
        filediff = get_object_or_404(diffset.files, pk=filediff_id)

        try:
            data = get_original_file(filediff=filediff,
                                     request=request)
        except FileNotFoundError:
            logger.exception(
                'Could not retrieve file "%s" (revision %s) for filediff '
                'ID %s',
                filediff.dest_detail, revision, filediff_id)
            raise Http404

        if self.file_type == self.TYPE_MODIFIED:
            data = get_patched_file(source_data=data,
                                    filediff=filediff,
                                    request=request)

        encoding_list = get_filediff_encodings(filediff)
        data = convert_to_unicode(data, encoding_list)[1]

        return HttpResponse(data, content_type='text/plain; charset=utf-8')
