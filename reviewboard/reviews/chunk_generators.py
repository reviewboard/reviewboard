from __future__ import unicode_literals

from django.utils.html import strip_tags

from reviewboard.diffviewer.chunk_generator import RawDiffChunkGenerator


class MarkdownDiffChunkGenerator(RawDiffChunkGenerator):
    """A chunk generator for rendered Markdown content.

    This works like a standard RawDiffChunkGenerator, but handles showing
    changes within a line for HTML-rendered Markdown.
    """

    def get_line_changed_regions(self, old_line_num, old_line,
                                 new_line_num, new_line):
        """Return information on changes between two lines.

        This returns the regions between lines of rendered Markdown that
        have changed.

        Only text changes are highlighted, and not formatting changes (such as
        the addition of bold text).
        """
        return \
            super(MarkdownDiffChunkGenerator, self).get_line_changed_regions(
                old_line_num,
                strip_tags(old_line),
                new_line_num,
                strip_tags(new_line))
