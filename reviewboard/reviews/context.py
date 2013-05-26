from reviewboard.attachments.forms import CommentFileForm, UploadFileForm
from reviewboard.reviews.forms import UploadDiffForm, UploadScreenshotForm


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
