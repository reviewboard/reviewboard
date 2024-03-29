"""Base class for a Review UI."""

from __future__ import annotations

import json
import logging
import os
from typing import (Any, Dict, Iterator, List, Optional, Sequence, Tuple,
                    TYPE_CHECKING)
from urllib.parse import urlencode
from uuid import uuid4

import mimeparse
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from typing_extensions import TypeAlias, TypedDict

from reviewboard.attachments.mimetypes import MIMETYPE_EXTENSIONS, score_match
from reviewboard.attachments.models import (FileAttachment,
                                            get_latest_file_attachments)
from reviewboard.deprecation import RemovedInReviewBoard80Warning
from reviewboard.diffviewer.models import FileDiff
from reviewboard.reviews.context import make_review_request_context
from reviewboard.reviews.markdown_utils import (markdown_render_conditional,
                                                normalize_text_for_edit)
from reviewboard.reviews.models import FileAttachmentComment, Review
from reviewboard.site.urlresolvers import local_site_reverse


if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.safestring import SafeText
    from djblets.util.typing import JSONDict

    from reviewboard.reviews.models import (
        BaseComment,
        ReviewRequest,
        ReviewRequestDraft,
    )
    from reviewboard.reviews.models.base_review_request_details import \
        BaseReviewRequestDetails


logger = logging.getLogger(__name__)


class SerializedCommentUser(TypedDict):
    """Serialized user for comment data.

    This must be kept in sync with the definitions in
    :file:`reviewboard/static/rb/js/reviews/models/commentData.ts`.

    Version Added:
        7.0
    """

    #: The user's full name, if available.
    name: str

    #: The user's username.
    username: str


class SerializedComment(TypedDict):
    """Serialized comment data to pass through to JavaScript.

    This must be kept in sync with the definitions in
    :file:`reviewboard/static/rb/js/reviews/models/commentData.ts`.

    Version Added:
        7.0
    """

    #: The ID of the comment.
    comment_id: int

    #: The rendered HTML version of the comment text.
    html: str

    #: Whether the comment opens an issue.
    issue_opened: bool

    #: The status of the issue, if one was opened.
    issue_status: str

    #: Whether the comment is part of the user's current draft review.
    localdraft: bool

    #: The ID of the review that this comment is a part of.
    review_id: int

    #: The ID of the review request that this comment is on.
    review_request_id: int

    #: Whether the comment text should be rendered in Markdown.
    rich_text: bool

    #: The raw text of the comment.
    text: str

    #: The URL to link to for the comment.
    url: str

    #: Information about the author of the comment.
    user: SerializedCommentUser


#: A type for the serialized comments for a review UI.
#:
#: Version Added:
#:     7.0
SerializedCommentBlocks: TypeAlias = Dict[str, List[SerializedComment]]


