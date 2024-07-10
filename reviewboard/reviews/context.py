"""Methods to help with building the review request rendering context."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING, Union

from django.utils.translation import gettext as _
from django.template.defaultfilters import truncatechars
from djblets.siteconfig.models import SiteConfiguration
from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import NotRequired, TypedDict

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.admin.server import build_server_url
from reviewboard.deprecation import (RemovedInReviewBoard80Warning,
                                     RemovedInReviewBoard90Warning)
from reviewboard.diffviewer.models import DiffSet
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from datetime import datetime

    from django.http import HttpRequest

    from reviewboard.reviews.models import (
        ReviewRequest,
        ReviewRequestDraft,
    )
    from reviewboard.reviews.models.review_request import \
        ReviewRequestCloseInfo
    from reviewboard.scmtools.models import Tool


class SerializedReviewRequestTab(TypedDict):
    """Serialized information about a tab on the review request page.

    Version Added:
        7.0
    """

    #: Whether this tab is the active tab.
    active: NotRequired[bool]

    #: The text to show on the tab label.
    text: str

    #: The URL to link to for the tab.
    url: str


class ReviewRequestContext(TypedDict):
    """Template context for rendering the review request.

    Version Changed:
        7.0.2:
        Added the following fields:

        * ``close_description``
        * ``close_description_rich_text``
        * ``close_timestamp``
        * ``draft``
        * ``force_view_user_draft``
        * ``review_request_details``
        * ``user_draft_exists``
        * ``viewing_user_draft``

    Version Added:
        7.0
    """

    #: The description attached to the most recent closing.
    #:
    #: Version Added:
    #:     7.0.2
    close_description: str

    #: Whether the close description is rich text.
    #:
    #: Version Added:
    #:     7.0.2
    close_description_rich_text: bool

    #: The timestamp of the most recent closing.
    #:
    #: Version Added:
    #:     7.0.2
    close_timestamp: Optional[datetime]

    #: The current draft, if present.
    #:
    #: Version Added:
    #:     7.0.2
    draft: Optional[ReviewRequestDraft]

    #: Whether to force viewing a draft owned by another user.
    #:
    #: Version Added:
    #:     7.0.2
    force_view_user_draft: bool

    #: Whether the review request is mutable by the current user.
    mutable_by_user: bool

    #: The review request object.
    review_request: ReviewRequest

    #: The current object to use for displaying the review request data.
    #:
    #: Version Added:
    #:     7.0.2
    review_request_details: Union[ReviewRequest, ReviewRequestDraft]

    #: The most recent review request visit info, if available.
    review_request_visit: NotRequired[ReviewRequestVisit]

    #: Whether the user can change the review request status.
    status_mutable_by_user: bool

    #: The SCMTool for the current review request, if it has a diff.
    scmtool: Optional[Tool]

    #: Global setting for whether to send e-mails for publish actions.
    send_email: bool

    #: The description to use for social media links to the review request.
    social_page_description: str

    #: The image URL to use for social media links.
    social_page_image_url: Optional[str]

    #: The title text to use for social media links.
    social_page_title: str

    #: The URL to use for social media links to the review request.
    social_page_url: str

    #: The tabs to show for the review request.
    tabs: list[SerializedReviewRequestTab]

    #: Whether a draft exists that is owned by another user.
    #:
    #: Version Added:
    #:     7.0.2
    user_draft_exists: bool

    #: Whether the user is viewing a draft owned by another user.
    #:
    #: Version Added:
    #:     7.0.2
    viewing_user_draft: bool


@deprecate_non_keyword_only_args(RemovedInReviewBoard80Warning)
def make_review_request_context(
    *,
    request: HttpRequest,
    review_request: ReviewRequest,
    extra_context: Optional[dict[str, Any]] = None,
    is_diff_view: bool = False,
    social_page_image_url: Optional[str] = None,
    social_page_title: str = '',
    review_request_details: Optional[
        Union[ReviewRequest, ReviewRequestDraft]] = None,
    close_info: Optional[ReviewRequestCloseInfo] = None,
    draft: Optional[ReviewRequestDraft] = None,
    force_view_user_draft: bool = False,
) -> ReviewRequestContext:
    """Return a dictionary for template contexts used for review requests.

    The dictionary will contain the common data that is used for all
    review request-related pages (the review request detail page, the diff
    viewer, and the screenshot pages).

    For convenience, extra data can be passed to this dictionary.

    Version Changed:
        7.0.2:
        * Deprecated the ``extra_context`` argument.
        * Added the ``review_request_details``, ``close_info``, ``draft`` and
          ``force_view_user_draft`` arguments.

    Version Changed:
        7.0:
        Added ``social_page_image_url`` and ``social_page_title`` arguments.

    Args:
        request (django.http.HttpRequest):
            The HTTP request.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request.

        extra_context (dict, optional):
            Extra information to include in the context.

        is_diff_view (bool, optional):
            Whether the user is viewing a diff.

        social_page_image_url (str, optional):
            The image URL to include for social media thumbnails.

            Version Added:
                7.0

        social_page_title (str, optional):
            The page title to include for social media thumbnails.

            Version Added:
                7.0

        review_request_details (reviewboard.reviews.models.ReviewRequest or
                                reviewboard.reviews.models.
                                ReviewRequestDraft):
            The object to show review request content from.

            Version Added:
                7.0

        close_info (reviewboard.reviews.models.review_request.
                    ReviewRequestCloseInfo, optional):
            Close information about the review request.

            Version Added:
                7.0.2

        draft (reviewboard.reviews.models.ReviewRequestDraft, optional):
            The review request draft.

            Version Added:
                7.0.2

        force_view_user_draft (bool, optional):
            Whether to force viewing another user's draft.

            This is used when a user with privilege to view other users' draft
            data is viewing something which only exists in the draft (such as
            an unpublished review request or a file attachment added in a new
            draft).

            Version Added:
                7.0.2

    Returns:
        ReviewRequestContext:
        The context for rendering review request templates.
    """
    if review_request.repository:
        scmtool = review_request.repository.get_scmtool()
    else:
        scmtool = None

    tabs: list[SerializedReviewRequestTab] = [
        {
            'text': _('Reviews'),
            'url': review_request.get_absolute_url(),
        },
    ]

    if draft is None:
        draft = review_request.get_draft(request.user)

    # If we have an accessible draft, and the viewing user is not the owner of
    # the review request, we normally do not want to show the draft data. If
    # the page is accessed via ?view-draft=1, we'll let the admin-like user see
    # and manipulate the draft data.
    user_draft_exists: bool = False
    viewing_user_draft: bool = False

    # If the user viewing this review request is not the submitter, but has
    # access to the draft, we want to let them choose to either view it as if
    # they were a regular user, or view the draft data. In the case of review
    # requests which are not yet public, we unconditionally show the draft
    # data.
    if draft and request.user != review_request.submitter:
        user_draft_exists = True

        if (force_view_user_draft or
            should_view_draft(request=request,
                              review_request=review_request,
                              draft=draft)):
            viewing_user_draft = True
        else:
            draft = None

        if not review_request.public:
            force_view_user_draft = True

    if ((draft and draft.diffset_id) or
        (hasattr(review_request, '_diffsets') and
         len(review_request._diffsets) > 0)):
        has_diffs = True
    else:
        # We actually have to do a query
        has_diffs = DiffSet.objects.filter(
            history__pk=review_request.diffset_history_id).exists()

    if has_diffs:
        tabs.append({
            'active': is_diff_view,
            'text': _('Diff'),
            'url': (
                local_site_reverse(
                    'view-diff',
                    args=[review_request.display_id],
                    local_site=review_request.local_site) +
                '#index_header'),
        })

    siteconfig = SiteConfiguration.objects.get_current()

    if review_request_details is None:
        review_request_details = draft or review_request

    description = review_request_details.description
    assert description is not None
    social_page_description = truncatechars(
        description.replace('\n', ' '), 300)

    if close_info is None:
        close_info = review_request.get_close_info()

    context: ReviewRequestContext = {
        'close_description': close_info['close_description'],
        'close_description_rich_text': close_info['is_rich_text'],
        'close_timestamp': close_info['timestamp'],
        'draft': draft,
        'force_view_user_draft': force_view_user_draft,
        'mutable_by_user': review_request.is_mutable_by(request.user),
        'status_mutable_by_user':
            review_request.is_status_mutable_by(request.user),
        'review_request': review_request,
        'review_request_details': review_request_details,
        'scmtool': scmtool,
        'send_email': siteconfig.get('mail_send_review_mail'),
        'tabs': tabs,
        'social_page_description': social_page_description,
        'social_page_image_url': social_page_image_url,
        'social_page_title': social_page_title,
        'social_page_url': build_server_url(request.path, request=request),
        'user_draft_exists': user_draft_exists,
        'viewing_user_draft': viewing_user_draft,
    }

    if extra_context:
        RemovedInReviewBoard90Warning.warn(
            'The extra_context argument to make_review_request_context is '
            'deprecated and will be removed in Review Board 9.0.')

        context.update(extra_context)

    if ('review_request_visit' not in context and
        request.user.is_authenticated):
        # The main review request view will already have populated this, but
        # other related views (like the diffviewer) don't.
        context['review_request_visit'] = \
            ReviewRequestVisit.objects.get_or_create(
                user=request.user,
                review_request=review_request)[0]

    return context


def should_view_draft(
    *,
    request: HttpRequest,
    review_request: ReviewRequest,
    draft: Optional[ReviewRequestDraft],
) -> bool:
    """Return whether the requesting user should view the draft.

    Args:
        request (django.http.HttpRequest):
            The HTTP request.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The current review request.

        draft (reviewboard.reviews.models.ReviewRequestDraft):
            The current review request draft.

    Returns:
        bool:
        ``True`` if the user should view the draft data.
    """
    if draft:
        # The owner of the review request should always see the draft data.
        if review_request.submitter == request.user:
            return True

        # Review requests that have not yet been published only have draft
        # data.
        if not review_request.public:
            return True

        # If the user wants to view the draft, show it.
        if request.GET.get('view-draft', False) == '1':
            return True

    return False
