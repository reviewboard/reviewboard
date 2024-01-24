"""A Review UI for text-based files."""

from __future__ import annotations

import logging
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    TYPE_CHECKING,
    Union,
    cast)

from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.safestring import mark_safe
from djblets.cache.backend import cache_memoize
from pygments import highlight
from pygments.lexers import (ClassNotFound, guess_lexer_for_filename,
                             TextLexer)

from reviewboard.attachments.mimetypes import TextMimetype
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.chunk_generator import (NoWrapperHtmlFormatter,
                                                    RawDiffChunkGenerator)
from reviewboard.diffviewer.diffutils import get_chunks_in_range
from reviewboard.diffviewer.settings import DiffSettings
from reviewboard.reviews.ui.base import ReviewUI


if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.util.typing import JSONDict
    from pygments.lexers import Lexer

    from reviewboard.reviews.models import FileAttachmentComment


logger = logging.getLogger(__name__)


class TextBasedReviewUI(ReviewUI):
    """A Review UI for text-based files.

    This renders the text file, applying syntax highlighting, and allows users
    to comment on one or more lines.
    """

    name = 'Text'
    object_key: str = 'text'
    supported_mimetypes = TextMimetype.supported_mimetypes
    template_name = 'reviews/ui/text.html'
    comment_thumbnail_template_name = 'reviews/ui/text_comment_thumbnail.html'
    can_render_text = False
    supports_diffing = True
    supports_file_attachments = True

    source_chunk_generator_cls = RawDiffChunkGenerator
    rendered_chunk_generator_cls = RawDiffChunkGenerator

    #: Extra classes to apply to the Review UI element.
    extra_css_classes: List[str] = []

    js_model_class: str = 'RB.TextBasedReviewable'
    js_view_class: str = 'RB.TextBasedReviewableView'

    def get_js_model_data(self) -> JSONDict:
        """Return data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model
        when constructed.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        data = super(TextBasedReviewUI, self).get_js_model_data()
        data['hasRenderedView'] = self.can_render_text

        if self.can_render_text:
            data['viewMode'] = 'rendered'
        else:
            data['viewMode'] = 'source'

        return data

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
        assert isinstance(self.obj, FileAttachment)
        context = {}
        diff_type_mismatch = False

        if self.diff_against_obj:
            assert isinstance(self.diff_against_obj, FileAttachment)
            diff_against_review_ui = self.diff_against_obj.review_ui

            context.update({
                'diff_caption': self.diff_against_obj.caption,
                'diff_filename': self.diff_against_obj.filename,
                'diff_revision': self.diff_against_obj.attachment_revision,
            })

            if type(self) != type(diff_against_review_ui):
                diff_type_mismatch = True
            else:
                chunk_generator = self._get_source_diff_chunk_generator()
                context['source_chunks'] = chunk_generator.get_chunks()

                chunk_generator = self._get_rendered_diff_chunk_generator()
                context['rendered_chunks'] = chunk_generator.get_chunks()
        else:
            file_line_list = [
                mark_safe(line)
                for line in self.get_text_lines()
            ]

            rendered_line_list = [
                mark_safe(line)
                for line in self.get_rendered_lines()
            ]

            context.update({
                'text_lines': file_line_list,
                'rendered_lines': rendered_line_list,
            })

        if self.obj.attachment_history is not None:
            num_revisions = FileAttachment.objects.filter(
                attachment_history=self.obj.attachment_history).count()
        else:
            num_revisions = 1

        context.update({
            'filename': self.obj.filename,
            'revision': self.obj.attachment_revision,
            'is_diff': self.diff_against_obj is not None,
            'num_revisions': num_revisions,
            'diff_type_mismatch': diff_type_mismatch,
        })

        return context

    def get_text(self) -> str:
        """Return the file contents as a string.

        This will fetch the file and then cache it for future renders.

        Returns:
            str:
            The file contents as a text string.
        """
        assert isinstance(self.obj, FileAttachment)

        return cast(
            str,
            cache_memoize('text-attachment-%d-string' % self.obj.pk,
                          self._get_text_uncached))

    def get_text_lines(self) -> List[str]:
        """Return the file contents as syntax-highlighted lines.

        This will fetch the file, render it however appropriate for the review
        UI, and split it into reviewable lines. It will then cache it for
        future renders.
        """
        assert isinstance(self.obj, FileAttachment)

        return cast(
            List[str],
            cache_memoize('text-attachment-%d-lines' % self.obj.pk,
                          lambda: list(self.generate_highlighted_text())))

    def get_rendered_lines(self) -> List[str]:
        """Return the file contents as a render, based on the raw text.

        If a subclass sets ``can_render_text = True`` and implements
        ``generate_render``, then this will render the contents in some
        specialized form, cache it as a list of lines, and return it.

        Returns:
            list of str:
            The rendered lines.
        """
        assert isinstance(self.obj, FileAttachment)

        if self.can_render_text:
            return cast(
                List[str],
                cache_memoize('text-attachment-%d-rendered' % self.obj.pk,
                              lambda: list(self.generate_render())))
        else:
            return []

    def _get_text_uncached(self) -> str:
        """Return the text from the file.

        Returns:
            str:
            The text of the file.
        """
        assert isinstance(self.obj, FileAttachment)
        self.obj.file.open()

        with self.obj.file as f:
            data = f.read()

        return data

    def generate_highlighted_text(self) -> List[str]:
        """Generate syntax-highlighted text for the file.

        This will render the text file to HTML, applying any syntax
        highlighting that's appropriate. The contents will be split into
        reviewable lines and will be cached for future renders.

        Returns:
            list of str:
            The syntax-highlighted text, split into lines.
        """
        assert isinstance(self.obj, FileAttachment)
        assert self.obj.filename is not None

        data = self.get_text()

        lexer = self.get_source_lexer(self.obj.filename, data)
        lines = highlight(data, lexer, NoWrapperHtmlFormatter()).splitlines()

        return [
            '<pre>%s</pre>' % line
            for line in lines
        ]

    def get_source_lexer(
        self,
        filename: str,
        data: str,
    ) -> Lexer:
        """Return the lexer that should be used for the text.

        By default, this will attempt to guess the lexer based on the
        filename, falling back to a plain-text lexer.

        Subclasses can override this to choose a more specific lexer.

        Args:
            filename (str):
                The filename of the file.

            data (str):
                The contents of the file.

        Returns:
            pygments.lexers.Lexer:
            The lexer to use for highlighting the source.
        """
        try:
            return guess_lexer_for_filename(filename, data)
        except ClassNotFound:
            return TextLexer()

    def generate_render(self) -> Iterator[str]:
        """Generate a render of the text.

        By default, this won't do anything. Subclasses should override it
        to turn the raw text into some form of rendered content. For
        example, rendering Markdown.

        Yields:
            str:
            The rendered lines of content.
        """
        raise NotImplementedError

    def serialize_comments(
        self,
        comments: List[FileAttachmentComment],
    ) -> Dict[str, Any]:
        """Return a dictionary of the comments for this file attachment."""
        result = {}

        for comment in comments:
            try:
                key = '%s-%s' % (comment.extra_data['beginLineNum'],
                                 comment.extra_data['endLineNum'])
            except KeyError:
                # It's possible this comment was made before the review UI
                # was provided, meaning it has no data. If this is the case,
                # ignore this particular comment, since it doesn't have a
                # line region.
                continue

            result.setdefault(key, []).append(self.serialize_comment(comment))

        return result

    def get_comment_thumbnail(
        self,
        comment: FileAttachmentComment,
    ) -> Optional[str]:
        """Generate and return a thumbnail representing this comment.

        This will find the appropriate lines the comment applies to and
        return it as HTML suited for rendering in reviews.

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment to render the thumbnail for.

        Returns:
            str:
            The rendered comment thumbnail.
        """
        assert isinstance(self.obj, FileAttachment)

        try:
            begin_line_num = int(comment.extra_data['beginLineNum'])
            end_line_num = int(comment.extra_data['endLineNum'])
            view_mode = comment.extra_data['viewMode']
        except (KeyError, ValueError):
            # This may be a comment from before we had review UIs. Or,
            # corrupted data. Either way, don't display anything.
            return None

        cache_key = 'text-review-ui-comment-thumbnail-%s-%s' % (
            self.obj.pk, comment.pk),

        return cast(
            Optional[str],
            cache_memoize(
                cache_key,
                lambda: self.render_comment_thumbnail(
                    comment, begin_line_num, end_line_num, view_mode)))

    def render_comment_thumbnail(
        self,
        comment: FileAttachmentComment,
        begin_line_num: int,
        end_line_num: int,
        view_mode: str,
    ) -> str:
        """Render the content of a comment thumbnail.

        This will, by default, call render() and then pull out the lines
        that were commented on.

        Subclasses can override to do more specialized thumbnail rendering.

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment to render the thumbnail for.

            begin_line_num (int):
                The starting line number for the comment.

            end_line_num (int):
                The end line number for the comment.

            view_mode (str):
                The view mode. One of ``source`` or ``rendered``.

        Returns:
            str:
            The rendered comment thumbnail.
        """
        if view_mode not in ('source', 'rendered'):
            logger.warning('Unexpected view mode "%s" when rendering '
                           'comment thumbnail.',
                           view_mode)
            return ''

        assert isinstance(self.obj, FileAttachment)

        context = {
            'is_diff': self.diff_against_obj is not None,
            'review_ui': self,
            'revision': self.obj.attachment_revision,
        }

        if self.diff_against_obj:
            assert isinstance(self.diff_against_obj, FileAttachment)

            if view_mode == 'source':
                chunk_generator = self._get_source_diff_chunk_generator()
            elif view_mode == 'rendered':
                chunk_generator = self._get_rendered_diff_chunk_generator()

            chunks = get_chunks_in_range(chunk_generator.get_chunks(),
                                         begin_line_num,
                                         end_line_num - begin_line_num + 1)

            context.update({
                'chunks': chunks,
                'diff_revision': self.diff_against_obj.attachment_revision,
            })
        else:
            try:
                if view_mode == 'source':
                    lines = self.get_text_lines()
                elif view_mode == 'rendered':
                    lines = self.get_rendered_lines()
            except Exception as e:
                logger.error('Unable to generate text attachment comment '
                             'thumbnail for comment %s: %s',
                             comment, e)
                return ''

            # Grab only the lines we care about.
            #
            # The line numbers are stored 1-indexed, so normalize to 0.
            lines = lines[begin_line_num - 1:end_line_num]

            context['lines'] = [
                {
                    'line_num': begin_line_num + i,
                    'text': mark_safe(line),
                }
                for i, line in enumerate(lines)
            ]

        return render_to_string(
            template_name=self.comment_thumbnail_template_name,
            context=context)

    def get_comment_link_url(
        self,
        comment: FileAttachmentComment,
    ) -> str:
        """Return the URL to the file and line commented on.

        This will link to the correct file, view mode, and line for the
        given comment.

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment to link to.

        Returns:
            str:
            The URL to link the comment to.
        """
        base_url = super(TextBasedReviewUI, self).get_comment_link_url(comment)

        try:
            begin_line_num = int(comment.extra_data['beginLineNum'])
            view_mode = comment.extra_data['viewMode']
        except (KeyError, ValueError):
            # This may be a comment from before we had review UIs. Or,
            # corrupted data. Either way, just return the default.
            return base_url

        return '%s#%s/line%s' % (base_url, view_mode, begin_line_num)

    def _get_diff_chunk_generator(
        self,
        chunk_generator_cls: type[RawDiffChunkGenerator],
        orig: Union[bytes, List[bytes]],
        modified: Union[bytes, List[bytes]],
    ) -> RawDiffChunkGenerator:
        """Return a chunk generator showing a diff for the text.

        The chunk generator will diff the text of this attachment against
        the text of the attachment being diffed against.

        This is used both for displaying the file attachment and
        rendering the thumbnail.

        Args:
            chunk_generator_cls (type):
                The chunk generator to instantiate. This should be a subclass
                of :py:class:`~reviewboard.diffviewer.chunk_generator
                .RawDiffChunkGenerator`.

            orig (bytes or list of bytes):
                The original file content to diff against.

            modified (bytes or list of bytes):
                The new file content.

        Returns:
            reviewboard.diffviewer.chunk_generator.RawDiffChunkGenerator:
            The chunk generator used to diff source or rendered text.
        """
        assert isinstance(self.obj, FileAttachment)
        assert isinstance(self.diff_against_obj, FileAttachment)

        return chunk_generator_cls(
            old=orig,
            new=modified,
            orig_filename=self.obj.filename,
            modified_filename=self.diff_against_obj.filename,
            diff_settings=DiffSettings.create(request=self.request))

    def _get_source_diff_chunk_generator(self) -> RawDiffChunkGenerator:
        """Return a chunk generator for diffing source text.

        Returns:
            reviewboard.diffviewer.chunk_generator.RawDiffChunkGenerator:
            The chunk generator used to diff source text.
        """
        assert isinstance(self.obj, FileAttachment)
        assert isinstance(self.diff_against_obj, FileAttachment)
        assert isinstance(self.diff_against_obj.review_ui, TextBasedReviewUI)

        return self._get_diff_chunk_generator(
            self.source_chunk_generator_cls,
            force_bytes(self.diff_against_obj.review_ui.get_text()),
            force_bytes(self.get_text()))

    def _get_rendered_diff_chunk_generator(self) -> RawDiffChunkGenerator:
        """Return a chunk generator for diffing rendered text.

        Returns:
            reviewboard.diffviewer.chunk_generator.RawDiffChunkGenerator:
            The chunk generator used to diff rendered text.
        """
        assert isinstance(self.diff_against_obj, FileAttachment)

        diff_against_review_ui = self.diff_against_obj.review_ui
        assert isinstance(diff_against_review_ui, TextBasedReviewUI)

        return self._get_diff_chunk_generator(
            self.rendered_chunk_generator_cls,
            [
                force_bytes(line)
                for line in diff_against_review_ui.get_rendered_lines()
            ],
            [
                force_bytes(line)
                for line in self.get_rendered_lines()
            ]
        )
