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
from django.utils.translation import ugettext as _

from reviewboard.attachments.mimetypes import MIMETYPE_EXTENSIONS, score_match
from reviewboard.attachments.models import (FileAttachment,
                                            get_latest_file_attachments)
from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.markdown_utils import (markdown_render_conditional,
                                                normalize_text_for_edit)
from reviewboard.reviews.models import FileAttachmentComment, Review
from reviewboard.site.urlresolvers import local_site_reverse


_file_attachment_review_uis = []


class ReviewUI(object):
    """Base class for a Review UI.

    Review UIs are interfaces for reviewing content of some type. They take a
    type of object and render a page around it, optionally allowing for the
    display of a diff view for the content. They can render context for
    comments made on the object, provide details for social media sharing (such
    as on a chat or social network).

    A Review UI makes use of a JavaScript side for the interaction, defined
    using :py:attr:`js_model_class` and :py:attr:`js_view_class`. The
    JavaScript side should interface with the API to create/update reviews and
    comments for the object being reviewed.

    Extensions providing Review UIs for file attachments should subclass
    :py:class:`FileAttachmentReviewUI`.

    Attributes:
        diff_against_obj (object):
            The object being diffed against, if any.

        obj (object):
            The object being reviewed.

        request (django.http.HttpRequest):
            The HTTP request from the client. This is only set once
            :py:meth:`render_to_string` is called.

        review_request (reviewboard.reviews.models.review_request.
                        ReviewRequest):
            The review request containing the object being reviewed.
    """

    #: The display name for the Review UI.
    name = None

    #: The template that renders the Review UI.
    #:
    #: Generally, subclasses should use the default template and render the
    #: UI using JavaScript.
    template_name = 'reviews/ui/default.html'

    #: The key passed to the template representing the object.
    object_key = 'obj'

    #: The key passed to the template representing an object to diff against.
    diff_object_key = 'diff_against_obj'

    #: Whether the Review UI can be rendered inline in diffs and other places.
    #:
    #: If set, the Review UI will be able to be displayed within the diff
    #: viewer (and potentially other locations).
    allow_inline = False

    #: Whether this Review UI supports diffing two objects.
    supports_diffing = False

    #: A list of CSS bundle names to include on the Review UI's page.
    css_bundle_names = []

    #: A list of JavaScript bundle names to include on the Review UI's page.
    js_bundle_names = []

    #: A list of specific JavaScript URLs to include on the page.
    #:
    #: It is recommended that :py:attr:`js_bundle_names` be used instead
    #: where possible.
    js_files = []

    #: The name of the JavaScript model class to use for the Review UI.
    js_model_class = None

    #: The name of the JavaScript view class to use for the Review UI.
    js_view_class = None

    def __init__(self, review_request, obj):
        """Initialize the Review UI.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request containing the object to review.

            obj (object):
                The object being reviewed.
        """
        self.review_request = review_request
        self.obj = obj
        self.diff_against_obj = None
        self.request = None

    def set_diff_against(self, obj):
        """Set the object to generate a diff against.

        This can only be called on Review UIs that support diffing,
        and must be called before rendering.

        Args:
            obj (object):
                The object being diffed against.
        """
        assert self.supports_diffing

        self.diff_against_obj = obj

    def is_enabled_for(self, user=None, review_request=None, **kwargs):
        """Return whether the Review UI is enabled under the given criteria.

        This can enable or disable a Review UI's functionality depending on
        the user, review request, or some state associated with one or more of
        those.

        When this is called, the arguments are always passed as keyword
        arguments. Subclasses don't need to accept all the arguments, as
        long as they take a ``**kwargs``.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user to check.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request to check.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            bool:
            ``True`` if the Review UI is enabled for the given criteria.
            ``False`` otherwise.

            By default, Review UIs are always enabled.
        """
        return True

    def render_to_response(self, request):
        """Render the Review UI to a response.

        This is used to render a page dedicated to the Review UI, complete
        with the standard Review Board chrome.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            django.http.HttpResponse:
            The HTTP response containing the page for the Review UI.
        """
        return HttpResponse(
            self.render_to_string(request, request.GET.get('inline', False)))

    def render_to_string(self, request, inline=True):
        """Render the Review UI to an HTML string.

        This renders the Review UI to a string for use in embedding into
        either an existing page or a new page.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            inline (bool, optional):
                Whether to render this such that it can be embedded into an
                existing page, instead of as a standalone page.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for the Review UI.
        """
        self.request = request

        try:
            context = self.build_render_context(request, inline=inline)

            return render_to_string(
                self.template_name,
                RequestContext(request, context))
        except Exception as e:
            logging.exception('Error when rendering %r: %s', self, e)

    def build_render_context(self, request, inline, **kwargs):
        """Build context for rendering the page.

        This computes the standard template context to use when rendering the
        page. Generally, subclasses should override
        :py:meth:`get_extra_context`, instead of this.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            inline (bool, optional):
                Whether to render this such that it can be embedded into an
                existing page, instead of as a standalone page.

        Returns:
            dict:
            The context to use in the template.
        """
        last_activity_time, updated_object = \
            self.review_request.get_last_activity()

        draft = self.review_request.get_draft(request.user)
        review_request_details = draft or self.review_request

        close_info = self.review_request.get_close_info()
        caption = self.get_caption(draft)

        context = make_review_request_context(request, self.review_request, {
            'caption': caption,
            'close_description': close_info['close_description'],
            'close_description_rich_text': close_info['is_rich_text'],
            'close_timestamp': close_info['timestamp'],
            'comments': self.get_comments(),
            'draft': draft,
            'last_activity_time': last_activity_time,
            'social_page_image_url': self.get_page_cover_image_url(),
            'social_page_title': (
                'Reviewable for Review Request #%s: %s'
                % (self.review_request.display_id, caption)
            ),
            'review_request_details': review_request_details,
            'review_request': self.review_request,
            'review_ui': self,
            'review_ui_uuid': six.text_type(uuid4()),
            self.object_key: self.obj,
            self.diff_object_key: self.diff_against_obj,
        })

        if inline:
            context.update({
                'base_template': 'reviews/ui/base_inline.html',
                'review_ui_inline': True,
            })
        else:
            context.update({
                'base_template': 'reviews/ui/base.html',
                'review': self.review_request.get_pending_review(request.user),
                'review_ui_inline': False,
            })

        try:
            context.update(self.get_extra_context(request))
        except Exception as e:
            logging.exception('Error when calling get_extra_context for '
                              '%r: %s',
                              self, e)

        return context

    def get_page_cover_image_url(self):
        """Return the URL to an image used to depict this on other sites.

        The returned image URL will be used for services like Facebook, Slack,
        Twitter, etc. when linking to the reviewable object. This may be
        anything from a standard thumbnail to a full-size image.

        By default, no image URL is returned.

        Returns:
            unicode:
            The absolute URL to an image used to depict the reviewable object.
        """
        return None

    def get_comments(self):
        """Return all existing comments on the reviewable object.

        Subclasses must override this.

        Returns:
            list of object:
            The list of comments for the page.
        """
        raise NotImplementedError

    def get_caption(self, draft=None):
        """Return the caption to show for the reviewable object.

        This defaults to requiring ``caption`` and ``draft_caption`` attributes
        on the reviewable object. Subclasses can override this to use something
        else.

        Args:
            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The active review request draft for the user, if any.

        Returns:
            unicode:
            The caption for the reviewable object.
        """
        raise NotImplementedError

    def get_comment_thumbnail(self, comment):
        """Return an HTML thumbnail for a comment.

        If comment thumbnails are possible for the reviewable object, this
        function should return HTML for the thumbnail.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to return a thumbnail for.

        Returns:
            django.utils.safestring.SafeText:
            The HTML for a thumbnail for the comment, or ``None`` if one
            can't be generated (using the default thumbnailing for the
            comment type, if one exists).
        """
        return None

    def get_comment_link_url(self, comment):
        """Return a URL for linking to a comment.

        Subclasses must override this.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to return a link for.

        Returns:
            unicode:
            The URL to link to the comment.
        """
        raise NotImplementedError

    def get_comment_link_text(self, comment):
        """Return the text to link to a comment.

        This must be implemented by subclasses.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to return text for.

        Returns:
            unicode:
            The text used to link to the comment.
        """
        raise NotImplementedError

    def get_extra_context(self, request):
        """Return extra context to use when rendering the Review UI.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            The context to provide to the template.
        """
        return {}

    def get_js_model_data(self):
        """Return data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model
        when constructed.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        return {}

    def get_js_view_data(self):
        """Return data to pass to the JavaScript View during instantiation.

        This data will be passed as options to the reviewable view
        when constructed.

        Returns:
            dict:
            The options to pass to the view.
        """
        return {}

    def get_comments_json(self):
        """Return a JSON-serialized representation of comments for a template.

        The result of this can be used directly in a template to provide
        comments to JavaScript functions.

        Returns:
            unicode:
            Serialized JSON content representing the comments on the reviewable
            object.
        """
        try:
            return mark_safe(json.dumps(
                self.serialize_comments(self.get_comments())))
        except Exception as e:
            logging.exception('Error When calling serialize_comments for '
                              '%r: %s',
                              self, e)

    def serialize_comments(self, comments):
        """Serialize the comments for the Review UI target.

        By default, this will return a list of serialized comments,
        but it can be overridden to return other list or dictionary-based
        representations, such as comments grouped by an identifier or region.
        These representations must be serializable into JSON.

        Args:
            comments (list of reviewboard.reviews.models.base_comment.
                      BaseComment):
                The list of objects to serialize. This will be the result of
                :py:meth:`get_comments`.

        Returns:
            list of dict:
            The list of serialized comment data.
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
                logging.exception('Error when calling serialize_comment for '
                                  '%r: %s',
                                  self, e)

        return result

    def serialize_comment(self, comment):
        """Serialize a comment.

        This will provide information on the comment that may be useful
        to the JavaScript code.

        Subclasses that want to add additional data should generally
        augment the result of this function and not replace it.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to serialize.

        Returns:
            dict:
            The serialized comment data.
        """
        review = comment.get_review()
        user = self.request.user

        return {
            'comment_id': comment.pk,
            'text': normalize_text_for_edit(user, comment.text,
                                            comment.rich_text),
            'rich_text': comment.rich_text,
            'html': markdown_render_conditional(comment.text,
                                                comment.rich_text),
            'user': {
                'username': review.user.username,
                'name': review.user.get_profile().get_display_name(user),
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

    Review UIs that deal with
    :py:class:`~reviewboard.attachments.models.FileAttachment` objects can
    subclass this to provide the common functionality for their Review UI.

    This class handles fetching and serializing comments, locating a correct
    subclass for a given mimetype, and feeding data to the JavaScript
    :js:class:`RB.AbstractReviewable` model.

    This also handles much of the work for diffing file attachments.
    """

    name = 'Unknown file type'
    object_key = 'file'
    diff_object_key = 'diff_against_file'
    supported_mimetypes = []
    js_model_class = 'RB.DummyReviewable'
    js_view_class = 'RB.DummyReviewableView'

    def is_enabled_for(self, user=None, review_request=None,
                       file_attachment=None, **kwargs):
        """Return whether the Review UI is enabled under the given criteria.

        This can enable or disable a Review UI's functionality, both on the
        file attachment thumbnail and Review UI page, depending on the
        user, review request, file attachment, or some state associated with
        one or more of those.

        When this is called, the arguments are always passed as keyword
        arguments. Subclasses don't need to accept all the arguments, as
        long as they take a ``**kwargs``.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user to check.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request to check.

            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment to check.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            bool:
            ``True`` if the Review UI is enabled for the given criteria.
            ``False`` otherwise.

            By default, Review UIs are always enabled.
        """
        return True

    def get_comments(self):
        """Return a list of comments made on the file attachment.

        If this Review UI is showing a diff between two attachments, the
        comments returned will be specific to that diff.

        Returns:
            list of reviewboard.reviews.models.file_attachment_comment.FileAttachmentComment:
            The list of comments on the file attachment or the diff.
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

    def get_caption(self, draft=None):
        """Return the caption to show for the file attachment.

        Args:
            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The active review request draft for the user, if any.

        Returns:
            unicode:
            The caption for the file attachment.
        """
        if draft and self.obj.draft_caption:
            return self.obj.draft_caption

        return self.obj.caption

    def get_comment_link_url(self, comment):
        """Return a URL for linking to a comment.

        This will normally just link to the Review UI itself, but subclasses
        may want to override this to provide a more specialized URL.

        Args:
            comment (reviewboard.reviews.models.file_attachment_comment.
                     FileAttachmentComment):
                The comment to return a link for.

        Returns:
            unicode:
            The URL to link to the comment.
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
        """Return the text to link to a comment.

        This will normally just return the file attachment's display name, but
        some may want to specialize to list things like page numbers or
        sections.

        Args:
            comment (reviewboard.reviews.models.file_attachment_comment.
                     FileAttachmentComment):
                The comment to return text for.

        Returns:
            unicode:
            The text used to link to the comment.
        """
        return self.obj.display_name

    def serialize_comment(self, comment):
        """Serialize a comment.

        This will provide information on the comment that may be useful
        to the JavaScript code.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to serialize.

        Returns:
            dict:
            The serialized comment data.
        """
        data = super(FileAttachmentReviewUI, self).serialize_comment(comment)
        data.update(comment.extra_data)
        return data

    def build_render_context(self, request, inline, **kwargs):
        """Return extra context to use when rendering the Review UI.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            inline (bool, optional):
                Whether to render this such that it can be embedded into an
                existing page, instead of as a standalone page.

        Returns:
            dict:
            The context to use in the template.
        """
        context = super(FileAttachmentReviewUI, self).build_render_context(
            request=request,
            inline=inline)

        context['social_page_title'] = (
            'Attachment for Review Request #%s: %s'
            % (self.review_request.display_id, context['caption'])
        )

        if not inline:
            context['tabs'].append({
                'url': request.path,
                'text': _('File'),
            })

            prev_file_attachment, next_file_attachment = \
                self._get_adjacent_file_attachments(
                    context['review_request_details'])

            context.update({
                'next_file_attachment': next_file_attachment,
                'prev_file_attachment': prev_file_attachment,
            })

        return context

    def get_js_model_data(self):
        """Return model data for the JavaScript AbstractReviewable subclass.

        This will return information on the file attachment, its history,
        and any information on an attachment being diffed against.

        Subclasses can override this to return additional data.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        data = {
            'fileAttachmentID': self.obj.pk,
            'fileRevision': self.obj.attachment_revision,
            'filename': self.obj.orig_filename,
        }

        if self.obj.attachment_history is not None:
            attachments = FileAttachment.objects.filter(
                attachment_history=self.obj.attachment_history)
            data['attachmentRevisionIDs'] = list(
                attachments.order_by('attachment_revision')
                .values_list('pk', flat=True))
            data['numRevisions'] = attachments.count()

        if self.diff_against_obj:
            data['diffCaption'] = self.diff_against_obj.display_name
            data['diffAgainstFileAttachmentID'] = self.diff_against_obj.pk
            data['diffRevision'] = self.diff_against_obj.attachment_revision

            if type(self) != type(self.diff_against_obj.review_ui):
                data['diffTypeMismatch'] = True

        return data

    def _get_adjacent_file_attachments(self, review_request_details):
        """Return the next and previous file attachments.

        The next and previous file attachments are the file attachments that
        occur before and after this one in the review request details view.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            tuple:
            A 2-tuple of the previous and next file attachments, which will
            either be ``None`` (if there isn't a previous or next file
            attachment) or
            :py:class:`~reviewboard.attachments.models.FileAttachment`
            instances.
        """
        file_attachments = iter(get_latest_file_attachments(
            review_request_details.get_file_attachments()))

        prev_obj = None
        next_obj = None

        for obj in file_attachments:
            if obj.pk == self.obj.pk:
                break

            prev_obj = obj

        try:
            next_obj = next(file_attachments)
        except StopIteration:
            pass

        return prev_obj, next_obj

    @classmethod
    def get_best_handler(cls, mimetype):
        """Return the Review UI and score that that best fit the mimetype.

        Args:
            mimetype (unicode):
                The mimetype to find a Review UI for.

        Returns:
            tuple:
            A tuple of ``(best_score, review_ui)``, or ``(0, None)`` if one
            could not be found.
        """
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
        """Return the Review UI that is the best fit for a file attachment.

        Args:
            attachment (reviewboard.attachments.models.FileAttachments):
                The file attachment to locate a Review UI for.

        Returns:
            FileAttachmentReviewUI:
            The Review UI for the attachment, or ``None`` if a suitable one
            could not be found.
        """
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
                                  attachment, e)
                except Exception as e:
                    logging.error('Error instantiating '
                                  'FileAttachmentReviewUI %r: %s',
                                  handler, e)

        return None


def register_ui(review_ui):
    """Register a Review UI class.

    This will register a Review UI. Review Board will use it to display a UI
    when reviewing a supported file attachment.

    Args:
        review_ui (type):
            The Review UI to register. This must be a subclass of
            :py:class:`FileAttachmentReviewUI`.

    Raises:
        TypeError:
            The provided Review UI class is not of a compatible type.
    """
    if not issubclass(review_ui, FileAttachmentReviewUI):
        raise TypeError('Only FileAttachmentReviewUI subclasses can be '
                        'registered')

    _file_attachment_review_uis.append(review_ui)


def unregister_ui(review_ui):
    """Unregister a Review UI class.

    This will unregister a previously registered Review UI.

    Only FileAttachmentReviewUI subclasses are supported. The class must
    have been registered beforehand or a ValueError will be thrown.

    Args:
        review_ui (type):
            The Review UI to unregister. This must be a subclass of
            :py:class:`FileAttachmentReviewUI`, and must have been registered
            before.

    Raises:
        TypeError:
            The provided Review UI class is not of a compatible type.

        ValueError:
            The provided Review UI was not previously registered.
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
