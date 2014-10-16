from __future__ import unicode_literals

import logging

from django.template.context import Context
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from djblets.cache.backend import cache_memoize
from pygments import highlight
from pygments.lexers import (ClassNotFound, guess_lexer_for_filename,
                             TextLexer)

from reviewboard.diffviewer.chunk_generator import NoWrapperHtmlFormatter
from reviewboard.reviews.ui.base import FileAttachmentReviewUI


class TextBasedReviewUI(FileAttachmentReviewUI):
    """A Review UI for text-based files.

    This renders the text file, applying syntax highlighting, and allows users
    to comment on one or more lines.
    """
    name = 'Text'
    object_key = 'text'
    supported_mimetypes = ['text/*']
    template_name = 'reviews/ui/text.html'
    comment_thumbnail_template_name = 'reviews/ui/text_comment_thumbnail.html'
    can_render_text = False

    extra_css_classes = []

    js_model_class = 'RB.TextBasedReviewable'
    js_view_class = 'RB.TextBasedReviewableView'

    def get_js_model_data(self):
        data = super(TextBasedReviewUI, self).get_js_model_data()
        data['hasRenderedView'] = self.can_render_text

        if self.can_render_text:
            data['viewMode'] = 'rendered'
        else:
            data['viewMode'] = 'source'

        return data

    def get_extra_context(self, request):
        return {
            'filename': self.obj.filename,
            'text_lines': [
                mark_safe(line)
                for line in self.get_text_lines()
            ],
            'rendered_lines': [
                mark_safe(line)
                for line in self.get_rendered_lines()
            ],
        }

    def get_text_lines(self):
        """Return the file contents as syntax-highlighted lines.

        This will fetch the file, render it however appropriate for the review
        UI, and split it into reviewable lines. It will then cache it for
        future renders.
        """
        return cache_memoize('text-attachment-%d-lines' % self.obj.pk,
                             lambda: list(self.generate_highlighted_text()))

    def get_rendered_lines(self):
        """Returns the file contents as a render, based on the raw text.

        If a subclass sets ``can_render_text = True`` and implements
        ``generate_render``, then this will render the contents in some
        specialized form, cache it as a list of lines, and return it.
        """
        if self.can_render_text:
            return cache_memoize(
                'text-attachment-%d-rendered' % self.obj.pk,
                lambda: list(self.generate_render()))
        else:
            return []

    def generate_highlighted_text(self):
        """Generates syntax-highlighted text for the file.

        This will render the text file to HTML, applying any syntax
        highlighting that's appropriate. The contents will be split into
        reviewable lines and will be cached for future renders.
        """
        self.obj.file.open()
        data = self.obj.file.read()
        self.obj.file.close()

        lexer = self.get_source_lexer(self.obj.filename, data)
        lines = highlight(data, lexer, NoWrapperHtmlFormatter()).splitlines()

        return [
            '<pre>%s</pre>' % line
            for line in lines
        ]

    def get_source_lexer(self, filename, data):
        """Returns the lexer that should be used for the text.

        By default, this will attempt to guess the lexer based on the
        filename, falling back to a plain-text lexer.

        Subclasses can override this to choose a more specific lexer.
        """
        try:
            return guess_lexer_for_filename(filename, data)
        except ClassNotFound:
            return TextLexer()

    def generate_render(self):
        """Generates a render of the text.

        By default, this won't do anything. Subclasses should override it
        to turn the raw text into some form of rendered content. For
        example, rendering Markdown.
        """
        raise NotImplementedError

    def serialize_comments(self, comments):
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

    def get_comment_thumbnail(self, comment):
        """Generates and returns a thumbnail representing this comment.

        This will find the appropriate lines the comment applies to and
        return it as HTML suited for rendering in reviews.
        """
        try:
            begin_line_num = int(comment.extra_data['beginLineNum'])
            end_line_num = int(comment.extra_data['endLineNum'])
            view_mode = comment.extra_data['viewMode']
        except (KeyError, ValueError):
            # This may be a comment from before we had review UIs. Or,
            # corrupted data. Either way, don't display anything.
            return None

        return cache_memoize(
            'text-review-ui-comment-thumbnail-%s-%s' % (self.obj.pk,
                                                        comment.pk),
            lambda: self.render_comment_thumbnail(comment, begin_line_num,
                                                  end_line_num, view_mode))

    def render_comment_thumbnail(self, comment, begin_line_num, end_line_num,
                                 view_mode):
        """Renders the content of a comment thumbnail.

        This will, by default, call render() and then pull out the lines
        that were commented on.

        Subclasses can override to do more specialized thumbnail rendering.
        """
        try:
            if view_mode == 'source':
                lines = self.get_text_lines()
            elif view_mode == 'rendered':
                lines = self.get_rendered_lines()
            else:
                logging.warning('Unexpected view mode "%s" when rendering '
                                'comment thumbnail.',
                                view_mode)
                return ''
        except Exception as e:
            logging.error('Unable to generate text attachment comment '
                          'thumbnail for comment %s: %s',
                          comment, e)
            return ''

        # Grab only the lines we care about.
        #
        # The line numbers are stored 1-indexed, so normalize to 0.
        lines = lines[begin_line_num - 1:end_line_num]

        return render_to_string(
            self.comment_thumbnail_template_name,
            Context({
                'review_ui': self,
                'lines': [
                    {
                        'line_num': begin_line_num + i,
                        'text': mark_safe(line),
                    }
                    for i, line in enumerate(lines)
                ],
            }))

    def get_comment_link_url(self, comment):
        """Returns the URL to the file and line commented on.

        This will link to the correct file, view mode, and line for the
        given comment.
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
