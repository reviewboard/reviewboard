from __future__ import unicode_literals

from django.db import models
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer.models import FileDiff
from reviewboard.reviews.models.base_comment import BaseComment


class Comment(BaseComment):
    """A comment made on a diff.

    A comment can belong to a single filediff or to an interdiff between
    two filediffs. It can also have multiple replies.
    """
    anchor_prefix = "comment"
    comment_type = "diff"
    filediff = models.ForeignKey(FileDiff, verbose_name=_('file diff'),
                                 related_name="comments")
    interfilediff = models.ForeignKey(FileDiff,
                                      verbose_name=_('interdiff file'),
                                      blank=True, null=True,
                                      related_name="interdiff_comments")

    # A null line number applies to an entire diff.  Non-null line numbers are
    # the line within the entire file, starting at 1.
    first_line = models.PositiveIntegerField(_("first line"), blank=True,
                                             null=True)
    num_lines = models.PositiveIntegerField(_("number of lines"), blank=True,
                                            null=True)

    last_line = property(lambda self: self.first_line + self.num_lines - 1)

    def get_absolute_url(self):
        revision_path = six.text_type(self.filediff.diffset.revision)
        if self.interfilediff:
            revision_path += "-%s" % self.interfilediff.diffset.revision

        return "%sdiff/%s/?file=%s#file%sline%s" % (
            self.get_review_request().get_absolute_url(),
            revision_path, self.filediff.id, self.filediff.id,
            self.first_line)

    class Meta(BaseComment.Meta):
        db_table = 'reviews_comment'
        verbose_name = _('Diff Comment')
        verbose_name_plural = _('Diff Comments')
