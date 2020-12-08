"""DiffCommit model definition."""

from __future__ import unicode_literals

from dateutil.tz import tzoffset
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.diffviewer.diffutils import get_total_line_counts
from reviewboard.diffviewer.managers import DiffCommitManager
from reviewboard.diffviewer.models.diffset import DiffSet
from reviewboard.diffviewer.validators import (COMMIT_ID_LENGTH,
                                               validate_commit_id)


@python_2_unicode_compatible
class DiffCommit(models.Model):
    """A representation of a commit from a version control system.

    A DiffSet on a Review Request that represents a commit history will have
    one or more DiffCommits. Each DiffCommit will have one or more associated
    FileDiffs (which also belong to the parent DiffSet).

    The information stored herein is intended to fully represent the state of
    a single commit in that history. The series of DiffCommits can be used to
    re-create the original series of commits posted for review.
    """

    #: The maximum length of the author_name and committer_name fields.
    NAME_MAX_LENGTH = 256

    #: The maximum length of the author_email and committer_email fields.
    EMAIL_MAX_LENGTH = 256

    #: The date format that this model uses.
    ISO_DATE_FORMAT = '%Y-%m-%d %H:%M:%S%z'

    filename = models.CharField(
        _('File Name'),
        max_length=256,
        help_text=_('The original file name of the diff.'))

    diffset = models.ForeignKey(DiffSet, related_name='commits')

    author_name = models.CharField(
        _('Author Name'),
        max_length=NAME_MAX_LENGTH,
        help_text=_('The name of the commit author.'))
    author_email = models.CharField(
        _('Author Email'),
        max_length=EMAIL_MAX_LENGTH,
        help_text=_('The e-mail address of the commit author.'))
    author_date_utc = models.DateTimeField(
        _('Author Date'),
        help_text=_('The date the commit was authored in UTC.'))
    author_date_offset = models.IntegerField(
        _('Author Date UTC Offset'),
        help_text=_("The author's UTC offset."))

    committer_name = models.CharField(
        _('Committer Name'),
        max_length=NAME_MAX_LENGTH,
        help_text=_('The name of the committer (if applicable).'),
        null=True,
        blank=True)
    committer_email = models.CharField(
        _('Committer Email'),
        max_length=EMAIL_MAX_LENGTH,
        help_text=_('The e-mail address of the committer (if applicable).'),
        null=True,
        blank=True)
    committer_date_utc = models.DateTimeField(
        _('Committer Date'),
        help_text=_('The date the commit was committed in UTC '
                    '(if applicable).'),
        null=True,
        blank=True)
    committer_date_offset = models.IntegerField(
        _('Committer Date UTC Offset'),
        help_text=_("The committer's UTC offset (if applicable)."),
        null=True,
        blank=True)

    commit_message = models.TextField(
        _('Description'),
        help_text=_('The commit message.'))

    commit_id = models.CharField(
        _('Commit ID'),
        max_length=COMMIT_ID_LENGTH,
        validators=[validate_commit_id],
        help_text=_('The unique identifier of the commit.'))

    parent_id = models.CharField(
        _('Parent ID'),
        max_length=COMMIT_ID_LENGTH,
        validators=[validate_commit_id],
        help_text=_('The unique identifier of the parent commit.'))

    #: A timestamp used for generating HTTP caching headers.
    last_modified = models.DateTimeField(
        _('Last Modified'),
        default=timezone.now)

    extra_data = JSONField(null=True)

    objects = DiffCommitManager()

    @property
    def author(self):
        """The author's name and e-mail address.

        This is formatted as :samp:`{author_name} <{author_email}>`.
        """
        return self._format_user(self.author_name, self.author_email)

    @property
    def author_date(self):
        """The author date in its original timezone."""
        tz = tzoffset(None, self.author_date_offset)
        return self.author_date_utc.astimezone(tz)

    @author_date.setter
    def author_date(self, value):
        """Set the author date.

        Args:
            value (datetime.datetime):
                The date to set.
        """
        self.author_date_utc = value

        if value is not None:
            self.author_date_offset = value.utcoffset().total_seconds()
        else:
            self.author_date_offset = None

    @property
    def committer(self):
        """The committer's name and e-mail address (if applicable).

        This will be formatted as :samp:`{committer_name} <{committer_email}>`
        if both :py:attr:`committer_name` and :py:attr:`committer_email` are
        set. Otherwise, it be whichever is defined. If neither are defined,
        this will be ``None``.
        """
        return self._format_user(self.committer_name, self.committer_email)

    @property
    def committer_date(self):
        """The committer date in its original timezone.

        If the commit has no committer, this will be ``None``.
        """
        if self.committer_date_offset is None:
            return None

        tz = tzoffset(None, self.committer_date_offset)
        return self.committer_date_utc.astimezone(tz)

    @committer_date.setter
    def committer_date(self, value):
        """Set the committer date.

        Args:
            value (datetime.datetime):
                The date to set.
        """
        self.committer_date_utc = value

        if value is not None:
            self.committer_date_offset = value.utcoffset().total_seconds()
        else:
            self.committer_date_offset = None

    @cached_property
    def summary(self):
        """The first line of the commit message."""
        summary = self.commit_message

        if summary:
            summary = summary.split('\n', 1)[0].strip()

        return summary

    @cached_property
    def summary_truncated(self):
        """The first line of the commit message, truncated to 80 characters."""
        summary = self.summary

        if len(summary) > 80:
            summary = summary[:77] + '...'

        return summary

    def serialize(self):
        """Serialize to a dictionary.

        Returns:
            dict:
            A dictionary representing this commit.
        """
        return {
            'author_name': self.author_name,
            'commit_id': self.commit_id,
            'commit_message': self.commit_message,
            'id': self.pk,
            'parent_id': self.parent_id,
        }

    def get_total_line_counts(self):
        """Return the total line counts of all child FileDiffs.

        Returns:
            dict:
            A dictionary with the following keys:

            * ``raw_insert_count``
            * ``raw_delete_count``
            * ``insert_count``
            * ``delete_count``
            * ``replace_count``
            * ``equal_count``
            * ``total_line_count``

            Each entry maps to the sum of that line count type for all child
            :py:class:`FileDiffs
            <reviewboard.diffviewer.models.filediff.FileDiff>`.
        """
        return get_total_line_counts(self.files.all())

    def __str__(self):
        """Return a human-readable representation of the commit.

        Returns:
            unicode:
            The commit ID and its summary (if available).
        """
        if self.summary:
            return '%s: %s' % (self.commit_id, self.summary)

        return self.commit_id

    def _format_user(self, name, email):
        """Format a name and e-mail address.

        Args:
            name (unicode):
                The user's name.

            email (unicode):
                The user's e-mail address.

        Returns:
            unicode:
            A pretty representation of the user and e-mail, or ``None`` if
            neither are defined.
        """
        if name and email:
            return '%s <%s>' % (name, email)
        elif name:
            return name
        elif email:
            return email

        return None

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_diffcommit'
        verbose_name = _('Diff Commit')
        verbose_name_plural = _('Diff Commits')
        unique_together = ('diffset', 'commit_id')
        ordering = ('pk',)
