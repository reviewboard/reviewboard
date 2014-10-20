from __future__ import unicode_literals

from django.utils import six

from reviewboard.attachments.forms import CommentFileForm, UploadFileForm
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.forms import UploadDiffForm, UploadScreenshotForm
from reviewboard.reviews.markdown_utils import normalize_text_for_edit
from reviewboard.reviews.models import BaseComment


def comment_counts(user, all_comments, filediff, interfilediff=None):
    """
    Returns an array of current comments for a filediff, sorted by line number.

    Each entry in the array has a dictionary containing the following keys:

      =========== ==================================================
      Key                Description
      =========== ==================================================
      comment_id         The ID of the comment
      text               The plain or rich text of the comment
      rich_text          The rich text flag for the comment
      line               The first line number
      num_lines          The number of lines this comment spans
      user               A dictionary containing "username" and "name" keys
                         for the user
      url                The URL to the comment
      localdraft         True if this is the current user's draft comment
      review_id          The ID of the review this comment is associated with
      ==============================================================
    """
    comment_dict = {}

    if interfilediff:
        key = (filediff.pk, interfilediff.pk)
    else:
        key = (filediff.pk, None)

    comments = all_comments.get(key, [])

    for comment in comments:
        review = comment.get_review()

        if review and (review.public or review.user == user):
            key = (comment.first_line, comment.num_lines)

            comment_dict.setdefault(key, []).append({
                'comment_id': comment.id,
                'text': normalize_text_for_edit(user, comment.text,
                                                comment.rich_text),
                'rich_text': comment.rich_text,
                'line': comment.first_line,
                'num_lines': comment.num_lines,
                'user': {
                    'username': review.user.username,
                    'name': (review.user.get_full_name() or
                             review.user.username),
                },
                'url': comment.get_review_url(),
                'localdraft': (review.user == user and
                               not review.public),
                'review_id': review.id,
                'issue_opened': comment.issue_opened,
                'issue_status': BaseComment.issue_status_to_string(
                    comment.issue_status),
            })

    comments_array = []

    for key, value in six.iteritems(comment_dict):
        comments_array.append({
            'linenum': key[0],
            'num_lines': key[1],
            'comments': value,
        })

    comments_array.sort(
        cmp=lambda x, y: (cmp(x['linenum'], y['linenum'] or
                          cmp(x['num_lines'], y['num_lines']))))

    return comments_array


def make_review_request_context(request, review_request, extra_context={}):
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

    return dict({
        'mutable_by_user': review_request.is_mutable_by(request.user),
        'status_mutable_by_user':
            review_request.is_status_mutable_by(request.user),
        'review_request': review_request,
        'upload_diff_form': upload_diff_form,
        'upload_screenshot_form': UploadScreenshotForm(),
        'file_attachment_form': UploadFileForm(),
        'comment_file_form': CommentFileForm(),
        'scmtool': scmtool,
    }, **extra_context)


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

    if q.count() > 0:
        return True

    # See if there are any interdiffs with comments on them in this review.
    q = DiffSet.objects.filter(files__comments__review=review)
    q = q.filter(files__comments__interfilediff__isnull=False)

    if interdiff:
        # The user is browsing an interdiff, so filter it out.
        q = q.exclude(pk=current_diffset.id,
                      files__comments__interfilediff__diffset=interdiff)

    return q.count() > 0


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
