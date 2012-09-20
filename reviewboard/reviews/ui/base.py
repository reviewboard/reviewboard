import logging

from django.http import HttpRequest
from django.shortcuts import render_to_response
from django.template.context import RequestContext
import mimeparse

from reviewboard.attachments.mimetypes import score_match
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import FileAttachmentComment


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
            RequestContext(request, {
                'base_template': base_template_name,
                'caption': self.get_caption(),
                'comments': self.get_comments(),
                'draft': draft,
                'has_diffs': (draft and draft.diffset) or diffset_count > 0,
                'review_request_details': review_request_details,
                'review_request': self.review_request,
                'review': review,
                'review_ui': self,
                self.object_key: self.obj,
            }, **self.get_extra_context(request)))

    def get_comments(self):
        return self.obj.get_comments()

    def get_caption(self):
        return self.obj.caption

    def get_extra_context(self, request):
        return {}


class FileAttachmentReviewUI(ReviewUI):
    comment_class = FileAttachmentComment
    object_key = 'file'
    supported_mimetypes = []

    @classmethod
    def get_best_handler(cls, mimetype):
        """Returns the handler and score that that best fit the mimetype."""
        best_score, best_fit = (0, None)

        for mt in cls.supported_mimetypes:
            try:
                score = score_match(mimeparse.parse_mime_type(mt), mimetype)

                if score > best_score:
                    best_score, best_fit = (score, cls)
            except ValueError:
                continue

        for handler in cls.__subclasses__():
            score, best_handler = handler.get_best_handler(mimetype)

            if score > best_score:
                best_score, best_fit = (score, best_handler)

        return (best_score, best_fit)

    @classmethod
    def for_type(cls, attachment):
        """Returns the handler that is the best fit for provided mimetype."""
        mimetype = mimeparse.parse_mime_type(attachment.mimetype)
        score, handler = cls.get_best_handler(mimetype)

        if handler:
            try:
                return handler(attachment.get_review_request(), attachment)
            except Exception, e:
                logging.error('Unable to load review UI for %s: %s',
                              attachment, e, exc_info=1)

        return None
