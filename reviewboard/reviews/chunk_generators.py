from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.utils.html import strip_tags

from reviewboard.diffviewer.chunk_generator import RawDiffChunkGenerator

if TYPE_CHECKING:
    from collections.abc import Sequence


#: Matches the attribute marking the gap before a rendered Markdown block.
#:
#: This must match what :py:mod:`reviewboard.reviews.ui.markdownui` adds.
#:
#: Version Added:
#:     9.0
_BLOCK_GAP_RE = re.compile(r' data-md-gap="[a-z]*"')


class MarkdownDiffChunkGenerator(RawDiffChunkGenerator):
    """A chunk generator for rendered Markdown content.

    This works like a standard RawDiffChunkGenerator, but handles showing
    changes within a line for HTML-rendered Markdown.
    """

    def get_comparison_lines(
        self,
        lines: Sequence[str],
    ) -> Sequence[str]:
        """Return the lines to compare when finding changes.

        A block's gap depends on the block before it, so it can change when
        the block itself didn't. Gaps are ignored when comparing.

        Version Added:
            9.0

        Args:
            lines (list of str):
                The lines of one side of the diff.

        Returns:
            list of str:
            The lines to compare.
        """
        return [
            _BLOCK_GAP_RE.sub('', line)
            for line in lines
        ]

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