class ReviewUI:
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
    name = 'Unknown file type'

    #: The template that renders the Review UI.
    #:
    #: Generally, subclasses should use the default template and render the
    #: UI using JavaScript.
    template_name = 'reviews/ui/default.html'

    #: Whether the Review UI can be rendered inline in diffs and other places.
    #:
    #: If set, the Review UI will be able to be displayed within the diff
    #: viewer (and potentially other locations).
    allow_inline = False

    #: Whether this Review UI supports diffing two objects.
    supports_diffing = False

    #: A list of CSS bundle names to include on the Review UI's page.
    css_bundle_names: List[str] = []

    #: A list of JavaScript bundle names to include on the Review UI's page.
    js_bundle_names: List[str] = []

    #: A list of specific JavaScript URLs to include on the page.
    #:
    #: It is recommended that :py:attr:`js_bundle_names` be used instead
    #: where possible.
    js_files: List[str] = []

    #: The list of MIME types that this Review UI supports.
    supported_mimetypes: List[str] = []

    #: Whether this Review UI supports reviewing FileAttachment objects.
    supports_file_attachments: bool = False

    #: Whether there's a file type mismatch when showing diffs.
    diff_type_mismatch: bool = False

    ######################
    # Instance variables #
    ######################

    #: The object being reviewed.
    obj: object

    #: The current HTTP request.
    request: HttpRequest

    @property
    def js_model_class(self) -> str:
        """The name of the JavaScript model class to use for the Review UI.

        Type:
            str
        """
        if isinstance(self.obj, FileAttachment):
            return 'RB.DummyReviewable'
        else:
            return 'RB.AbstractReviewable'

    @property
    def js_view_class(self) -> str:
        """The name of the JavaScript view class to use for the Review UI.

        Type:
            str
        """
        if isinstance(self.obj, FileAttachment):
            return 'RB.DummyReviewableView'
        else:
            return 'RB.AbstractReviewableView'

    @property
    def object_key(self) -> str:
        """The key passed to the template representing the object.

        Type:
            str
        """
        if isinstance(self.obj, FileAttachment):
            return 'file'
        else:
            return 'obj'

    @property
    def diff_object_key(self) -> str:
        """The key passed to the template for an object to diff against.

        Type:
            str
        """
        if isinstance(self.obj, FileAttachment):
            return 'diff_against_file'
        else:
            return 'diff_against_obj'

    def __init__(
        self,
        review_request: ReviewRequest,
        obj: object,
    ) -> None:
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

    def set_diff_against(
        self,
        obj: object,
    ) -> None:
        """Set the object to generate a diff against.

        This can only be called on Review UIs that support diffing,
        and must be called before rendering.

        Args:
            obj (object):
                The object being diffed against.
        """
        assert self.supports_diffing

        self.diff_against_obj = obj

    def is_enabled_for(
        self,
        user: Optional[User] = None,
        review_request: Optional[ReviewRequest] = None,
        obj: Optional[object] = None,
        **kwargs,
    ) -> bool:
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
                            ReviewRequest, optional):
                The review request to check.

            obj (object, optional):
                The object being reviewed.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            bool:
            ``True`` if the Review UI is enabled for the given criteria.
            ``False`` otherwise.

            By default, Review UIs are always enabled.
        """
        if 'file_attachment' in kwargs:
            RemovedInReviewBoard80Warning.warn(
                'The file_attachment argument to ReviewUI.is_enabled_for is '
                'deprecated. Please pass obj= instead.')

        return True

    def render_to_response(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
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
        return HttpResponse(self.render_to_string(
            request=request,
            inline=request.GET.get('inline', '0') in ('1', 'true')))

    def render_to_string(
        self,
        request: HttpRequest,
        inline: bool = True,
    ) -> SafeText:
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
                template_name=self.template_name,
                context=context,
                request=request)
        except Exception as e:
            logger.exception('Error when rendering %r: %s', self, e,
                             extra={'request': request})
            raise

    def build_render_context(
        self,
        request: HttpRequest,
        inline: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
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
        last_activity_time = \
            self.review_request.get_last_activity_info()['timestamp']

        draft = self.review_request.get_draft(request.user)
        review_request_details = draft or self.review_request

        close_info = self.review_request.get_close_info()
        caption = self.get_caption(draft)

        context = make_review_request_context(
            request=request,
            review_request=self.review_request,
            extra_context={
                'caption': caption,
                'close_description': close_info['close_description'],
                'close_description_rich_text': close_info['is_rich_text'],
                'close_timestamp': close_info['timestamp'],
                'comments': self.get_comments(),
                'draft': draft,
                'last_activity_time': last_activity_time,
                'review_request_details': review_request_details,
                'review_request': self.review_request,
                'review_ui': self,
                'review_ui_uuid': str(uuid4()),
                self.object_key: self.obj,
                self.diff_object_key: self.diff_against_obj,
            },
            social_page_image_url=self.get_page_cover_image_url(),
            social_page_title=(
                f'Reviewable for Review Request '
                f'#{self.review_request.display_id}: {caption}'))

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
            logger.exception('Error when calling get_extra_context for '
                             '%r: %s',
                             self, e,
                             extra={'request': request})
            raise

        if isinstance(self.obj, FileAttachment):
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
                    self._get_adjacent_file_attachments(review_request_details)

                context.update({
                    'next_file_attachment': next_file_attachment,
                    'prev_file_attachment': prev_file_attachment,
                })

        return context

    def get_page_cover_image_url(self) -> Optional[str]:
        """Return the URL to an image used to depict this on other sites.

        The returned image URL will be used for services like Facebook, Slack,
        Twitter, etc. when linking to the reviewable object. This may be
        anything from a standard thumbnail to a full-size image.

        By default, no image URL is returned.

        Returns:
            str:
            The absolute URL to an image used to depict the reviewable object.
        """
        return None

    def get_comments(self) -> List[BaseComment]:
        """Return all existing comments on the reviewable object.

        Subclasses must override this.

        Returns:
            list of reviewboard.reviews.models.base_comment.BaseComment:
            The list of comments for the page.
        """
        if isinstance(self.obj, FileAttachment):
            comments = FileAttachmentComment.objects.filter(
                file_attachment_id=self.obj.pk)

            if self.diff_against_obj:
                assert isinstance(self.diff_against_obj, FileAttachment)
                comments = comments.filter(
                    diff_against_file_attachment_id=self.diff_against_obj.pk)
            else:
                comments = comments.filter(
                    diff_against_file_attachment_id__isnull=True)

            return list(comments)

        raise NotImplementedError

    def get_caption(
        self,
        draft: Optional[ReviewRequestDraft] = None,
    ) -> str:
        """Return the caption to show for the reviewable object.

        This defaults to requiring ``caption`` and ``draft_caption`` attributes
        on the reviewable object. Subclasses can override this to use something
        else.

        Args:
            draft (reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                The active review request draft for the user, if any.

        Returns:
            str:
            The caption for the reviewable object.
        """
        if isinstance(self.obj, FileAttachment):
            if draft and self.obj.draft_caption:
                return self.obj.draft_caption
            else:
                return self.obj.caption

        raise NotImplementedError

    def get_comment_thumbnail(
        self,
        comment: BaseComment,
    ) -> Optional[SafeText]:
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

    def get_comment_link_url(
        self,
        comment: BaseComment,
    ) -> str:
        """Return a URL for linking to a comment.

        Subclasses must override this.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to return a link for.

        Returns:
            str:
            The URL to link to the comment.
        """
        if isinstance(comment, FileAttachmentComment):
            assert isinstance(self.obj, FileAttachment)

            if self.obj.is_from_diff:
                return self._get_diff_attachment_comment_link_url(comment)
            else:
                return local_site_reverse(
                    'file-attachment',
                    local_site=self.review_request.local_site,
                    kwargs={
                        'review_request_id': self.review_request.display_id,
                        'file_attachment_id': self.obj.pk,
                    })

        raise NotImplementedError

    def get_comment_link_text(
        self,
        comment: BaseComment,
    ) -> Optional[str]:
        """Return the text to link to a comment.

        This must be implemented by subclasses.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to return text for.

        Returns:
            str:
            The text used to link to the comment.
        """
        if isinstance(self.obj, FileAttachment):
            return self.obj.display_name

        raise NotImplementedError

    def get_extra_context(
        self,
        request: HttpRequest,
    ) -> Dict[str, Any]:
        """Return extra context to use when rendering the Review UI.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            The context to provide to the template.
        """
        return {}

    def get_js_model_data(self) -> JSONDict:
        """Return data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model
        when constructed.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        data: Dict[str, Any] = {}
        obj = self.obj

        if isinstance(obj, FileAttachment):
            state = self.review_request.get_file_attachment_state(obj)
            data.update({
                'fileAttachmentID': obj.pk,
                'fileRevision': obj.attachment_revision,
                'filename': obj.orig_filename,
                'state': state.value,
            })

            if obj.attachment_history is not None:
                attachments = FileAttachment.objects.filter(
                    attachment_history=obj.attachment_history)
                data['attachmentRevisionIDs'] = list(
                    attachments.order_by('attachment_revision')
                    .values_list('pk', flat=True))
                data['numRevisions'] = attachments.count()

            if self.diff_against_obj:
                diff_against_obj = self.diff_against_obj
                assert isinstance(diff_against_obj, FileAttachment)

                data['diffCaption'] = diff_against_obj.display_name
                data['diffAgainstFileAttachmentID'] = diff_against_obj.pk
                data['diffRevision'] = diff_against_obj.attachment_revision
                data['diffTypeMismatch'] = self.diff_type_mismatch

        return data

    def get_js_view_data(self) -> JSONDict:
        """Return data to pass to the JavaScript View during instantiation.

        This data will be passed as options to the reviewable view
        when constructed.

        Returns:
            dict:
            The options to pass to the view.
        """
        return {}

    def get_comments_json(self) -> str:
        """Return a JSON-serialized representation of comments for a template.

        The result of this can be used directly in a template to provide
        comments to JavaScript functions.

        Returns:
            str:
            Serialized JSON content representing the comments on the reviewable
            object.
        """
        try:
            return json.dumps(
                self.serialize_comments(self.get_comments()),
                sort_keys=True)
        except Exception as e:
            logger.exception('Error When calling serialize_comments for '
                             '%r: %s',
                             self, e,
                             extra={'request': self.request})
            raise

    def serialize_comments(
        self,
        comments: Sequence[BaseComment],
    ) -> SerializedCommentBlocks:
        """Serialize the comments for the Review UI target.

        By default, this will return a "flat" array of comments, but it can be
        overridden in order to group comments by identifier or region.

        Args:
            comments (list of reviewboard.reviews.models.base_comment.
                      BaseComment):
                The list of objects to serialize. This will be the result of
                :py:meth:`get_comments`.

        Returns:
            SerializedCommentBlocks:
            The set of serialized comment data.
        """
        result: SerializedCommentBlocks = {}

        for i, comment in enumerate(self.flat_serialized_comments(comments)):
            result[str(i)] = [comment]

        return result

    def flat_serialized_comments(
        self,
        comments: Sequence[BaseComment],
    ) -> Iterator[SerializedComment]:
        """Yield the serialized comments.

        This will go through the list of comments and filter out any which
        should not be shown (ones which are in other users' drafts), then yield
        the serialized form for each.

        Yields:
            SerializedComment:
            The serialized comment.
        """
        assert self.request is not None
        user = self.request.user

        for comment in comments:
            try:
                review = comment.get_review()
            except Review.DoesNotExist:
                logger.error('Missing Review for comment %r',
                             comment,
                             extra={'request': self.request})
                continue

            try:
                if review and (review.public or review.user_id == user.pk):
                    yield self.serialize_comment(comment)
            except Exception as e:
                logger.exception(
                    'Error when calling serialize_comment for %r: %s',
                    comment, e,
                    extra={'request': self.request})
                raise

    def serialize_comment(
        self,
        comment: BaseComment,
    ) -> SerializedComment:
        """Serialize a comment.

        This will provide information on the comment that may be useful
        to the JavaScript code.

        Subclasses that want to add additional data should generally
        augment the result of this function and not replace it.

        Args:
            comment (reviewboard.reviews.models.base_comment.BaseComment):
                The comment to serialize.

        Returns:
            SerializedComment:
            The serialized comment data.
        """
        review = comment.get_review()

        assert self.request is not None
        user = self.request.user

        data: SerializedComment = {
            'comment_id': comment.pk,
            'issue_opened': comment.issue_opened,
            'issue_status': comment.issue_status_to_string(
                comment.issue_status),
            'html': markdown_render_conditional(comment.text,
                                                comment.rich_text),
            'localdraft': review.user_id == user.pk and not review.public,
            'reply_to_id': comment.reply_to_id,
            'review_id': review.pk,
            'review_request_id': review.review_request_id,
            'rich_text': comment.rich_text,
            'text': normalize_text_for_edit(user, comment.text,
                                            comment.rich_text),
            'url': comment.get_review_url(),
            'user': {
                'username': review.user.username,
                'name': review.user.get_profile().get_display_name(user),
            },
        }

        if isinstance(comment, FileAttachmentComment):
            data.update(comment.extra_data)

        return data

    def _get_adjacent_file_attachments(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> Tuple[Optional[FileAttachment], Optional[FileAttachment]]:
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
        assert isinstance(self.obj, FileAttachment)

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

    def _get_diff_attachment_comment_link_url(
        self,
        comment: FileAttachmentComment,
    ) -> str:
        """Return the URL for linking to a comment on a diff file attachment.

        This will inspect a file attachment comment which was made on an
        attachment that's part of a diff, and return the URL to the diff viewer
        with the correct revisions.

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The file attachment comment.

        Returns:
            str:
            The link to the relevant diffviewer revision that the comment was
            made on.
        """
        revision_info = comment.get_comment_diff_revision_info()
        assert revision_info is not None

        diff_revision = revision_info['diff_revision']
        interdiff_revision = revision_info['interdiff_revision']
        base_commit_id = revision_info['base_commit_id']
        tip_commit_id = revision_info['tip_commit_id']
        modified_filediff = revision_info['modified_filediff']
        modified_diffset = revision_info['modified_diffset']

        filediff_id: int = modified_filediff.pk
        query: dict[str, Any] = {}

        if base_commit_id:
            query['base-commit-id'] = base_commit_id

        if tip_commit_id:
            query['tip-commit-id'] = tip_commit_id

        if (modified_diffset.commit_count and
            not base_commit_id and
            not tip_commit_id):
            # For review requests created with commit history, we can have
            # multiple FileDiffs for the same file--one as part of the commit,
            # and one as part of the cumulative diff. The file attachment for a
            # binary file gets uploaded to the FileDiff corresponding to the
            # commit.
            #
            # When the user loads the cumulative diff, we'll find the file
            # attachments that correspond to those files. See
            # :py:meth:`reviewboard.attachments.managers.
            # FileAttachmentManager.get_for_filediff`.
            #
            # When we've reached this point in the code, we know that the user
            # made their comment on the cumulative diff (we don't have any
            # base-commit-id or tip-commit-id parameters to stick in the URL,
            # yet the diffset has commits). We therefore need to do the reverse
            # of what ``get_for_filediff` does, and find the FileDiff in the
            # cumulative diff that corresponds to the commit-specific one we
            # have.
            filediff_id = (
                FileDiff.objects
                .filter(
                    diffset_id=modified_diffset.pk,
                    commit__isnull=True,
                    dest_file=modified_filediff.dest_file)
                .values_list('pk', flat=True)
            )[0]

        review_request = self.review_request

        if interdiff_revision:
            url = local_site_reverse(
                'view-interdiff',
                local_site=review_request.local_site,
                kwargs={
                    'interdiff_revision': interdiff_revision,
                    'review_request_id': review_request.display_id,
                    'revision': diff_revision,
                })
        else:
            url = local_site_reverse(
                'view-diff-revision',
                local_site=review_request.local_site,
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diff_revision,
                })

        if query:
            url += f'?{urlencode(query)}'

        return f'{url}#file{filediff_id}'

    @classmethod
    def for_object(
        cls,
        obj: object,
    ) -> Optional[type[ReviewUI]]:
        """Return the Review UI that is the best fit for a given object.

        Args:
            obj (object):
                The object to review.

        Returns:
            class:
            The Review UI class for the given object, or ``None`` if a
            suitable one could not be found.
        """
        is_file_attachment = isinstance(obj, FileAttachment)
        mime_str: Optional[str] = None
        extension: Optional[str] = None

        if is_file_attachment:
            mime_str = obj.mimetype

            assert obj.filename is not None
            extension = os.path.splitext(obj.filename)[1]

        if not mime_str:
            return None

        if extension and extension in MIMETYPE_EXTENSIONS:
            mimetype = MIMETYPE_EXTENSIONS[extension]
        else:
            try:
                mimetype = mimeparse.parse_mime_type(mime_str)
            except Exception as e:
                logger.error('Unable to parse MIME type "%s" for '
                             'reviewable object %s: %s',
                             mime_str, obj, e)
                return None

        best_score = 0
        best_fit: Optional[type[ReviewUI]] = None

        from reviewboard.reviews.ui import review_ui_registry

        for review_ui in review_ui_registry:
            if not (is_file_attachment and
                    review_ui.supports_file_attachments):
                continue

            for mt in review_ui.supported_mimetypes:
                try:
                    score = score_match(mimeparse.parse_mime_type(mt),
                                        mimetype)

                    if score > best_score:
                        best_score = score
                        best_fit = review_ui
                except ValueError:
                    continue

        return best_fit


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

    supports_file_attachments = True

    @classmethod
    def get_best_handler(
        cls,
        mimetype: Tuple[str, str, str],
    ) -> Tuple[float, Optional[type[ReviewUI]]]:
        """Return the Review UI and score that that best fit the mimetype.

        Args:
            mimetype (tuple):
                A parsed mimetype to find the best review UI for. This is a
                3-tuple of the type, subtype, and parameters as returned by
                :py:func:`mimeparse.parse_mime_type`.

        Returns:
            tuple:
            A tuple of ``(best_score, review_ui)``, or ``(0, None)`` if one
            could not be found.
        """
        RemovedInReviewBoard80Warning.warn(
            'FileAttachmentReviewUI.get_best_handler is deprecated and will '
            'be removed in Review Board 8.0.')

        best_score = 0
        best_fit = None

        from reviewboard.reviews.ui import review_ui_registry

        for review_ui in review_ui_registry:
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
    def for_type(
        cls,
        attachment: FileAttachment,
    ) -> Optional[ReviewUI]:
        """Return the Review UI that is the best fit for a file attachment.

        Args:
            attachment (reviewboard.attachments.models.FileAttachments):
                The file attachment to locate a Review UI for.

        Returns:
            FileAttachmentReviewUI:
            The Review UI for the attachment, or ``None`` if a suitable one
            could not be found.
        """
        RemovedInReviewBoard80Warning.warn(
            'FileAttachmentReviewUI.for_type is deprecated and will '
            'be removed in Review Board 8.0. Callers should instead use '
            'ReviewUI.for_object')

        if attachment.mimetype:
            # Override the mimetype if mimeparse is known to misinterpret this
            # type of file as 'octet-stream'
            assert attachment.filename is not None
            extension = os.path.splitext(attachment.filename)[1]

            if extension in MIMETYPE_EXTENSIONS:
                mimetype = MIMETYPE_EXTENSIONS[extension]
            else:
                try:
                    mimetype = mimeparse.parse_mime_type(attachment.mimetype)
                except Exception:
                    logger.error('Unable to parse MIME type "%s" for %s',
                                 attachment.mimetype, attachment)
                    return None

            score, handler = cls.get_best_handler(mimetype)

            if handler:
                try:
                    return handler(attachment.get_review_request(), attachment)
                except ObjectDoesNotExist as e:
                    logger.error('Unable to load review UI for %s: %s',
                                 attachment, e)
                except Exception as e:
                    logger.exception('Error instantiating '
                                     'FileAttachmentReviewUI %r: %s',
                                     handler, e)

        return None


class DiffMismatchReviewUI(ReviewUI):
    """A special review UI to show when the file types in a diff don't match.
    """

    diff_type_mismatch = True
    supports_diffing = True


def register_ui(review_ui: type[ReviewUI]) -> None:
    """Register a Review UI class.

    This will register a Review UI. Review Board will use it to display a UI
    when reviewing a supported file attachment.

    Args:
        review_ui (type):
            The Review UI to register. This must be a subclass of
            :py:class:`ReviewUI`.

    Raises:
        TypeError:
            The provided Review UI class is not of a compatible type.
    """
    if not issubclass(review_ui, ReviewUI):
        raise TypeError('Only ReviewUI subclasses can be registered')

    from reviewboard.reviews.ui import review_ui_registry

    review_ui_registry.register(review_ui)


def unregister_ui(review_ui: type[ReviewUI]) -> None:
    """Unregister a Review UI class.

    This will unregister a previously registered Review UI.

    Only :py:class:`ReviewUI` subclasses are supported. The class must have
    been registered beforehand or a ValueError will be thrown.

    Args:
        review_ui (type):
            The Review UI to unregister. This must be a subclass of
            :py:class:`ReviewUI`, and must have been registered before.

    Raises:
        TypeError:
            The provided Review UI class is not of a compatible type.

        ValueError:
            The provided Review UI was not previously registered.
    """
    if not issubclass(review_ui, ReviewUI):
        raise TypeError('Only ReviewUI subclasses can be '
                        'unregistered')

    from reviewboard.reviews.ui import review_ui_registry

    review_ui_registry.unregister(review_ui)
