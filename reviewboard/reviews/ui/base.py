import logging

from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils import simplejson
from django.utils.html import escape
from django.utils.safestring import mark_safe
import mimeparse

from reviewboard.attachments.mimetypes import score_match
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.site.urlresolvers import local_site_reverse


_file_attachment_review_uis = []


class ReviewUI(object):
    model = None
    comment_model = None
    allow_inline = False
    template_name = None
    object_key = 'obj'

    def __init__(self, review_request, obj):
        self.review_request = review_request
        self.obj = obj

    def render_to_response(self, request):
        if request.GET.get('inline', False):
            base_template_name = 'reviews/ui/base_inline.html'
        else:
            base_template_name = 'reviews/ui/base.html'

        self.request = request

        draft = self.review_request.get_draft(request.user)
        review_request_details = draft or self.review_request
        review = self.review_request.get_pending_review(request.user)

        if self.review_request.repository_id:
            diffset_count = DiffSet.objects.filter(
                history__pk=self.review_request.diffset_history_id).count()
        else:
            diffset_count = 0

        return render_to_response(
            self.template_name,
            RequestContext(
                request,
                make_review_request_context(request, self.review_request, {
                    'base_template': base_template_name,
                    'caption': self.get_caption(draft),
                    'comments': self.get_comments(),
                    'draft': draft,
                    'has_diffs': (draft and draft.diffset) or
                                 diffset_count > 0,
                    'review_request_details': review_request_details,
                    'review_request': self.review_request,
                    'review': review,
                    'review_ui': self,
                    self.object_key: self.obj,
                }),
                **self.get_extra_context(request)))

    def get_comments(self):
        return self.obj.get_comments()

    def get_caption(self, draft=None):
        if draft and self.obj.draft_caption:
            return self.obj.draft_caption

        return self.obj.caption

    def get_comment_thumbnail(self, comment):
        """Returns the thumbnail (as HTML) for a comment.

        If this ReviewUI can render comments with a contextual thumbnail,
        it should return HTML representing that comment. Otherwise, return
        None in order to use the fallback.
        """
        return None

    def get_comment_link_url(self, comment):
        """Returns the link for a comment.

        This will normally just link to the review UI itself, but some may want
        to specialize the URL to link to a specific location within the
        file."""
        local_site_name = None
        if self.review_request.local_site:
            local_site_name = self.review_request.local_site.name

        return local_site_reverse(
            'file_attachment',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': self.review_request.display_id,
                'file_attachment_id': self.obj.pk,
            })

    def get_comment_link_text(self, comment):
        """Returns the text to link to a comment.

        This will normally just return the filename, but some may want to
        specialize to list things like page numbers or sections."""
        return self.obj.filename

    def get_extra_context(self, request):
        return {}

    def get_comments_json(self):
        """Returns a JSON-serialized representation of comments for a template.

        The result of this can be used directly in a template to provide
        comments to JavaScript functions.
        """
        return mark_safe(simplejson.dumps(
            self.serialize_comments(self.get_comments())))

    def serialize_comments(self, comments):
        """Serializes the comments for the review UI target.

        By default, this will return a list of serialized comments,
        but it can be overridden to return other list or dictionary-based
        representations, such as comments grouped by an identifier or region.
        These representations must be serializable into JSON.
        """
        user = self.request.user

        for comment in comments:
            review = comment.get_review()

            if review and (review.public or review.user == user):
                yield self.serialize_comment(comment)

    def serialize_comment(self, comment):
        """Serializes a comment.

        This will provide information on the comment that may be useful
        to the JavaScript code.

        Subclasses that want to add additional data should generally
        augment the result of this function and not replace it.
        """
        review = comment.get_review()
        user = self.request.user

        return {
            'comment_id': comment.pk,
            'text': escape(comment.text),
            'user': {
                'username': review.user.username,
                'name': review.user.get_full_name() or review.user.username,
            },
            'url': comment.get_review_url(),
            'localdraft': review.user == user and not review.public,
            'review_id': review.pk,
            'review_request_id': review.review_request_id,
            'issue_opened': comment.issue_opened,
            'issue_status':
                comment.issue_status_to_string(comment.issue_status),
        }


class FileAttachmentReviewUI(ReviewUI):
    comment_class = FileAttachmentComment
    object_key = 'file'
    supported_mimetypes = []

    def serialize_comment(self, comment):
        data = super(FileAttachmentReviewUI, self).serialize_comment(comment)
        data.update(comment.extra_data)
        return data

    @classmethod
    def get_best_handler(cls, mimetype):
        """Returns the handler and score that that best fit the mimetype."""
        best_score = 0
        best_fit = None

        for review_ui in _file_attachment_review_uis:
            for mt in review_ui.supported_mimetypes:
                try:
                    score = score_match(mimeparse.parse_mime_type(mt),
                                        mimetype)

                    if score > best_score:
                        best_score = score
                        best_fit = review_ui
                except ValueError:
                    continue

        return best_score, best_fit

    @classmethod
    def for_type(cls, attachment):
        """Returns the handler that is the best fit for provided mimetype."""
        if attachment.mimetype:
            mimetype = mimeparse.parse_mime_type(attachment.mimetype)
            score, handler = cls.get_best_handler(mimetype)

            if handler:
                try:
                    return handler(attachment.get_review_request(), attachment)
                except Exception, e:
                    logging.error('Unable to load review UI for %s: %s',
                                  attachment, e, exc_info=1)

        return None


def register_ui(review_ui):
    """Registers a review UI class.

    This will register a review UI. Review Board will use it to
    display a UI when reviewing a supported file attachment.

    Only FileAttachmentReviewUI subclasses are supported.
    """
    if not issubclass(review_ui, FileAttachmentReviewUI):
        raise TypeError('Only FileAttachmentReviewUI subclasses can be '
                        'registered')

    _file_attachment_review_uis.append(review_ui)


def unregister_ui(review_ui):
    """Unregisters a review UI class.

    This will unregister a previously registered review UI.

    Only FileAttachmentReviewUI subclasses are supported. The class must
    have been registered beforehand or a ValueError will be thrown.
    """
    if not issubclass(review_ui, FileAttachmentReviewUI):
        raise TypeError('Only FileAttachmentReviewUI subclasses can be '
                        'unregistered')

    try:
        _file_attachment_review_uis.remove(review_ui)
    except ValueError:
        logging.error('Failed to unregister missing review UI %r' %
                      review_ui)
        raise ValueError('This review UI was not previously registered')
