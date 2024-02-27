"""A comment made on a diff."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from reviewboard.diffviewer.models import FileDiff
from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.site.urlresolvers import local_site_reverse


class Comment(BaseComment):
    """A comment made on a diff.

    A comment can belong to a single filediff or to an interdiff between
    two filediffs. It can also have multiple replies.
    """

    _BASE_FILEDIFF_ID_KEY = '__base_filediff_id'

    anchor_prefix = 'comment'
    comment_type = 'diff'
    filediff = models.ForeignKey(FileDiff,
                                 on_delete=models.CASCADE,
                                 verbose_name=_('file diff'),
                                 related_name='comments')
    interfilediff = models.ForeignKey(FileDiff,
                                      on_delete=models.CASCADE,
                                      verbose_name=_('interdiff file'),
                                      blank=True, null=True,
                                      related_name='interdiff_comments')

    # A null line number applies to an entire diff.  Non-null line numbers are
    # the line within the entire file, starting at 1.
    first_line = models.PositiveIntegerField(_('first line'), blank=True,
                                             null=True)
    num_lines = models.PositiveIntegerField(_('number of lines'), blank=True,
                                            null=True)

    last_line = property(lambda self: self.first_line + self.num_lines - 1)

    @property
    def base_filediff_id(self) -> Optional[int]:
        """The base FileDiff ID for the cumulative diff this comment is on.

        Type:
            int
        """
        if self.extra_data:
            return self.extra_data.get(self._BASE_FILEDIFF_ID_KEY)

        return None

    @base_filediff_id.setter
    def base_filediff_id(self, filediff_id: int):
        if self.extra_data is None:
            self.extra_data = {}

        self.extra_data[self._BASE_FILEDIFF_ID_KEY] = filediff_id

    @property
    def base_filediff(self) -> Optional[FileDiff]:
        """The base filediff, if this comment is made on a commit range.

        Type:
            reviewboard.diffviewer.models.FileDiff
        """
        base_filediff_id = self.base_filediff_id

        if base_filediff_id:
            try:
                return FileDiff.objects.get(pk=base_filediff_id)
            except ObjectDoesNotExist:
                pass

        return None

    def get_absolute_url(self) -> str:
        """Return the URL for the given comment.

        Returns:
            str:
            The URL to view the part of the file where the comment was added.
        """
        review_request = self.get_review_request()

        query: dict[str, Any] = {}

        base_filediff = self.base_filediff

        if base_filediff:
            query['base-commit-id'] = base_filediff.commit_id

        if self.filediff.commit_id:
            query['tip-commit-id'] = self.filediff.commit_id

        if self.interfilediff:
            url = local_site_reverse(
                'view-interdiff',
                local_site=review_request.local_site,
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': self.filediff.diffset.revision,
                    'interdiff_revision':
                        self.interfilediff.diffset.revision,
                })
        else:
            url = local_site_reverse(
                'view-diff-revision',
                local_site=review_request.local_site,
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': self.filediff.diffset.revision,
                })

        anchor = '#file%sline%s' % (self.filediff.id, self.first_line)

        return '%s?%s%s' % (url, urlencode(query), anchor)

    def diff_is_public(self) -> bool:
        """Return whether the diff(s) being commented on are public.

        Returns:
            bool:
            True if the diff (and interdiff, if applicable) is public.
        """
        return (self.filediff.diffset.history is not None and
                (self.interfilediff is None or
                 self.interfilediff.diffset.history is not None))

    class Meta(BaseComment.Meta):
        db_table = 'reviews_comment'
        verbose_name = _('Diff Comment')
        verbose_name_plural = _('Diff Comments')
