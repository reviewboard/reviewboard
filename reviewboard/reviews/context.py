from django.utils.html import escape

from reviewboard.attachments.forms import CommentFileForm, UploadFileForm
from reviewboard.reviews.forms import UploadDiffForm, UploadScreenshotForm
from reviewboard.reviews.models import BaseComment


def comment_counts(context, filediff, interfilediff=None):
    """
    Returns an array of current comments for a filediff, sorted by line number.

    Each entry in the array has a dictionary containing the following keys:

      =========== ==================================================
      Key                Description
      =========== ==================================================
      comment_id         The ID of the comment
      text               The text of the comment
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
    user = context.get('user', None)
    all_comments = context.get('comments', {})

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
                'text': escape(comment.text),
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

    for key, value in comment_dict.iteritems():
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

    return dict({
        'review_request': review_request,
        'upload_diff_form': upload_diff_form,
        'upload_screenshot_form': UploadScreenshotForm(),
        'file_attachment_form': UploadFileForm(),
        'comment_file_form': CommentFileForm(),
        'scmtool': scmtool,
    }, **extra_context)
