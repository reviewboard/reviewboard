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

    @property
    def base_commit_id(self):
        """Return the base commit ID of the associated diff or None.

        The base commit ID is only defined when the associated diff is
        cumulative.
        """
        if self.extra_data is None:
            return None

        return self.extra_data.get('base_commit_id', None)

    @base_commit_id.setter
    def base_commit_id(self, value):
        """Set the base commit ID of the associated diff.

        If this is set to a non-None value, cumulative_diff will be set to
        True.
        """
        if self.extra_data is None:
            self.extra_data = {}

        if value is not None or 'base_commit_id' in self.extra_data:
            self.extra_data['base_commit_id'] = value

        if value is not None:
            self.cumulative_diff = True

    @property
    def cumulative_diff(self):
        """Return whether or not the associated diff is cumulative."""
        return (self.extra_data and
                self.extra_data.get('cumulative_diff', False))

    @cumulative_diff.setter
    def cumulative_diff(self, value):
        """Set whether or not the associated diff was cumulative.

        If this is set to False, this will also unset the base_commit_id if it
        is set.
        """
        if self.extra_data is None:
            self.extra_data = {}

        value = bool(value)
        self.extra_data['cumulative_diff'] = value

        if not value:
            self.base_commit_id = None

    def get_absolute_url(self):
        revision_path = six.text_type(self.filediff.diffset.revision)
        if self.interfilediff:
            revision_path += "-%s" % self.interfilediff.diffset.revision

        return "%sdiff/%s/?file=%s#file%sline%s" % (
            self.get_review_request().get_absolute_url(),
            revision_path, self.filediff.id, self.filediff.id,
            self.first_line)
