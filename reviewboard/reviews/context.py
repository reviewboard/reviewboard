"""Methods to help with building the review request rendering context."""

from __future__ import annotations

from django.utils.translation import gettext as _
from django.template.defaultfilters import truncatechars
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.admin.server import build_server_url
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.forms import UploadDiffForm
from reviewboard.site.urlresolvers import local_site_reverse


def make_review_request_context(request, review_request, extra_context={},
                                is_diff_view=False):
    """Returns a dictionary for template contexts used for review requests.

    The dictionary will contain the common data that is used for all
    review request-related pages (the review request detail page, the diff
    viewer, and the screenshot pages).

    For convenience, extra data can be passed to this dictionary.
    """
    if review_request.repository:
        upload_diff_form = UploadDiffForm(review_request, request=request)
        scmtool = review_request.repository.get_scmtool()
    else:
        upload_diff_form = None
        scmtool = None

    if 'blocks' not in extra_context:
        extra_context['blocks'] = list(review_request.blocks.all())

    tabs = [
        {
            'text': _('Reviews'),
            'url': review_request.get_absolute_url(),
        },
    ]

    draft = review_request.get_draft(request.user)

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

    review_request_details = extra_context.get('review_request_details',
                                               review_request)
    social_page_description = truncatechars(
        review_request_details.description.replace('\n', ' '),
        300)

    context = dict({
        'mutable_by_user': review_request.is_mutable_by(request.user),
        'status_mutable_by_user':
            review_request.is_status_mutable_by(request.user),
        'review_request': review_request,
        'upload_diff_form': upload_diff_form,
        'scmtool': scmtool,
        'send_email': siteconfig.get('mail_send_review_mail'),
        'tabs': tabs,
        'social_page_description': social_page_description,
        'social_page_url': build_server_url(request.path, request=request),
    }, **extra_context)

    if ('review_request_visit' not in context and
        request.user.is_authenticated):
        # The main review request view will already have populated this, but
        # other related views (like the diffviewer) don't.
        context['review_request_visit'] = \
            ReviewRequestVisit.objects.get_or_create(
                user=request.user,
                review_request=review_request)[0]

    return context


def has_comments_in_diffsets_excluding(review, diffset_pair):
    """Returns whether the specified review has "other comments".

    This is used to notify users that their review has comments on diff
    revisions other than the one that they happen to be looking at at any given
    moment.
    """
    if not review:
        return False

    current_diffset, interdiff = diffset_pair

    # See if there are any diffsets with comments on them in this review.
    q = DiffSet.objects.filter(files__comments__review=review)
    q = q.filter(files__comments__interfilediff__isnull=True).distinct()

    if not interdiff:
        # The user is browsing a standard diffset, so filter it out.
        q = q.exclude(pk=current_diffset.id)

    if q.exists():
        return True

    # See if there are any interdiffs with comments on them in this review.
    q = DiffSet.objects.filter(files__comments__review=review)
    q = q.filter(files__comments__interfilediff__isnull=False)

    if interdiff:
        # The user is browsing an interdiff, so filter it out.
        q = q.exclude(pk=current_diffset.id,
                      files__comments__interfilediff__diffset=interdiff)

    return q.exists()


def diffsets_with_comments(review, current_pair):
    """Returns a list of diffsets in the review that contain draft comments."""
    if not review:
        return

    diffsets = DiffSet.objects.filter(files__comments__review=review)
    diffsets = diffsets.filter(files__comments__interfilediff__isnull=True)
    diffsets = diffsets.distinct()

    for diffset in diffsets:
        yield {
            'diffset': diffset,
            'is_current': (current_pair[0] == diffset and
                           current_pair[1] is None),
        }


def interdiffs_with_comments(review, current_pair):
    """Get a list of interdiffs in the review that contain draft comments."""
    if not review:
        return

    diffsets = DiffSet.objects.filter(files__comments__review=review)
    diffsets = diffsets.filter(files__comments__interfilediff__isnull=False)
    diffsets = diffsets.distinct()

    for diffset in diffsets:
        interdiffs = DiffSet.objects.filter(
            files__interdiff_comments__filediff__diffset=diffset).distinct()

        for interdiff in interdiffs:
            yield {
                'diffset': diffset,
                'interdiff': interdiff,
                'is_current': (current_pair[0] == diffset and
                               current_pair[1] == interdiff),
            }
