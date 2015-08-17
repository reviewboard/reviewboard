from __future__ import unicode_literals

import json
import logging
import os
from uuid import uuid4

import mimeparse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.safestring import mark_safe

from reviewboard.attachments.mimetypes import MIMETYPE_EXTENSIONS, score_match
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.markdown_utils import normalize_text_for_edit
from reviewboard.reviews.models import FileAttachmentComment, Review
from reviewboard.site.urlresolvers import local_site_reverse


_file_attachment_review_uis = []


class ReviewUI(object):
    name = None
    model = None
    template_name = 'reviews/ui/default.html'
    object_key = 'obj'
    diff_object_key = 'diff_against_obj'

    allow_inline = False
    supports_diffing = False

    css_bundle_names = []
    js_bundle_names = []
    js_files = []

    js_model_class = None
    js_view_class = None

    def __init__(self, review_request, obj):
        self.review_request = review_request
        self.obj = obj
        self.diff_against_obj = None
        self.request = None

    def set_diff_against(self, obj):
        """Sets the object to generate a diff against.

        This can only be called on review UIs that support diffing,
        and must be called before rendering.
        """
        assert self.supports_diffing

        self.diff_against_obj = obj

    def is_enabled_for(self, user=None, review_request=None,
                       file_attachment=None, **kwargs):
        """Returns whether the review UI is enabled under the given criteria.

        This can enable or disable a review UI's functionality, both on the
        file attachment thumbnail and review UI page, depending on the
        user, review request, file attachment, or some state associated with
        one or more of those.

        When this is called, the arguments are always passed as keyword
        arguments. Subclasses don't need to accept all the arguments, as
        long as they take a ``**kwargs``.
        """
        return True

    def render_to_response(self, request):
        """Renders the review UI to an HttpResponse.

        This is used to render a page dedicated to the review UI, complete
        with the standard Review Board chrome.
        """
        return HttpResponse(
            self.render_to_string(request, request.GET.get('inline', False)))

    def render_to_string(self, request, inline=True):
        """Renders the review UI to an HTML string.

        This renders the review UI to a string for use in embedding into
        either an existing page or a new page.

        If inline is True, the rendered review UI will be embeddable into
        an existing page.

        If inline is False, it will be rendered for use as a full, standalone
        page, compelte with Review Board chrome.
        """
        self.request = request

        last_activity_time, updated_object = \
            self.review_request.get_last_activity()

        draft = self.review_request.get_draft(request.user)
        review_request_details = draft or self.review_request

        close_description, close_description_rich_text = \
            self.review_request.get_close_description()

        context = {
            'caption': self.get_caption(draft),
            'close_description': close_description,
            'close_description_rich_text': close_description_rich_text,
            'comments': self.get_comments(),
            'draft': draft,
            'last_activity_time': last_activity_time,
            'review_request_details': review_request_details,
            'review_request': self.review_request,
            'review_ui': self,
            'review_ui_uuid': six.text_type(uuid4()),
            self.object_key: self.obj,
            self.diff_object_key: self.diff_against_obj,
        }

        if inline:
            context.update({
                'base_template': 'reviews/ui/base_inline.html',
                'review_ui_inline': True,
            })
        else:
            if self.review_request.repository_id:
                diffset_count = DiffSet.objects.filter(
                    history__pk=self.review_request.diffset_history_id).count()
            else:
                diffset_count = 0

            context.update({
                'base_template': 'reviews/ui/base.html',
                'has_diffs': (draft and draft.diffset) or diffset_count > 0,
                'review': self.review_request.get_pending_review(request.user),
                'review_ui_inline': False,
            })
        try:
            context.update(self.get_extra_context(request))
        except Exception as e:
            logging.error('Error when calling get_extra_context for '
                          'FileAttachmentReviewUI %r: %s',
                          self, e, exc_info=1)
        try:
            return render_to_string(
                self.template_name,
                RequestContext(
                    request,
                    make_review_request_context(request, self.review_request,
                                                context)))
        except Exception as e:
            logging.error('Error when calling get_js_model_data or '
                          'get_js_view_data for FileAttachmentReviewUI '
                          '%r: %s',
                          self, e, exc_info=1)

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
        file.
        """
        local_site_name = None
        if self.review_request.local_site:
            local_site_name = self.review_request.local_site.name

        return local_site_reverse(
            'file-attachment',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': self.review_request.display_id,
                'file_attachment_id': self.obj.pk,
            })

    def get_comment_link_text(self, comment):
        """Returns the text to link to a comment.

        This will normally just return the filename, but some may want to
        specialize to list things like page numbers or sections.
        """
        return self.obj.filename

    def get_extra_context(self, request):
        return {}

    def get_js_model_data(self):
        """Returns data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model
        when constructed.
        """
        return {}

    def get_js_view_data(self):
        """Returns data to pass to the JavaScript View during instantiation.

        This data will be passed as options to the reviewable view
        when constructed.
        """
        return {}

    def get_comments_json(self):
        """Returns a JSON-serialized representation of comments for a template.

        The result of this can be used directly in a template to provide
        comments to JavaScript functions.
        """
        try:
            return mark_safe(json.dumps(
                self.serialize_comments(self.get_comments())))
        except Exception as e:
                logging.error('Error When calling serialize_comments for '
                              'FileAttachmentReviewUI %r: %s',
                              self, e, exc_info=1)

    def serialize_comments(self, comments):
        """Serializes the comments for the review UI target.

        By default, this will return a list of serialized comments,
        but it can be overridden to return other list or dictionary-based
        representations, such as comments grouped by an identifier or region.
        These representations must be serializable into JSON.
        """
        user = self.request.user

        result = []
        for comment in comments:
            try:
                review = comment.get_review()
            except Review.DoesNotExist:
                logging.error('Missing Review for comment %r' % comment)
                continue

            try:
                if review and (review.public or review.user == user):
                    result.append(self.serialize_comment(comment))
            except Exception as e:
                logging.error('Error when calling serialize_comment for '
                              'FileAttachmentReviewUI %r: %s',
                              self, e, exc_info=1)

        return result

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
            'text': normalize_text_for_edit(user, comment.text,
                                            comment.rich_text),
            'rich_text': comment.rich_text,
            'user': {
                'username': review.user.username,
                'name': review.user.get_full_name() or review.user.username,
            },
            'url': comment.get_review_url(),
            'localdraft': review.user == user and not review.public,
            'review_id': review.pk,
            'review_request_id': review.review_request_id,
            'issue_opened': comment.issue_opened,
            'issue_status': comment.issue_status_to_string(
                comment.issue_status),
        }


class FileAttachmentReviewUI(ReviewUI):
    """Base class for Review UIs for file attachments.

    Review UIs that deal with FileAttachment objects can subclass this
    to provide the common functionality for their review UI.

    This class handles fetching and serializing comments, locating a correct
    FileAttachmentReviewUI subclass for a given mimetype, and feeding
    data to the JavaScript AbstractReviewable model.

    This also handles much of the work for diffing FileAttachments.
    """
    object_key = 'file'
    diff_object_key = 'diff_against_file'
    supported_mimetypes = []

    def get_comments(self):
        """Returns a list of comments made on the FileAttachment.

        If this review UI is showing a diff between two FileAttachments,
        the comments returned will be specific to that diff.
        """
        comments = FileAttachmentComment.objects.filter(
            file_attachment_id=self.obj.pk)

        if self.diff_against_obj:
            comments = comments.filter(
                diff_against_file_attachment_id=self.diff_against_obj.pk)
        else:
            comments = comments.filter(
                diff_against_file_attachment_id__isnull=True)

        return comments

    def serialize_comment(self, comment):
        data = super(FileAttachmentReviewUI, self).serialize_comment(comment)
        data.update(comment.extra_data)
        return data

    def get_js_model_data(self):
        """Returns model data for the JavaScript AbstractReviewable subclass.

        This will provide the fileAttachmentID and, if diffing, the
        diffAgainstFileAttachmentID.

        Subclasses can override this to return additional data.
        """
        data = {
            'fileAttachmentID': self.obj.pk,
        }

        if self.diff_against_obj:
            data['diffAgainstFileAttachmentID'] = self.diff_against_obj.pk

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
            try:
                mimetype = mimeparse.parse_mime_type(attachment.mimetype)
            except:
                logging.error('Unable to parse MIME type "%s" for %s',
                              attachment.mimetype, attachment)
                return None

            # Override the mimetype if mimeparse is known to misinterpret this
            # type of file as 'octet-stream'
            extension = os.path.splitext(attachment.filename)[1]

            if extension in MIMETYPE_EXTENSIONS:
                mimetype = MIMETYPE_EXTENSIONS[extension]

            score, handler = cls.get_best_handler(mimetype)

            if handler:
                try:
                    return handler(attachment.get_review_request(), attachment)
                except ObjectDoesNotExist as e:
                    logging.error('Unable to load review UI for %s: %s',
                                  attachment, e, exc_info=1)
                except Exception as e:
                    logging.error('Error instantiating '
                                  'FileAttachmentReviewUI %r: %s',
                                  handler, e, exc_info=1)

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
